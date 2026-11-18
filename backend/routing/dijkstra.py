"""Dijkstra shortest-path implementation for the shared network topology."""

from __future__ import annotations

from heapq import heappop, heappush

TopologyData = dict


def _validated_graph(topology: TopologyData) -> dict[str, dict[str, int]]:
    """Validate topology data and build an active, bidirectional weighted graph."""

    if not isinstance(topology, dict):
        raise ValueError("Topology must be a dictionary.")

    routers = topology.get("routers")
    links = topology.get("links")
    if not isinstance(routers, list) or not isinstance(links, list):
        raise ValueError("Topology must contain routers and links lists.")

    router_ids: list[str] = []
    for router in routers:
        if not isinstance(router, dict) or not isinstance(router.get("id"), str):
            raise ValueError("Each router must have a string id.")
        if not router["id"]:
            raise ValueError("Router ids must not be empty.")
        if router["id"] in router_ids:
            raise ValueError("Router ids must be unique.")
        router_ids.append(router["id"])

    graph: dict[str, dict[str, int]] = {router_id: {} for router_id in router_ids}

    for link in links:
        if not isinstance(link, dict):
            raise ValueError("Each link must be a dictionary.")

        source = link.get("source")
        destination = link.get("target")
        cost = link.get("cost")

        if source not in graph or destination not in graph:
            raise ValueError("Link endpoints must refer to existing routers.")
        if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
            raise ValueError("Link costs must be positive integers.")

        if link.get("active") is False:
            continue
        if not isinstance(link.get("active"), bool):
            raise ValueError("Link active state must be a boolean.")

        if destination not in graph[source] or cost < graph[source][destination]:
            graph[source][destination] = cost
        if source not in graph[destination] or cost < graph[destination][source]:
            graph[destination][source] = cost

    return graph


def shortest_path(topology: TopologyData, source: str, destination: str) -> dict:
    """Return the shortest path and cost using Dijkstra's algorithm."""

    graph = _validated_graph(topology)

    if source not in graph:
        raise ValueError(f"Unknown source router: {source}")
    if destination not in graph:
        raise ValueError(f"Unknown destination router: {destination}")

    if source == destination:
        return {
            "source": source,
            "destination": destination,
            "path": [source],
            "total_cost": 0,
            "reachable": True,
        }

    distances = {router: float("inf") for router in graph}
    previous: dict[str, str | None] = {router: None for router in graph}
    distances[source] = 0
    queue: list[tuple[int, str]] = [(0, source)]

    while queue:
        current_cost, current = heappop(queue)
        if current_cost != distances[current]:
            continue
        if current == destination:
            break

        for neighbor, cost in graph[current].items():
            candidate = current_cost + cost
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                previous[neighbor] = current
                heappush(queue, (candidate, neighbor))

    if distances[destination] == float("inf"):
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
