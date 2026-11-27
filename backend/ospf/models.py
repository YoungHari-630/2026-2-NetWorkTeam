"""Shared data models and topology helpers for the OSPF simulation engine.

The engine deliberately uses plain dataclasses and JSON-compatible dicts so it
stays independent of FastAPI/pydantic and can be reused by tests, scripts, and
the team leader's REST integration layer.
"""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

Number = int | float
TopologyData = dict[str, Any]


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class SimulationConfig:
    """Virtual-time parameters of the simulation.

    All delays are expressed in abstract *simulation time units*; no real
    sleeping ever happens.

    Attributes:
        detection_delay: Time between a physical link change and the moment
            the attached routers notice it and originate a new LSA.
        transmission_delay: Default one-hop LSA propagation delay.
        link_delays: Optional per-link override of ``transmission_delay``,
            keyed by link ID.
        spf_delay: Time between an LSDB change and the SPF run it triggers.
            Several LSDB changes that occur before the SPF runs are coalesced
            into one SPF calculation (similar to OSPF SPF throttling).
        max_events: Safety limit for :meth:`OSPFSimulator.run_until_idle`.
    """

    detection_delay: Number = 0
    transmission_delay: Number = 1
    link_delays: Mapping[str, Number] = field(default_factory=dict)
    spf_delay: Number = 0
    max_events: int = 100_000

    def __post_init__(self) -> None:
        for name in ("detection_delay", "transmission_delay", "spf_delay"):
            value = getattr(self, name)
            if not _is_number(value) or value < 0:
                raise ValueError(f"{name} must be a non-negative number.")
        delays = dict(self.link_delays)
        for link_id, value in delays.items():
            if not _is_number(value) or value < 0:
                raise ValueError(
                    f"Delay for link {link_id!r} must be a non-negative number."
                )
        # Store a private copy so later caller mutations cannot leak in.
        object.__setattr__(self, "link_delays", delays)
        if (
            isinstance(self.max_events, bool)
            or not isinstance(self.max_events, int)
            or self.max_events <= 0
        ):
            raise ValueError("max_events must be a positive integer.")

    def delay_for(self, link_id: str) -> Number:
        """Return the one-hop propagation delay used on ``link_id``."""

        return self.link_delays.get(link_id, self.transmission_delay)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detection_delay": self.detection_delay,
            "transmission_delay": self.transmission_delay,
            "link_delays": dict(self.link_delays),
            "spf_delay": self.spf_delay,
            "max_events": self.max_events,
        }


@dataclass(frozen=True)
class RouteEntry:
    """One routing-table row computed by a router from its own LSDB."""

    destination: str
    next_hop: str | None
    path: tuple[str, ...]
    cost: int | None
    reachable: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "next_hop": self.next_hop,
            "path": list(self.path),
            "cost": self.cost,
            "reachable": self.reachable,
        }


def validate_topology(topology: TopologyData) -> TopologyData:
    """Validate a shared-format topology and return a normalized deep copy.

    The format is the one documented in ``docs/api-contract.md``. Router IDs
    are arbitrary non-empty strings; nothing assumes routers A-D.

    Raises:
        ValueError: If the topology is malformed.
    """

    if not isinstance(topology, dict):
        raise ValueError("Topology must be a dictionary.")
    routers = topology.get("routers")
    links = topology.get("links")
    if not isinstance(routers, list) or not isinstance(links, list):
        raise ValueError("Topology must contain routers and links lists.")
    if not routers:
        raise ValueError("Topology must contain at least one router.")

    router_ids: list[str] = []
    for router in routers:
        if not isinstance(router, dict) or not isinstance(router.get("id"), str):
            raise ValueError("Each router must have a string id.")
        if not router["id"]:
            raise ValueError("Router ids must not be empty.")
        if router["id"] in router_ids:
            raise ValueError(f"Duplicate router id: {router['id']}")
        router_ids.append(router["id"])

    known = set(router_ids)
    link_ids: set[str] = set()
    normalized_links: list[dict[str, Any]] = []
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("Each link must be a dictionary.")
        link_id = link.get("id")
        if not isinstance(link_id, str) or not link_id:
            raise ValueError("Each link must have a non-empty string id.")
        if link_id in link_ids:
            raise ValueError(f"Duplicate link id: {link_id}")
        link_ids.add(link_id)
        source, target = link.get("source"), link.get("target")
        if source not in known or target not in known:
            raise ValueError(f"Link {link_id} endpoints must refer to existing routers.")
        if source == target:
            raise ValueError(f"Link {link_id} must connect two different routers.")
        validate_cost(link.get("cost"))
        if not isinstance(link.get("active"), bool):
            raise ValueError(f"Link {link_id} active state must be a boolean.")
        normalized_links.append(
            {
                "id": link_id,
                "source": source,
                "target": target,
                "cost": link["cost"],
                "active": link["active"],
            }
        )

    return {
        "routers": [{"id": router_id} for router_id in router_ids],
        "links": normalized_links,
    }


def validate_cost(cost: object) -> int:
    """Return ``cost`` if it is a positive integer, otherwise raise ValueError."""

    if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
        raise ValueError("Link costs must be positive integers.")
    return cost


def connected_components(
    router_ids: list[str], links: list[dict[str, Any]]
) -> list[list[str]]:
    """Return physical connected components using only active links.

    Components and their members are returned in topology order, which keeps
    snapshots deterministic.
    """

    adjacency: dict[str, list[str]] = {router_id: [] for router_id in router_ids}
    for link in links:
        if link["active"]:
            adjacency[link["source"]].append(link["target"])
            adjacency[link["target"]].append(link["source"])

    order = {router_id: index for index, router_id in enumerate(router_ids)}
    seen: set[str] = set()
    components: list[list[str]] = []
    for start in router_ids:
        if start in seen:
            continue
        seen.add(start)
        queue = deque([start])
        members: list[str] = []
        while queue:
            current = queue.popleft()
            members.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(members, key=order.__getitem__))
    return components


def copy_topology(topology: TopologyData) -> TopologyData:
    """Return a defensive deep copy of topology data."""

    return deepcopy(topology)
