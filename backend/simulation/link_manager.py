"""Thread-safe in-memory network and link-state event management."""

from copy import deepcopy
from threading import RLock
from typing import Any


TopologyData = dict[str, Any]


def toggle_link(topology: TopologyData, link_id: str) -> TopologyData:
    """Return a copy of topology with the selected link's state inverted.

    Raises:
        KeyError: If ``link_id`` is not present in the topology.
    """

    updated = deepcopy(topology)
    for link in updated["links"]:
        if link["id"] == link_id:
            link["active"] = not link["active"]
            return updated
    raise KeyError(link_id)


def reset_topology(initial_topology: TopologyData) -> TopologyData:
    """Return a fresh copy of the initial topology."""

    return deepcopy(initial_topology)


class LinkManager:
    """Own the mutable simulation state and its ordered state-change log.

    ``step`` is a sequence number for this simulation run. It is not a measure
    of wall-clock time or real OSPF convergence performance.
    """

    def __init__(self, initial_topology: TopologyData) -> None:
        self._initial_topology = reset_topology(initial_topology)
        self._topology = reset_topology(initial_topology)
        self._events: list[dict[str, Any]] = []
        self._step = 0
        self._lock = RLock()

    def get_topology(self) -> TopologyData:
        """Return a defensive copy of the current network state."""

        with self._lock:
            return deepcopy(self._topology)

    def get_link_status(self, link_id: str) -> bool:
        """Return whether a link is active, raising ``KeyError`` if absent."""

        with self._lock:
            for link in self._topology["links"]:
                if link["id"] == link_id:
                    return link["active"]
        raise KeyError(link_id)

    def get_failed_links(self) -> list[str]:
        """Return IDs of links that are currently inactive."""

        with self._lock:
            return [
                link["id"]
                for link in self._topology["links"]
                if not link["active"]
            ]

    def toggle_link(self, link_id: str) -> TopologyData:
        """Invert a link's state, record the event, and return the new topology."""

        with self._lock:
            for link in self._topology["links"]:
                if link["id"] != link_id:
                    continue

                previous_state = link["active"]
                link["active"] = not previous_state
                self._record_link_event(link, previous_state, link["active"])
                return deepcopy(self._topology)

        raise KeyError(link_id)

    def reset(self) -> TopologyData:
        """Restore the initial topology and clear simulation state and events."""

        with self._lock:
            self._topology = reset_topology(self._initial_topology)
            self._events.clear()
            self._step = 0
            return deepcopy(self._topology)

    def get_events(self) -> list[dict[str, Any]]:
        """Return a defensive copy of state-change events in sequence order."""

        with self._lock:
            return deepcopy(self._events)

    def _record_link_event(
        self,
        link: dict[str, Any],
        previous_state: bool,
        new_state: bool,
    ) -> None:
        self._step += 1
        action = "restored" if new_state else "failed"
        self._events.append(
            {
                "event_id": f"E{self._step:04d}",
                "step": self._step,
                "event_type": f"link_{action}",
                "router_id": None,
                "source": link["source"],
                "destination": link["target"],
                "related_link": link["id"],
                "previous_state": previous_state,
                "new_state": new_state,
                "description": f"Link {link['id']} {action}.",
            }
        )
