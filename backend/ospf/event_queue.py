"""Deterministic discrete-event queue driven by a virtual clock.

Ordering policy (documented in ``docs/ospf/README.md``):

1. Earlier simulation time first.
2. At equal time, lower *type priority* first:
   physical link changes (0) < LSA generation (1) < LSA reception (2)
   < SPF calculation (3). This guarantees that every LSA arriving at time
   ``t`` is installed before an SPF scheduled for ``t`` runs.
3. At equal time and priority, insertion order (FIFO).

The key ``(time, priority, sequence)`` is unique, so the order never depends
on hash randomization or object identity.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping

from backend.ospf.models import Number


class EventType(str, Enum):
    """All event types that can appear in the queue or the history."""

    # Events that are scheduled in the queue and processed by ``step()``.
    LINK_FAILURE = "link_failure"
    LINK_RECOVERY = "link_recovery"
    LINK_COST_CHANGE = "link_cost_change"
    LSA_GENERATION = "lsa_generation"
    LSA_RECEPTION = "lsa_reception"
    SPF_CALCULATION = "spf_calculation"

    # Outcomes recorded in the history while processing a queued event.
    SIMULATION_INITIALIZED = "simulation_initialized"
    LINK_CHANGE_IGNORED = "link_change_ignored"
    LSA_TRANSMISSION = "lsa_transmission"
    LSA_DROPPED = "lsa_dropped"
    LSA_REJECTED = "lsa_rejected"
    LSDB_UPDATE = "lsdb_update"
    ROUTING_TABLE_UPDATE = "routing_table_update"
    CONVERGENCE_STATUS_CHANGE = "convergence_status_change"


#: Same-time ordering priority of queueable events (lower runs first).
EVENT_PRIORITY: dict[EventType, int] = {
    EventType.LINK_FAILURE: 0,
    EventType.LINK_RECOVERY: 0,
    EventType.LINK_COST_CHANGE: 0,
    EventType.LSA_GENERATION: 1,
    EventType.LSA_RECEPTION: 2,
    EventType.SPF_CALCULATION: 3,
}

#: Physical changes requested from outside the protocol.
TOPOLOGY_EVENT_TYPES = frozenset(
    {EventType.LINK_FAILURE, EventType.LINK_RECOVERY, EventType.LINK_COST_CHANGE}
)

#: Protocol work that must finish before the network can be "converged".
PROTOCOL_EVENT_TYPES = frozenset(
    {EventType.LSA_GENERATION, EventType.LSA_RECEPTION, EventType.SPF_CALCULATION}
)


def _serialize(value: Any) -> Any:
    """Convert payload values (e.g. LSAs, enums) to JSON-compatible data."""

    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


@dataclass(frozen=True)
class ScheduledEvent:
    """An event waiting in (or popped from) the queue."""

    event_id: str
    time: Number
    event_type: EventType
    router_id: str | None
    payload: Mapping[str, Any] = field(default_factory=dict)
    sequence: int = 0

    @property
    def sort_key(self) -> tuple[Number, int, int]:
        return (self.time, EVENT_PRIORITY[self.event_type], self.sequence)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "time": self.time,
            "event_type": self.event_type.value,
            "router_id": self.router_id,
            "payload": _serialize(dict(self.payload)),
        }


class EventQueue:
    """Priority queue of :class:`ScheduledEvent` objects."""

    def __init__(self) -> None:
        self._heap: list[tuple[tuple[Number, int, int], ScheduledEvent]] = []
        self._counter = 0

    def schedule(
        self,
        time: Number,
        event_type: EventType,
        router_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> ScheduledEvent:
        """Add an event and return it. ``event_type`` must be queueable."""

        if event_type not in EVENT_PRIORITY:
            raise ValueError(f"{event_type.value} cannot be scheduled in the queue.")
        self._counter += 1
        event = ScheduledEvent(
            event_id=f"E{self._counter:05d}",
            time=time,
            event_type=event_type,
            router_id=router_id,
            payload=dict(payload or {}),
            sequence=self._counter,
        )
        heapq.heappush(self._heap, (event.sort_key, event))
        return event

    def pop(self) -> ScheduledEvent | None:
        """Remove and return the next event, or None if the queue is empty."""

        if not self._heap:
            return None
        return heapq.heappop(self._heap)[1]

    def peek(self) -> ScheduledEvent | None:
        return self._heap[0][1] if self._heap else None

    def pending(self) -> list[ScheduledEvent]:
        """Return pending events in the exact order they will be processed."""

        return [event for _, event in sorted(self._heap, key=lambda item: item[0])]

    def count(self, event_types: Iterable[EventType]) -> int:
        wanted = set(event_types)
        return sum(1 for _, event in self._heap if event.event_type in wanted)

    def clear(self) -> None:
        self._heap.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)
