"""Simplified OSPF Router-LSA model.

Each router originates exactly one LSA describing *all* of its own interfaces
(its adjacent links), similar to an OSPF Router-LSA (type 1). A newer LSA from
the same origin completely replaces the older one. Freshness is decided only by
the sequence number, as in OSPF (age and checksum are not modelled).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from backend.ospf.models import Number

#: Sequence number of the LSAs every router holds when the simulation starts.
INITIAL_SEQUENCE_NUMBER = 1


@dataclass(frozen=True)
class AdvertisedLink:
    """One interface of the originating router, as advertised in its LSA."""

    link_id: str
    neighbor_id: str
    cost: int
    active: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "neighbor_id": self.neighbor_id,
            "cost": self.cost,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdvertisedLink":
        return cls(
            link_id=data["link_id"],
            neighbor_id=data["neighbor_id"],
            cost=data["cost"],
            active=data["active"],
        )


@dataclass(frozen=True)
class LinkStateAdvertisement:
    """An immutable link-state advertisement.

    Attributes:
        origin_router_id: Router that originated (and owns) this LSA.
        sequence_number: Monotonically increasing per origin; higher is newer.
        links: The origin's interfaces with neighbor, cost, and status.
        timestamp: Virtual simulation time at which the LSA was originated.
    """

    origin_router_id: str
    sequence_number: int
    links: tuple[AdvertisedLink, ...]
    timestamp: Number

    @property
    def key(self) -> tuple[str, int]:
        """Identity of this LSA instance: ``(origin, sequence_number)``."""

        return (self.origin_router_id, self.sequence_number)

    def is_newer_than(self, other: "LinkStateAdvertisement") -> bool:
        """Return True if this LSA supersedes ``other`` from the same origin."""

        if other.origin_router_id != self.origin_router_id:
            raise ValueError("Only LSAs from the same origin can be compared.")
        return self.sequence_number > other.sequence_number

    def link(self, link_id: str) -> AdvertisedLink | None:
        """Return the advertised entry for ``link_id``, if present."""

        for advertised in self.links:
            if advertised.link_id == link_id:
                return advertised
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "origin_router_id": self.origin_router_id,
            "sequence_number": self.sequence_number,
            "timestamp": self.timestamp,
            "links": [link.to_dict() for link in self.links],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LinkStateAdvertisement":
        return cls(
            origin_router_id=data["origin_router_id"],
            sequence_number=data["sequence_number"],
            timestamp=data["timestamp"],
            links=tuple(AdvertisedLink.from_dict(link) for link in data["links"]),
        )


#: Short alias used throughout the engine.
LSA = LinkStateAdvertisement


def advertised_links_for(
    router_id: str, physical_links: Iterable[dict[str, Any]]
) -> tuple[AdvertisedLink, ...]:
    """Describe ``router_id``'s own interfaces from physical link records.

    A router legitimately knows the state of its *own* interfaces, so this is
    the only place where physical topology is read to build link-state data.
    """

    advertised: list[AdvertisedLink] = []
    for link in physical_links:
        if link["source"] == router_id:
            neighbor = link["target"]
        elif link["target"] == router_id:
            neighbor = link["source"]
        else:
            continue
        advertised.append(
            AdvertisedLink(
                link_id=link["id"],
                neighbor_id=neighbor,
                cost=link["cost"],
                active=link["active"],
            )
        )
    return tuple(advertised)


def originate_router_lsa(
    router_id: str,
    sequence_number: int,
    physical_links: Iterable[dict[str, Any]],
    timestamp: Number,
) -> LinkStateAdvertisement:
    """Build the Router-LSA that ``router_id`` advertises for its interfaces."""

    return LinkStateAdvertisement(
        origin_router_id=router_id,
        sequence_number=sequence_number,
        links=advertised_links_for(router_id, physical_links),
        timestamp=timestamp,
    )
