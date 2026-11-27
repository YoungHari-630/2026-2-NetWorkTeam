"""Per-router link-state database (LSDB).

Every router owns an independent :class:`LinkStateDatabase`. There is no
shared global database: two routers may hold different LSAs for the same
origin while an update is still being flooded.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from backend.ospf.lsa import LinkStateAdvertisement


class InstallResult(str, Enum):
    """Outcome of offering an LSA to an LSDB."""

    INSTALLED = "installed"   # New origin, or a higher sequence number.
    DUPLICATE = "duplicate"   # Same origin and same sequence number.
    OUTDATED = "outdated"     # Lower sequence number than the stored LSA.


class LinkStateDatabase:
    """The link-state database held by one router.

    ``version`` increases each time an LSA is installed. The simulator uses it
    to know whether a routing table was computed from the current LSDB.
    """

    def __init__(self, owner_id: str) -> None:
        self.owner_id = owner_id
        self._lsas: dict[str, LinkStateAdvertisement] = {}
        self.version = 0

    def classify(self, lsa: LinkStateAdvertisement) -> InstallResult:
        """Decide what would happen to ``lsa`` without changing the database."""

        current = self._lsas.get(lsa.origin_router_id)
        if current is None or lsa.is_newer_than(current):
            return InstallResult.INSTALLED
        if lsa.sequence_number == current.sequence_number:
            return InstallResult.DUPLICATE
        return InstallResult.OUTDATED

    def install(self, lsa: LinkStateAdvertisement) -> InstallResult:
        """Install ``lsa`` if it is newer; reject duplicates and outdated LSAs."""

        result = self.classify(lsa)
        if result is InstallResult.INSTALLED:
            self._lsas[lsa.origin_router_id] = lsa
            self.version += 1
        return result

    def get(self, origin_router_id: str) -> LinkStateAdvertisement | None:
        return self._lsas.get(origin_router_id)

    def __contains__(self, origin_router_id: object) -> bool:
        return origin_router_id in self._lsas

    def __len__(self) -> int:
        return len(self._lsas)

    def lsas(self) -> list[LinkStateAdvertisement]:
        """Return stored LSAs ordered by origin ID (deterministic)."""

        return [self._lsas[origin] for origin in sorted(self._lsas)]

    def sequence_summary(self) -> dict[str, int]:
        """Return ``{origin: sequence_number}`` for quick comparisons."""

        return {lsa.origin_router_id: lsa.sequence_number for lsa in self.lsas()}

    def known_routers(self) -> list[str]:
        """Routers this LSDB knows about: LSA origins plus advertised neighbors."""

        known = set(self._lsas)
        for lsa in self._lsas.values():
            known.update(link.neighbor_id for link in lsa.links)
        return sorted(known)

    def to_topology(self) -> dict[str, Any]:
        """Build the router's *local view* of the network for SPF.

        The result uses the shared topology format so the existing Dijkstra
        implementation can be reused unchanged. A link is considered usable
        only if it passes a **two-way check**: both endpoints have an LSA in
        this database and both advertise the link as active towards each
        other. This mirrors OSPF's bidirectional-link check and lets a single
        "link down" LSA from either endpoint remove the link.

        If the two endpoints temporarily advertise different costs (a cost
        change still being flooded), the larger cost is used. This is a
        documented simplification; after convergence both values are equal.
        """

        links: list[dict[str, Any]] = []
        seen_link_ids: set[str] = set()
        for lsa in self.lsas():
            for advertised in lsa.links:
                if advertised.link_id in seen_link_ids or not advertised.active:
                    continue
                neighbor_lsa = self._lsas.get(advertised.neighbor_id)
                if neighbor_lsa is None:
                    continue
                reverse = neighbor_lsa.link(advertised.link_id)
                if (
                    reverse is None
                    or not reverse.active
                    or reverse.neighbor_id != lsa.origin_router_id
                ):
                    continue
                seen_link_ids.add(advertised.link_id)
                links.append(
                    {
                        "id": advertised.link_id,
                        "source": lsa.origin_router_id,
                        "target": advertised.neighbor_id,
                        "cost": max(advertised.cost, reverse.cost),
                        "active": True,
                    }
                )
        return {
            "routers": [{"id": router_id} for router_id in self.known_routers()],
            "links": links,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "router_id": self.owner_id,
            "version": self.version,
            "lsas": [lsa.to_dict() for lsa in self.lsas()],
        }
