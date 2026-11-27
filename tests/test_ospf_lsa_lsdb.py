"""Unit tests for the LSA model, per-router LSDB and LSDB-based SPF."""

import pytest

from backend.ospf import (
    AdvertisedLink,
    InstallResult,
    LinkStateAdvertisement,
    LinkStateDatabase,
    compute_routing_table,
    originate_router_lsa,
)

LINKS = [
    {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": True},
    {"id": "AC", "source": "A", "target": "C", "cost": 2, "active": True},
    {"id": "BD", "source": "B", "target": "D", "cost": 1, "active": False},
]


def lsa(origin: str, seq: int, *links: tuple[str, str, int, bool], t: float = 0):
    return LinkStateAdvertisement(
        origin_router_id=origin,
        sequence_number=seq,
        links=tuple(AdvertisedLink(*link) for link in links),
        timestamp=t,
    )


def test_originated_lsa_describes_only_own_interfaces() -> None:
    advertisement = originate_router_lsa("B", 3, LINKS, timestamp=7)

    assert advertisement.origin_router_id == "B"
    assert advertisement.sequence_number == 3
    assert advertisement.timestamp == 7
    assert advertisement.links == (
        AdvertisedLink("AB", "A", 1, True),
        AdvertisedLink("BD", "D", 1, False),
    )


def test_lsa_round_trips_through_dict() -> None:
    advertisement = originate_router_lsa("A", 2, LINKS, timestamp=1.5)

    assert LinkStateAdvertisement.from_dict(advertisement.to_dict()) == advertisement
    assert advertisement.to_dict()["links"][0] == {
        "link_id": "AB",
        "neighbor_id": "B",
        "cost": 1,
        "active": True,
    }


def test_freshness_is_decided_by_sequence_number() -> None:
    older = lsa("A", 1, t=10)
    newer = lsa("A", 2, t=0)

    assert newer.is_newer_than(older)
    assert not older.is_newer_than(newer)
    with pytest.raises(ValueError):
        newer.is_newer_than(lsa("B", 1))


def test_lsdb_installs_newer_and_rejects_duplicate_and_outdated() -> None:
    lsdb = LinkStateDatabase("X")

    assert lsdb.install(lsa("A", 2)) is InstallResult.INSTALLED
    assert lsdb.version == 1
    assert lsdb.install(lsa("A", 2)) is InstallResult.DUPLICATE
    assert lsdb.install(lsa("A", 1)) is InstallResult.OUTDATED
    assert lsdb.version == 1, "rejected LSAs must not change the database"
    assert lsdb.get("A").sequence_number == 2
    assert lsdb.install(lsa("A", 3)) is InstallResult.INSTALLED
    assert lsdb.sequence_summary() == {"A": 3}
    assert lsdb.version == 2


def test_classify_does_not_modify_database() -> None:
    lsdb = LinkStateDatabase("X")

    assert lsdb.classify(lsa("A", 1)) is InstallResult.INSTALLED
    assert len(lsdb) == 0


def test_two_way_check_excludes_link_advertised_down_by_one_side() -> None:
    lsdb = LinkStateDatabase("A")
    lsdb.install(lsa("A", 1, ("AB", "B", 1, True)))
    lsdb.install(lsa("B", 2, ("AB", "A", 1, False)))

    assert lsdb.to_topology()["links"] == []


def test_two_way_check_requires_neighbor_lsa() -> None:
    lsdb = LinkStateDatabase("A")
    lsdb.install(lsa("A", 1, ("AB", "B", 1, True)))

    topology = lsdb.to_topology()

    assert topology["routers"] == [{"id": "A"}, {"id": "B"}]
    assert topology["links"] == []


def test_temporary_cost_disagreement_uses_larger_cost() -> None:
    lsdb = LinkStateDatabase("A")
    lsdb.install(lsa("A", 1, ("AB", "B", 1, True)))
    lsdb.install(lsa("B", 2, ("AB", "A", 9, True)))

    assert lsdb.to_topology()["links"] == [
        {"id": "AB", "source": "A", "target": "B", "cost": 9, "active": True}
    ]


def test_routing_table_is_computed_from_lsdb_contents_only() -> None:
    # The LSDB still believes BD is up (stale information); SPF must use it.
    lsdb = LinkStateDatabase("A")
    lsdb.install(lsa("A", 1, ("AB", "B", 1, True), ("AC", "C", 2, True)))
    lsdb.install(lsa("B", 1, ("AB", "A", 1, True), ("BD", "D", 1, True)))
    lsdb.install(lsa("C", 1, ("AC", "A", 2, True), ("CD", "D", 3, True)))
    lsdb.install(lsa("D", 1, ("BD", "B", 1, True), ("CD", "C", 3, True)))

    table = compute_routing_table(lsdb, "A")

    assert table["D"] == {
        "destination": "D",
        "next_hop": "B",
        "path": ["A", "B", "D"],
        "cost": 2,
        "reachable": True,
    }
    assert table["A"]["cost"] == 0 and table["A"]["reachable"] is True

    # Once B's newer LSA reports BD down, the same router switches to C.
    lsdb.install(lsa("B", 2, ("AB", "A", 1, True), ("BD", "D", 1, False)))
    assert compute_routing_table(lsdb, "A")["D"]["path"] == ["A", "C", "D"]


def test_unknown_destination_is_unreachable_in_routing_table() -> None:
    lsdb = LinkStateDatabase("A")
    lsdb.install(lsa("A", 1, ("AB", "B", 1, False)))

    assert compute_routing_table(lsdb, "A")["B"] == {
        "destination": "B",
        "next_hop": None,
        "path": [],
        "cost": None,
        "reachable": False,
    }
