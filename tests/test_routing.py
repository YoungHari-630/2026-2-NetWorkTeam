"""Tests for the Dijkstra routing implementation and route API."""

from backend.main import app
from backend.routing import build_routing_table, shortest_path
from fastapi.testclient import TestClient


TOPOLOGY = {
    "routers": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
    "links": [
        {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": True},
        {"id": "AC", "source": "A", "target": "C", "cost": 2, "active": True},
        {"id": "BD", "source": "B", "target": "D", "cost": 1, "active": True},
        {"id": "CD", "source": "C", "target": "D", "cost": 3, "active": True},
    ],
}


def test_shortest_path_returns_expected_route() -> None:
    result = shortest_path(TOPOLOGY, "A", "D")

    assert result == {
        "source": "A",
        "destination": "D",
        "path": ["A", "B", "D"],
        "total_cost": 2,
        "reachable": True,
    }


def test_shortest_path_handles_unreachable_destination() -> None:
    disconnected_topology = {
        "routers": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "links": [{"id": "AB", "source": "A", "target": "B", "cost": 5, "active": True}],
    }

    assert shortest_path(disconnected_topology, "A", "C") == {
        "source": "A",
        "destination": "C",
        "path": [],
        "total_cost": None,
        "reachable": False,
    }


def test_build_routing_table_includes_all_destinations() -> None:
    table = build_routing_table(TOPOLOGY, "A")

    assert set(table) == {"A", "B", "C", "D"}
    assert table["A"]["path"] == ["A"]
    assert table["D"]["path"] == ["A", "B", "D"]
    assert table["D"]["cost"] == 2


def test_route_api_returns_shortest_path() -> None:
    with TestClient(app) as client:
        response = client.post("/api/route", json={"source": "A", "destination": "D"})

    assert response.status_code == 200
    assert response.json() == {
        "source": "A",
        "destination": "D",
        "path": ["A", "B", "D"],
        "total_cost": 2,
        "reachable": True,
    }
