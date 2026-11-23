"""FastAPI application for the OSPF/Dijkstra simulator foundation."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException

from backend.models import LinkToggleRequest, RouteRequest, RouteResult, Topology
from backend.routing import shortest_path
from backend.simulation.link_manager import reset_topology, toggle_link


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_FILE = PROJECT_ROOT / "data" / "topologies" / "basic.json"


def load_initial_topology() -> dict[str, Any]:
    with TOPOLOGY_FILE.open(encoding="utf-8") as topology_file:
        topology = json.load(topology_file)
    # Validate the shared fixture at startup so malformed network data is
    # reported immediately, while retaining a JSON-compatible dict for APIs.
    return Topology(**topology).model_dump()


INITIAL_TOPOLOGY = load_initial_topology()
current_topology = reset_topology(INITIAL_TOPOLOGY)

app = FastAPI(
    title="OSPF/Dijkstra Routing Reconvergence Simulator",
    description="Starter API for a network routing reconvergence simulator.",
    version="0.1.0",
)


@app.get("/api/topology", response_model=Topology, tags=["topology"])
def get_topology() -> dict[str, Any]:
    """Return the current in-memory network topology."""

    return deepcopy(current_topology)


@app.post("/api/links/toggle", response_model=Topology, tags=["simulation"])
def post_toggle_link(request: LinkToggleRequest) -> dict[str, Any]:
    """Toggle one link between active and failed, then return the topology."""

    global current_topology
    try:
        current_topology = toggle_link(current_topology, request.link_id)
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Link '{request.link_id}' was not found.",
        ) from error
    return deepcopy(current_topology)


@app.post("/api/reset", response_model=Topology, tags=["simulation"])
def post_reset() -> dict[str, Any]:
    """Restore the in-memory topology to its initial state."""

    global current_topology
    current_topology = reset_topology(INITIAL_TOPOLOGY)
    return deepcopy(current_topology)


@app.post("/api/route", response_model=RouteResult, tags=["routing"])
def post_route(request: RouteRequest) -> dict[str, Any]:
    """Calculate the shortest valid path between two routers."""

    return shortest_path(current_topology, request.source, request.destination)
