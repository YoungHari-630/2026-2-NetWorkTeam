"""Event-driven, single-area OSPF-style reconvergence simulator.

Overview of the protocol model
------------------------------
* Each router owns an independent :class:`LinkStateDatabase`.
* When a physical link changes (failure, recovery, cost change), each of its
  two endpoints *detects* the change after ``detection_delay`` and originates
  a new Router-LSA with an incremented sequence number.
* LSAs are flooded hop by hop over links that the sending router believes are
  up. Each hop takes ``config.delay_for(link_id)`` virtual time units.
* A receiving router installs an LSA only if it is newer than the copy in its
  own LSDB, then re-floods it on all its other active interfaces. Duplicates
  and outdated LSAs are rejected and *not* re-flooded, which terminates
  flooding.
* When an interface comes back up, the router sends a copy of its whole LSDB
  over it (a simplified OSPF database exchange). This lets two partitions that
  are re-joined learn what changed while they were separated.
* Every LSDB change schedules an SPF calculation on that router (coalesced if
  one is already pending). SPF runs the existing Dijkstra code on the router's
  *local* view of the network built from its own LSDB, never on the global
  physical topology.

The physical topology is only read for (a) the state of a router's *own*
interfaces when it originates an LSA, (b) whether a link is physically up
when a packet is sent over it or delivered, and (c) the convergence and
partition reports, which are observer-side measurements.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from backend.ospf.event_queue import (
    PROTOCOL_EVENT_TYPES,
    EventQueue,
    EventType,
    ScheduledEvent,
)
from backend.ospf.lsa import (
    INITIAL_SEQUENCE_NUMBER,
    AdvertisedLink,
    LinkStateAdvertisement,
    advertised_links_for,
    originate_router_lsa,
)
from backend.ospf.lsdb import InstallResult, LinkStateDatabase
from backend.ospf.models import (
    Number,
    RouteEntry,
    SimulationConfig,
    TopologyData,
    connected_components,
    validate_cost,
    validate_topology,
)
from backend.routing.routing_table import build_routing_table


def compute_routing_table(lsdb: LinkStateDatabase, router_id: str) -> dict[str, dict]:
    """Run SPF for ``router_id`` using only the contents of ``lsdb``.

    Reuses :func:`backend.routing.routing_table.build_routing_table` (and so
    the existing Dijkstra implementation) on the LSDB-derived local topology.
    Returns ``{destination: RouteEntry.to_dict()}`` ordered by destination.
    """

    local_topology = lsdb.to_topology()
    raw_table = build_routing_table(local_topology, router_id)
    table: dict[str, dict] = {}
    for destination in sorted(raw_table):
        row = raw_table[destination]
        table[destination] = RouteEntry(
            destination=destination,
            next_hop=row["next_hop"],
            path=tuple(row["path"]),
            cost=row["cost"],
            reachable=row["cost"] is not None,
        ).to_dict()
    return table


class OSPFSimulator:
    """Deterministic OSPF-style link-state simulation over a weighted topology.

    Public interface (see ``docs/ospf/public-interface.md``):

    * ``OSPFSimulator(topology, config=None)`` - initialize a converged network.
    * ``fail_link / recover_link / change_link_cost / toggle_link`` - schedule
      physical changes (optionally ``delay`` time units in the future).
    * ``step()`` - process exactly one queued event.
    * ``run_until(time)`` / ``run_until_idle()`` - process many events.
    * ``reset()`` - restore the initial topology and clear all state.
    * ``snapshot()`` - JSON-serializable state for the API and frontend.
    """

    def __init__(
        self, topology: TopologyData, config: SimulationConfig | None = None
    ) -> None:
        self._initial_topology = validate_topology(topology)
        self._config = config or SimulationConfig()
        self._handlers: dict[EventType, Callable[[ScheduledEvent], None]] = {
            EventType.LINK_FAILURE: self._handle_link_failure,
            EventType.LINK_RECOVERY: self._handle_link_recovery,
            EventType.LINK_COST_CHANGE: self._handle_link_cost_change,
            EventType.LSA_GENERATION: self._handle_lsa_generation,
            EventType.LSA_RECEPTION: self._handle_lsa_reception,
            EventType.SPF_CALCULATION: self._handle_spf_calculation,
        }
        self.reset()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def reset(self) -> dict[str, Any]:
        """Restore the initial topology, LSDBs, routing tables and clock.

        Initial state: inside every physically connected component, all
        routers hold the sequence-1 LSA of every router in that component
        (i.e. the network starts converged). Routers never start with LSAs
        from a component they cannot reach.
        """

        self._time: Number = 0
        self._topology = deepcopy(self._initial_topology)
        self._router_ids = [router["id"] for router in self._topology["routers"]]
        self._links = {link["id"]: link for link in self._topology["links"]}
        self._queue = EventQueue()
        self._history: list[dict[str, Any]] = []
        self._sequence_numbers = {
            router_id: INITIAL_SEQUENCE_NUMBER for router_id in self._router_ids
        }
        self._lsdbs = {
            router_id: LinkStateDatabase(router_id) for router_id in self._router_ids
        }
        self._routing_tables: dict[str, dict[str, dict]] = {}
        self._table_versions: dict[str, int] = {}
        self._spf_pending: set[str] = set()
        self._generation_pending: set[str] = set()

        self._episode_start: Number | None = None
        self._episode_triggers: list[str] = []
        self._episodes: list[dict[str, Any]] = []
        self._last_change_time: Number | None = None
        self._last_converged_time: Number | None = 0

        initial_lsas = {
            router_id: originate_router_lsa(
                router_id, INITIAL_SEQUENCE_NUMBER, self._topology["links"], 0
            )
            for router_id in self._router_ids
        }
        for component in self._components():
            for router_id in component:
                for origin in component:
                    self._lsdbs[router_id].install(initial_lsas[origin])
        for router_id in self._router_ids:
            self._store_routing_table(router_id)

        self._converged = self._evaluate_convergence()["converged"]
        self._record(
            EventType.SIMULATION_INITIALIZED,
            None,
            None,
            f"Simulation initialized with {len(self._router_ids)} routers and "
            f"{len(self._links)} links.",
            router_count=len(self._router_ids),
            link_count=len(self._links),
            converged=self._converged,
        )
        return self.snapshot()

    # ------------------------------------------------------------------
    # Scheduling physical changes
    # ------------------------------------------------------------------
    def fail_link(self, link_id: str, delay: Number = 0) -> str:
        """Schedule a failure of ``link_id`` ``delay`` units from now."""

        return self._schedule_topology_event(EventType.LINK_FAILURE, link_id, delay)

    def recover_link(self, link_id: str, delay: Number = 0) -> str:
        """Schedule a recovery of ``link_id`` ``delay`` units from now."""

        return self._schedule_topology_event(EventType.LINK_RECOVERY, link_id, delay)

    def change_link_cost(self, link_id: str, cost: int, delay: Number = 0) -> str:
        """Schedule a cost change of ``link_id`` to positive integer ``cost``."""

        validate_cost(cost)
        return self._schedule_topology_event(
            EventType.LINK_COST_CHANGE, link_id, delay, cost=cost
        )

    def toggle_link(self, link_id: str, delay: Number = 0) -> str:
        """Schedule a failure if the link is currently up, else a recovery."""

        self._require_link(link_id)
        if self._links[link_id]["active"]:
            return self.fail_link(link_id, delay)
        return self.recover_link(link_id, delay)

    def _schedule_topology_event(
        self, event_type: EventType, link_id: str, delay: Number, **extra: Any
    ) -> str:
        self._require_link(link_id)
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or delay < 0:
            raise ValueError("delay must be a non-negative number.")
        event = self._queue.schedule(
            self._time + delay, event_type, None, {"link_id": link_id, **extra}
        )
        return event.event_id

    def _require_link(self, link_id: str) -> None:
        if link_id not in self._links:
            raise KeyError(link_id)

    # ------------------------------------------------------------------
    # Running the simulation
    # ------------------------------------------------------------------
    def step(self) -> dict[str, Any] | None:
        """Process the next queued event.

        Returns ``{"event": <processed event>, "records": [<history records>]}``
        or ``None`` when the queue is empty.
        """

        event = self._queue.pop()
        if event is None:
            return None
        self._time = event.time
        first_record = len(self._history)
        self._handlers[event.event_type](event)
        self._update_convergence(event)
        return {
            "event": event.to_dict(),
            "records": deepcopy(self._history[first_record:]),
        }

    def run_until(self, time: Number) -> list[dict[str, Any]]:
        """Process every event scheduled at or before ``time``.

        The clock is then advanced to ``time`` (if it is in the future).
        """

        processed: list[dict[str, Any]] = []
        while True:
            upcoming = self._queue.peek()
            if upcoming is None or upcoming.time > time:
                break
            processed.append(self.step())
        self._time = max(self._time, time)
        return processed

    def run_until_idle(self, max_events: int | None = None) -> list[dict[str, Any]]:
        """Process events until the queue is empty.

        Raises:
            RuntimeError: If more than ``max_events`` (default
                ``config.max_events``) events would be processed, which would
                indicate runaway flooding.
        """

        limit = max_events if max_events is not None else self._config.max_events
        processed: list[dict[str, Any]] = []
        while self._queue:
            if len(processed) >= limit:
                raise RuntimeError(
                    f"Simulation did not become idle within {limit} events."
                )
            processed.append(self.step())
        return processed

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_link_failure(self, event: ScheduledEvent) -> None:
        link = self._links[event.payload["link_id"]]
        if not link["active"]:
            self._record_ignored(event, link, "link is already down")
            return
        link["active"] = False
        self._record(
            EventType.LINK_FAILURE,
            None,
            event.event_id,
            f"Link {link['id']} ({link['source']}-{link['target']}) failed.",
            link_id=link["id"],
            source=link["source"],
            target=link["target"],
            previous_state=True,
            new_state=False,
        )
        self._on_topology_change(event, link)

    def _handle_link_recovery(self, event: ScheduledEvent) -> None:
        link = self._links[event.payload["link_id"]]
        if link["active"]:
            self._record_ignored(event, link, "link is already up")
            return
        link["active"] = True
        self._record(
            EventType.LINK_RECOVERY,
            None,
            event.event_id,
            f"Link {link['id']} ({link['source']}-{link['target']}) recovered.",
            link_id=link["id"],
            source=link["source"],
            target=link["target"],
            previous_state=False,
            new_state=True,
        )
        self._on_topology_change(event, link)

    def _handle_link_cost_change(self, event: ScheduledEvent) -> None:
        link = self._links[event.payload["link_id"]]
        new_cost = event.payload["cost"]
        if link["cost"] == new_cost:
            self._record_ignored(event, link, f"cost is already {new_cost}")
            return
        previous_cost = link["cost"]
        link["cost"] = new_cost
        self._record(
            EventType.LINK_COST_CHANGE,
            None,
            event.event_id,
            f"Link {link['id']} cost changed from {previous_cost} to {new_cost}.",
            link_id=link["id"],
            source=link["source"],
            target=link["target"],
            previous_cost=previous_cost,
            new_cost=new_cost,
        )
        self._on_topology_change(event, link)

    def _on_topology_change(self, event: ScheduledEvent, link: dict[str, Any]) -> None:
        """Start/extend a reconvergence episode and let endpoints detect it."""

        self._last_change_time = self._time
        if self._episode_start is None:
            self._episode_start = self._time
            self._episode_triggers = []
        self._episode_triggers.append(event.event_id)
        for router_id in (link["source"], link["target"]):
            self._schedule_generation(router_id, event.event_type, link["id"])

    def _schedule_generation(
        self, router_id: str, trigger: EventType, link_id: str
    ) -> None:
        # Coalesce: a pending generation reads the interface state when it
        # runs, so it already covers every change detected before then.
        if router_id in self._generation_pending:
            return
        self._generation_pending.add(router_id)
        self._queue.schedule(
            self._time + self._config.detection_delay,
            EventType.LSA_GENERATION,
            router_id,
            {"trigger": trigger.value, "link_id": link_id},
        )

    def _handle_lsa_generation(self, event: ScheduledEvent) -> None:
        router_id = event.router_id
        self._generation_pending.discard(router_id)
        lsdb = self._lsdbs[router_id]
        previous = lsdb.get(router_id)

        self._sequence_numbers[router_id] += 1
        lsa = originate_router_lsa(
            router_id,
            self._sequence_numbers[router_id],
            self._topology["links"],
            self._time,
        )
        self._record(
            EventType.LSA_GENERATION,
            router_id,
            event.event_id,
            f"{router_id} originated LSA seq {lsa.sequence_number}.",
            lsa=lsa.to_dict(),
            trigger=event.payload.get("trigger"),
            link_id=event.payload.get("link_id"),
        )
        lsdb.install(lsa)
        self._record_lsdb_update(router_id, event.event_id, lsa, None)
        self._schedule_spf(router_id)

        previously_up = (
            {link.link_id for link in previous.links if link.active} if previous else set()
        )
        for interface in lsa.links:
            if not interface.active:
                continue
            if interface.link_id in previously_up:
                self._transmit(router_id, interface, lsa, "flood", event.event_id)
            else:
                # Interface just came up: simplified database exchange.
                for stored in lsdb.lsas():
                    self._transmit(
                        router_id, interface, stored, "database_exchange", event.event_id
                    )

    def _handle_lsa_reception(self, event: ScheduledEvent) -> None:
        router_id = event.router_id
        lsa: LinkStateAdvertisement = event.payload["lsa"]
        link_id = event.payload["link_id"]
        sender = event.payload["from_router"]
        lsa_ref = f"{lsa.origin_router_id}#{lsa.sequence_number}"

        if not self._links[link_id]["active"]:
            self._record(
                EventType.LSA_DROPPED,
                router_id,
                event.event_id,
                f"LSA {lsa_ref} from {sender} lost: link {link_id} went down in transit.",
                origin_router_id=lsa.origin_router_id,
                sequence_number=lsa.sequence_number,
                from_router=sender,
                link_id=link_id,
            )
            return

        self._record(
            EventType.LSA_RECEPTION,
            router_id,
            event.event_id,
            f"{router_id} received LSA {lsa_ref} from {sender} via {link_id}.",
            origin_router_id=lsa.origin_router_id,
            sequence_number=lsa.sequence_number,
            from_router=sender,
            link_id=link_id,
        )
        lsdb = self._lsdbs[router_id]
        stored = lsdb.get(lsa.origin_router_id)
        result = lsdb.install(lsa)
        if result is not InstallResult.INSTALLED:
            self._record(
                EventType.LSA_REJECTED,
                router_id,
                event.event_id,
                f"{router_id} rejected {result.value} LSA {lsa_ref} "
                f"(stored seq {stored.sequence_number}).",
                reason=result.value,
                origin_router_id=lsa.origin_router_id,
                sequence_number=lsa.sequence_number,
                stored_sequence_number=stored.sequence_number,
                from_router=sender,
                link_id=link_id,
            )
            return

        self._record_lsdb_update(router_id, event.event_id, lsa, stored)
        self._schedule_spf(router_id)
        own_lsa = lsdb.get(router_id)
        for interface in own_lsa.links if own_lsa else ():
            if interface.active and interface.link_id != link_id:
                self._transmit(router_id, interface, lsa, "flood", event.event_id)

    def _handle_spf_calculation(self, event: ScheduledEvent) -> None:
        router_id = event.router_id
        self._spf_pending.discard(router_id)
        previous_table = self._routing_tables[router_id]
        self._store_routing_table(router_id)
        new_table = self._routing_tables[router_id]
        self._record(
            EventType.SPF_CALCULATION,
            router_id,
            event.event_id,
            f"{router_id} ran SPF on its LSDB (version {self._lsdbs[router_id].version}).",
            lsdb_version=self._lsdbs[router_id].version,
        )
        changes = [
            {
                "destination": destination,
                "previous": previous_table.get(destination),
                "current": new_table.get(destination),
            }
            for destination in sorted(set(previous_table) | set(new_table))
            if previous_table.get(destination) != new_table.get(destination)
        ]
        if changes:
            self._record(
                EventType.ROUTING_TABLE_UPDATE,
                router_id,
                event.event_id,
                f"{router_id} routing table changed for "
                f"{', '.join(change['destination'] for change in changes)}.",
                changes=changes,
            )

    # ------------------------------------------------------------------
    # Protocol helpers
    # ------------------------------------------------------------------
    def _transmit(
        self,
        sender: str,
        interface: AdvertisedLink,
        lsa: LinkStateAdvertisement,
        reason: str,
        caused_by: str,
    ) -> None:
        """Send ``lsa`` from ``sender`` over one of its interfaces."""

        receiver = interface.neighbor_id
        lsa_ref = f"{lsa.origin_router_id}#{lsa.sequence_number}"
        if not self._links[interface.link_id]["active"]:
            # The sender has not detected the failure yet; the packet is lost.
            self._record(
                EventType.LSA_DROPPED,
                sender,
                caused_by,
                f"LSA {lsa_ref} to {receiver} lost: link {interface.link_id} is down.",
                origin_router_id=lsa.origin_router_id,
                sequence_number=lsa.sequence_number,
                to_router=receiver,
                link_id=interface.link_id,
            )
            return
        arrival = self._time + self._config.delay_for(interface.link_id)
        scheduled = self._queue.schedule(
            arrival,
            EventType.LSA_RECEPTION,
            receiver,
            {
                "lsa": lsa,
                "from_router": sender,
                "link_id": interface.link_id,
                "reason": reason,
            },
        )
        self._record(
            EventType.LSA_TRANSMISSION,
            sender,
            caused_by,
            f"{sender} sent LSA {lsa_ref} to {receiver} via {interface.link_id} "
            f"({reason}), arriving at t={arrival}.",
            origin_router_id=lsa.origin_router_id,
            sequence_number=lsa.sequence_number,
            to_router=receiver,
            link_id=interface.link_id,
            reason=reason,
            arrival_time=arrival,
            reception_event_id=scheduled.event_id,
        )

    def _schedule_spf(self, router_id: str) -> None:
        if router_id in self._spf_pending:
            return
        self._spf_pending.add(router_id)
        self._queue.schedule(
            self._time + self._config.spf_delay, EventType.SPF_CALCULATION, router_id
        )

    def _store_routing_table(self, router_id: str) -> None:
        lsdb = self._lsdbs[router_id]
        self._routing_tables[router_id] = compute_routing_table(lsdb, router_id)
        self._table_versions[router_id] = lsdb.version

    def _components(self) -> list[list[str]]:
        return connected_components(self._router_ids, self._topology["links"])

    # ------------------------------------------------------------------
    # Convergence
    # ------------------------------------------------------------------
    def _evaluate_convergence(self) -> dict[str, Any]:
        """Apply the convergence policy (see ``docs/ospf/README.md``).

        The network is converged when all three conditions hold:

        1. No *relevant* protocol work is pending: no LSA generation, no SPF,
           and no in-flight LSA that the receiver would install. In-flight
           duplicates/outdated copies (which will be rejected) and copies
           travelling on a link that is already down (which will be lost)
           cannot change any state, so they do not delay convergence. Future
           *scheduled* link changes do not count: they have not happened yet.
        2. Every router's own LSA matches the real state of its interfaces,
           and inside each physically connected component every router
           holds exactly that latest LSA of every other router in the same
           component. Routers in different components are never compared.
        3. Every routing table was computed from the router's current LSDB.
        """

        reasons: list[str] = []
        pending = self._queue.count(PROTOCOL_EVENT_TYPES)
        relevant = sum(1 for event in self._queue.pending() if self._is_relevant(event))
        if relevant:
            reasons.append(f"{relevant} relevant protocol event(s) pending.")

        for router_id in self._router_ids:
            own = self._lsdbs[router_id].get(router_id)
            actual = advertised_links_for(router_id, self._topology["links"])
            if own is None or own.links != actual:
                reasons.append(
                    f"{router_id} has not yet advertised its current interface state."
                )

        for component in self._components():
            for router_id in component:
                lsdb = self._lsdbs[router_id]
                for origin in component:
                    latest = self._lsdbs[origin].get(origin)
                    held = lsdb.get(origin)
                    if held is None or latest is None or held.key != latest.key:
                        reasons.append(
                            f"{router_id} does not hold the latest LSA of {origin}."
                        )

        for router_id in self._router_ids:
            if self._table_versions[router_id] != self._lsdbs[router_id].version:
                reasons.append(f"{router_id} routing table is stale.")

        converged = not reasons
        return {
            "converged": converged,
            "status": "converged" if converged else "converging",
            "pending_protocol_events": pending,
            "relevant_pending_events": relevant,
            "reasons": reasons,
        }

    def _is_relevant(self, event: ScheduledEvent) -> bool:
        """Whether a pending event can still change LSDBs or routing tables."""

        if event.event_type not in PROTOCOL_EVENT_TYPES:
            return False
        if event.event_type is not EventType.LSA_RECEPTION:
            return True
        if not self._links[event.payload["link_id"]]["active"]:
            return False
        lsdb = self._lsdbs[event.router_id]
        return lsdb.classify(event.payload["lsa"]) is InstallResult.INSTALLED

    def _update_convergence(self, event: ScheduledEvent) -> None:
        status = self._evaluate_convergence()
        if status["converged"] == self._converged:
            return
        self._converged = status["converged"]
        details: dict[str, Any] = {"converged": self._converged}
        if self._converged:
            self._last_converged_time = self._time
            partitioned = len(self._components()) > 1
            episode = {
                "started_at": self._episode_start,
                "converged_at": self._time,
                "duration": (
                    self._time - self._episode_start
                    if self._episode_start is not None
                    else 0
                ),
                "trigger_event_ids": list(self._episode_triggers),
                "partitioned": partitioned,
            }
            self._episodes.append(episode)
            self._episode_start = None
            self._episode_triggers = []
            details.update(episode)
            description = (
                f"Network reconverged at t={self._time} "
                f"after {episode['duration']} time units"
                + (" (network is partitioned)." if partitioned else ".")
            )
        else:
            details["started_at"] = self._episode_start
            description = f"Network is reconverging since t={self._episode_start}."
        self._record(
            EventType.CONVERGENCE_STATUS_CHANGE,
            None,
            event.event_id,
            description,
            **details,
        )

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def _record(
        self,
        event_type: EventType,
        router_id: str | None,
        caused_by: str | None,
        description: str,
        **details: Any,
    ) -> None:
        self._history.append(
            {
                "record_id": len(self._history) + 1,
                "time": self._time,
                "event_type": event_type.value,
                "router_id": router_id,
                "caused_by": caused_by,
                "description": description,
                "details": details,
            }
        )

    def _record_ignored(
        self, event: ScheduledEvent, link: dict[str, Any], reason: str
    ) -> None:
        self._record(
            EventType.LINK_CHANGE_IGNORED,
            None,
            event.event_id,
            f"{event.event_type.value} on {link['id']} ignored: {reason}.",
            requested=event.event_type.value,
            link_id=link["id"],
            reason=reason,
        )

    def _record_lsdb_update(
        self,
        router_id: str,
        caused_by: str,
        lsa: LinkStateAdvertisement,
        previous: LinkStateAdvertisement | None,
    ) -> None:
        previous_seq = previous.sequence_number if previous else None
        self._record(
            EventType.LSDB_UPDATE,
            router_id,
            caused_by,
            f"{router_id} installed LSA {lsa.origin_router_id}#{lsa.sequence_number}.",
            origin_router_id=lsa.origin_router_id,
            sequence_number=lsa.sequence_number,
            previous_sequence_number=previous_seq,
            lsdb_version=self._lsdbs[router_id].version,
        )

    # ------------------------------------------------------------------
    # Read-only accessors and snapshots
    # ------------------------------------------------------------------
    @property
    def time(self) -> Number:
        """Current virtual simulation time."""

        return self._time

    @property
    def config(self) -> SimulationConfig:
        return self._config

    @property
    def router_ids(self) -> list[str]:
        return list(self._router_ids)

    def get_topology(self) -> TopologyData:
        """Physical topology (ground truth), as a defensive copy."""

        return deepcopy(self._topology)

    def get_lsdb(self, router_id: str) -> LinkStateDatabase:
        """Return ``router_id``'s LSDB (read-only by convention)."""

        return self._lsdbs[router_id]

    def get_routing_table(self, router_id: str) -> dict[str, dict]:
        return deepcopy(self._routing_tables[router_id])

    def get_history(self) -> list[dict[str, Any]]:
        return deepcopy(self._history)

    def get_pending_events(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self._queue.pending()]

    def is_converged(self) -> bool:
        return self._evaluate_convergence()["converged"]

    def convergence_status(self) -> dict[str, Any]:
        status = self._evaluate_convergence()
        status.update(
            {
                "current_episode_started_at": self._episode_start,
                "last_change_time": self._last_change_time,
                "last_converged_time": self._last_converged_time,
                "reconvergence_episodes": deepcopy(self._episodes),
            }
        )
        return status

    def partition_status(self) -> dict[str, Any]:
        """Physical partition report, separate from protocol convergence."""

        components = self._components()
        return {
            "partitioned": len(components) > 1,
            "component_count": len(components),
            "components": components,
            "isolated_routers": [c[0] for c in components if len(c) == 1],
        }

    def snapshot(self, include_history: bool = True) -> dict[str, Any]:
        """Return the full, JSON-serializable simulation state."""

        return {
            "time": self._time,
            "config": self._config.to_dict(),
            "topology": deepcopy(self._topology),
            "lsdbs": {
                router_id: self._lsdbs[router_id].to_dict()
                for router_id in self._router_ids
            },
            "routing_tables": {
                router_id: deepcopy(self._routing_tables[router_id])
                for router_id in self._router_ids
            },
            "pending_events": self.get_pending_events(),
            "event_history": deepcopy(self._history) if include_history else [],
            "convergence": self.convergence_status(),
            "partition": self.partition_status(),
        }
