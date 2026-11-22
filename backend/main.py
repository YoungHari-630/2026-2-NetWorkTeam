"""FastAPI application for the OSPF/Dijkstra simulator."""

import importlib
import json
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models import (
    LinkToggleRequest,
    RouteRequest,
    RouteResult,
    SimulationEventList,
    Topology,
)
from backend.simulation.link_manager import LinkManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOPOLOGY_FILE = PROJECT_ROOT / "data" / "topologies" / "basic.json"


def load_initial_topology() -> dict[str, Any]:
    with TOPOLOGY_FILE.open(encoding="utf-8") as topology_file:
        topology = json.load(topology_file)
    # Validate the shared fixture at startup while keeping a JSON-compatible
    # dict for Role 2's routing interface and the HTTP API.
    return Topology(**topology).model_dump()


INITIAL_TOPOLOGY = load_initial_topology()
link_manager = LinkManager(INITIAL_TOPOLOGY)

app = FastAPI(
    title="OSPF/Dijkstra Routing Reconvergence Simulator",
    description="API for topology state, link events, and route calculation.",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/topology", response_model=Topology, tags=["topology"])
def get_topology() -> dict[str, Any]:
    """Return the current in-memory network topology."""

    return link_manager.get_topology()


@app.post("/api/links/toggle", response_model=Topology, tags=["simulation"])
def post_toggle_link(request: LinkToggleRequest) -> dict[str, Any]:
    """Toggle one link between active and failed, then return the topology."""

    try:
        return link_manager.toggle_link(request.link_id)
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail=f"Link '{request.link_id}' was not found.",
        ) from error


@app.post("/api/reset", response_model=Topology, tags=["simulation"])
def post_reset() -> dict[str, Any]:
    """Restore the initial topology and clear link-state simulation events."""

    return link_manager.reset()


@app.get(
    "/api/simulation/events",
    response_model=SimulationEventList,
    tags=["simulation"],
)
def get_simulation_events() -> dict[str, Any]:
    """Return recorded link failure and recovery events in step order."""

    return {"events": link_manager.get_events()}


def _get_shortest_path() -> Callable[..., Any] | None:
    """Load Role 2's implementation without adding a second algorithm here."""

    module_name = "backend.routing.dijkstra"
    try:
        routing_module = importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            return None
        raise
    return getattr(routing_module, "shortest_path", None)


@app.post("/api/route", response_model=RouteResult, tags=["routing"])
def post_route(request: RouteRequest) -> dict[str, Any]:
    """Delegate route calculation to Role 2 when its module is available."""

    topology = link_manager.get_topology()
    router_ids = {router["id"] for router in topology["routers"]}
    for router_id in (request.source, request.destination):
        if router_id not in router_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Router '{router_id}' was not found.",
            )

    shortest_path = _get_shortest_path()
    if shortest_path is None:
        raise HTTPException(
            status_code=501,
            detail=(
                "Route calculation is not implemented yet. "
                "Role 2 will provide the routing functions."
            ),
        )

    return shortest_path(topology, request.source, request.destination)
