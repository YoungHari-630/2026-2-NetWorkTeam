"""Tests for the deterministic virtual-time event queue."""

import pytest

from backend.ospf import EventQueue, EventType


def test_events_are_popped_in_chronological_order() -> None:
    queue = EventQueue()
    queue.schedule(5, EventType.SPF_CALCULATION, "A")
    queue.schedule(1, EventType.SPF_CALCULATION, "B")
    queue.schedule(3, EventType.SPF_CALCULATION, "C")

    assert [queue.pop().time for _ in range(3)] == [1, 3, 5]
    assert queue.pop() is None


def test_same_time_events_follow_type_priority() -> None:
    queue = EventQueue()
    queue.schedule(2, EventType.SPF_CALCULATION, "A")
    queue.schedule(2, EventType.LSA_RECEPTION, "A")
    queue.schedule(2, EventType.LSA_GENERATION, "A")
    queue.schedule(2, EventType.LINK_FAILURE, None, {"link_id": "AB"})

    assert [queue.pop().event_type for _ in range(4)] == [
        EventType.LINK_FAILURE,
        EventType.LSA_GENERATION,
        EventType.LSA_RECEPTION,
        EventType.SPF_CALCULATION,
    ]


def test_same_time_and_priority_is_fifo() -> None:
    queue = EventQueue()
    for router_id in ["Z", "A", "M"]:
        queue.schedule(0, EventType.LSA_RECEPTION, router_id)

    assert [queue.pop().router_id for _ in range(3)] == ["Z", "A", "M"]


def test_pending_lists_events_in_processing_order() -> None:
    queue = EventQueue()
    queue.schedule(1, EventType.SPF_CALCULATION, "A")
    queue.schedule(0, EventType.LSA_RECEPTION, "B")
    queue.schedule(1, EventType.LSA_RECEPTION, "C")

    pending_ids = [event.event_id for event in queue.pending()]

    assert pending_ids == ["E00002", "E00003", "E00001"]
    assert [queue.pop().event_id for _ in range(3)] == pending_ids


def test_record_only_types_cannot_be_scheduled() -> None:
    with pytest.raises(ValueError):
        EventQueue().schedule(0, EventType.LSDB_UPDATE, "A")


def test_count_and_clear() -> None:
    queue = EventQueue()
    queue.schedule(0, EventType.SPF_CALCULATION, "A")
    queue.schedule(0, EventType.LINK_RECOVERY, None, {"link_id": "AB"})

    assert queue.count({EventType.SPF_CALCULATION}) == 1
    assert len(queue) == 2
    queue.clear()
    assert not queue
    assert queue.schedule(0, EventType.SPF_CALCULATION, "A").event_id == "E00001"
