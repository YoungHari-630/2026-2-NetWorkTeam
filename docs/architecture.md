# Architecture

## Current foundation

```text
Browser UI (Role 3, planned)
        │ HTTP / JSON
        ▼
FastAPI application: backend/main.py
        ├── backend/models.py             Shared request and response schema
        ├── backend/simulation/link_manager.py  In-memory link toggle/reset
        ├── backend/routing/               Role 2 implementation area (empty)
        └── data/topologies/basic.json     Startup topology fixture
```

At startup, FastAPI loads and validates the canonical topology JSON. The API
holds the current copy in process memory. `GET /api/topology` reads it,
`POST /api/links/toggle` updates one link, and `POST /api/reset` restores the
initial copy. `POST /api/route` validates its request and returns `501` until
the routing implementation is integrated.

## Planned integration

Role 2 implements Dijkstra and routing-table generation under
`backend/routing/`, following [`api-contract.md`](api-contract.md). The API can
then call `shortest_path(current_topology, source, destination)` for
`POST /api/route`. Role 3 builds the graph view in `frontend/`, consumes the
topology endpoints, and highlights returned paths once route calculation is
available. Role 1+4 coordinates integration and later adds OSPF/LSA event
simulation.

All links are undirected and have positive integer costs. Inactive links stay
in the data sent to the UI but are unavailable to route calculations.
