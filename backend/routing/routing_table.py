"""Routing table generation for the network simulator."""

from backend.routing.dijkstra import shortest_path

TopologyData = dict


def build_routing_table(topology: TopologyData, source: str) -> dict[str, dict]:
    """Generate one routing entry for every router in the topology.

    Each entry contains destination, next_hop, cost, and path. The source route
    has cost 0 and a null next hop. Unreachable destinations have null cost,
    null next hop, and an empty path.
    """

    routers = topology.get("routers") if isinstance(topology, dict) else None
    if not isinstance(routers, list):
        raise ValueError("Topology must contain a routers list.")

    router_ids = [router.get("id") for router in routers if isinstance(router, dict)]
    if source not in router_ids:
        raise ValueError(f"Unknown source router: {source}")

    table: dict[str, dict] = {}
    for destination in router_ids:
        route = shortest_path(topology, source, destination)

        if destination == source:
            next_hop = None
            cost = 0
        elif route["reachable"]:
            next_hop = route["path"][1] if len(route["path"]) > 1 else None
            cost = route["total_cost"]
        else:
            next_hop = None
            cost = None

        table[destination] = {
            "destination": destination,
            "next_hop": next_hop,
            "cost": cost,
            "path": route["path"],
        }

    return table
