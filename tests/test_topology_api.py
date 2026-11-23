"""Tests for the shared topology and link-state API foundation."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        test_client.post("/api/reset")
        yield test_client
        test_client.post("/api/reset")


def test_get_topology_returns_basic_network(client: TestClient) -> None:
    response = client.get("/api/topology")

    assert response.status_code == 200
    topology = response.json()
    assert [router["id"] for router in topology["routers"]] == ["A", "B", "C", "D"]
    assert [(link["id"], link["cost"]) for link in topology["links"]] == [
        ("AB", 1),
        ("AC", 2),
        ("BD", 1),
        ("CD", 3),
    ]
    assert all(link["active"] for link in topology["links"])


def test_toggle_link_changes_state_and_returns_full_topology(client: TestClient) -> None:
    response = client.post("/api/links/toggle", json={"link_id": "AB"})

    assert response.status_code == 200
    topology = response.json()
    assert len(topology["routers"]) == 4
    assert next(link for link in topology["links"] if link["id"] == "AB")["active"] is False

    restored = client.post("/api/links/toggle", json={"link_id": "AB"})
    assert next(link for link in restored.json()["links"] if link["id"] == "AB")["active"] is True


def test_toggle_unknown_link_returns_404(client: TestClient) -> None:
    response = client.post("/api/links/toggle", json={"link_id": "missing"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Link 'missing' was not found."


def test_reset_restores_initial_topology(client: TestClient) -> None:
    client.post("/api/links/toggle", json={"link_id": "CD"})

    response = client.post("/api/reset")

    assert response.status_code == 200
    assert all(link["active"] for link in response.json()["links"])


def test_route_endpoint_returns_shortest_path(client: TestClient) -> None:
    response = client.post(
        "/api/route",
        json={"source": "A", "destination": "D"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "source": "A",
        "destination": "D",
        "path": ["A", "B", "D"],
        "total_cost": 2,
        "reachable": True,
    }


def test_route_endpoint_validates_request_shape(client: TestClient) -> None:
    response = client.post("/api/route", json={"source": "A"})

    assert response.status_code == 422
