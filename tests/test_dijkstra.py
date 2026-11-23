"""Tests for Dijkstra paths, routing tables, failures, and invalid input."""

from copy import deepcopy

import pytest

from backend.routing.dijkstra import shortest_path
from backend.routing.routing_table import build_routing_table


@pytest.fixture
def topology() -> dict:
    return {
        "routers": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
        "links": [
            {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": True},
            {"id": "AC", "source": "A", "target": "C", "cost": 2, "active": True},
            {"id": "BD", "source": "B", "target": "D", "cost": 1, "active": True},
            {"id": "CD", "source": "C", "target": "D", "cost": 3, "active": True},
        ],
    }


def test_normal_shortest_path(topology: dict) -> None:
    assert shortest_path(topology, "A", "D") == {
        "source": "A",
        "destination": "D",
        "path": ["A", "B", "D"],
        "total_cost": 2,
        "reachable": True,
    }


def test_bd_link_failure_uses_alternate_route(topology: dict) -> None:
    failed = deepcopy(topology)
    next(link for link in failed["links"] if link["id"] == "BD")["active"] = False

    assert shortest_path(failed, "A", "D") == {
        "source": "A",
        "destination": "D",
        "path": ["A", "C", "D"],
        "total_cost": 5,
        "reachable": True,
    }


def test_bd_link_recovery_restores_original_route(topology: dict) -> None:
    recovered = deepcopy(topology)
    bd_link = next(link for link in recovered["links"] if link["id"] == "BD")
    bd_link["active"] = False
    assert shortest_path(recovered, "A", "D")["path"] == ["A", "C", "D"]

    bd_link["active"] = True
    assert shortest_path(recovered, "A", "D") == {
        "source": "A",
        "destination": "D",
        "path": ["A", "B", "D"],
        "total_cost": 2,
        "reachable": True,
    }


def test_source_destination_is_reachable_at_zero_cost(topology: dict) -> None:
    assert shortest_path(topology, "A", "A") == {
        "source": "A",
        "destination": "A",
        "path": ["A"],
        "total_cost": 0,
        "reachable": True,
    }


def test_unreachable_destination(topology: dict) -> None:
    disconnected = deepcopy(topology)
    disconnected["routers"] = [{"id": "A"}, {"id": "B"}, {"id": "C"}]
    disconnected["links"] = [
        {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": True}
    ]

    assert shortest_path(disconnected, "A", "C") == {
        "source": "A",
        "destination": "C",
        "path": [],
        "total_cost": None,
        "reachable": False,
    }


def test_routing_table_format(topology: dict) -> None:
    table = build_routing_table(topology, "A")

    assert table["A"] == {"destination": "A", "next_hop": None, "cost": 0, "path": ["A"]}
    assert table["D"] == {
        "destination": "D",
        "next_hop": "B",
        "cost": 2,
        "path": ["A", "B", "D"],
    }


def test_routing_table_unreachable_destination() -> None:
    topology = {
        "routers": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "links": [{"id": "AB", "source": "A", "target": "B", "cost": 1, "active": True}],
    }

    assert build_routing_table(topology, "A")["C"] == {
        "destination": "C",
        "next_hop": None,
        "cost": None,
        "path": [],
    }


@pytest.mark.parametrize("source,destination", [("Z", "A"), ("A", "Z")])
def test_unknown_router_raises_value_error(topology: dict, source: str, destination: str) -> None:
    with pytest.raises(ValueError, match="Unknown"):
        shortest_path(topology, source, destination)


@pytest.mark.parametrize("invalid_cost", [0, -1, 1.5, True])
def test_invalid_link_cost_raises_value_error(topology: dict, invalid_cost: object) -> None:
    invalid = deepcopy(topology)
    invalid["links"][0]["cost"] = invalid_cost

    with pytest.raises(ValueError, match="positive integers"):
        shortest_path(invalid, "A", "D")


def test_unknown_routing_table_source_raises_value_error(topology: dict) -> None:
    with pytest.raises(ValueError, match="Unknown source router"):
        build_routing_table(topology, "Z")
