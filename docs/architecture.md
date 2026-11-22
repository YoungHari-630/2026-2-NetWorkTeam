# Architecture

## Current foundation

```text
Browser UI (Role 3, planned)
        │ HTTP / JSON
        ▼
FastAPI application: backend/main.py
        ├── backend/models.py                  Shared request and response schema
        ├── backend/simulation/link_manager.py Thread-safe state and link event log
        ├── backend/routing/                   Role 2 implementation area (empty)
        └── data/topologies/basic.json          Startup topology fixture
```

At startup, FastAPI loads and validates the canonical topology JSON. A
thread-safe `LinkManager` holds the current copy and link state-change events
in process memory. `GET /api/topology` reads the current topology,
`POST /api/links/toggle` updates one link and records a numbered simulation
step, and `POST /api/reset` restores the initial copy and clears events.
`GET /api/simulation/events` returns those link events. `POST /api/route`
delegates to `backend/routing/dijkstra.py` when Role 2 supplies its function;
until then it returns `501`.

## Planned integration

Role 2 implements Dijkstra and routing-table generation under
`backend/routing/`, following [`api-contract.md`](api-contract.md). The API
calls `shortest_path(topology, source, destination)` for `POST /api/route`.
Role 3 builds the graph view in `frontend/`, consumes the topology endpoints,
and highlights returned paths once route calculation is available. Role 1+4
coordinates integration and can extend the current link event log with
event-by-event LSA propagation, per-router LSDB state, SPF recalculation, and
reconvergence records. Those Phase 2 behaviors are not yet implemented.

All links are undirected and have positive integer costs. Inactive links stay
in the data sent to the UI but are unavailable to route calculations.
