"""Simplified single-area OSPF-style link-state reconvergence simulator.

This package is independent of FastAPI and of the frontend. The team leader's
REST layer is expected to wrap :class:`OSPFSimulator` and expose its
``snapshot()`` output.
"""

from backend.ospf.event_queue import (
    EVENT_PRIORITY,
    PROTOCOL_EVENT_TYPES,
    EventQueue,
    EventType,
    ScheduledEvent,
)
from backend.ospf.lsa import (
    INITIAL_SEQUENCE_NUMBER,
    LSA,
    AdvertisedLink,
    LinkStateAdvertisement,
    originate_router_lsa,
)
from backend.ospf.lsdb import InstallResult, LinkStateDatabase
from backend.ospf.models import RouteEntry, SimulationConfig, validate_topology
from backend.ospf.simulator import OSPFSimulator, compute_routing_table

__all__ = [
    "EVENT_PRIORITY",
    "INITIAL_SEQUENCE_NUMBER",
    "LSA",
    "PROTOCOL_EVENT_TYPES",
    "AdvertisedLink",
    "EventQueue",
    "EventType",
    "InstallResult",
    "LinkStateAdvertisement",
    "LinkStateDatabase",
    "OSPFSimulator",
    "RouteEntry",
    "ScheduledEvent",
    "SimulationConfig",
    "compute_routing_table",
    "originate_router_lsa",
    "validate_topology",
]
