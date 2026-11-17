"""Dijkstra shortest-path helpers for the routing simulator."""

from __future__ import annotations

from math import inf


def _neighbors(topology: dict) -> dict[str, dict[str, int]]:
    """Build an adjacency map using only active undirected links."""

    graph: dict[str, dict[str, int]] = {
        router["id"]: {} for router in topology.get("routers", [])
    }

    for link in topology.get("links", []):
        if not link.get("active", False):
            continue

        source = link["source"]
        target = link["target"]
        if source not in graph or target not in graph:
            continue

        cost = int(link["cost"])
        if target not in graph[source] or cost < graph[source][target]:
            graph[source][target] = cost
        if source not in graph[target] or cost < graph[target][source]:
            graph[target][source] = cost

    return graph


def shortest_path(topology: dict, source: str, destination: str) -> dict[str, object]:
    """Return the best path and cost from source to destination.

    The result follows the contract in docs/api-contract.md. Unreachable nodes
    are represented as {
        "reachable": False,
        "path": [],
        "total_cost": None,
    }.
    """

    if source == destination:
        return {
            "source": source,
            "destination": destination,
            "path": [source],
            "total_cost": 0,
            "reachable": True,
        }

    graph = _neighbors(topology)
    if source not in graph or destination not in graph:
        return {
            "source": source,
            "destination": destination,
            "path": [],
            "total_cost": None,
            "reachable": False,
        }

    distances: dict[str, float] = {router: inf for router in graph}
    previous: dict[str, str | None] = {router: None for router in graph}
    distances[source] = 0
    visited: set[str] = set()

    while len(visited) < len(graph):
        current = None
        current_distance = inf
        for router, distance in distances.items():
            if router in visited:
                continue
            if distance < current_distance:
                current = router
                current_distance = distance

        if current is None or current_distance == inf:
            break

        if current == destination:
            break

        visited.add(current)
        for neighbor, cost in graph[current].items():
            if neighbor in visited:
                continue
            candidate = current_distance + cost
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = current

    if destination not in distances or distances[destination] == inf:
        return {
            "source": source,
            "destination": destination,
            "path": [],
            "total_cost": None,
            "reachable": False,
        }

    path: list[str] = []
    current: str | None = destination
    while current is not None:
        path.append(current)
        current = previous[current]
    path.reverse()

    return {
        "source": source,
        "destination": destination,
        "path": path,
        "total_cost": int(distances[destination]),
        "reachable": True,
    }


def build_routing_table(topology: dict, source: str) -> dict[str, dict[str, object]]:
    """Build a per-destination routing table for a given source router."""

    routers = [router["id"] for router in topology.get("routers", [])]
    return {
        router_id: shortest_path(topology, source, router_id)
        for router_id in routers
    }
