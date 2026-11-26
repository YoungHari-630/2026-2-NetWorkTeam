# Phase 2 — Role 3 Frontend Report

**Team:** Ping Pong  
**Project:** OSPF/Dijkstra Routing Reconvergence Simulator and Visualizer  
**Branch:** `feature/phase2-frontend`  
**Base:** latest `origin/main` fetched on 2026-11-26 (`ecd06f8`)  
**Verification date:** 2026-11-26

## Implemented

- Added dynamic graph/topology controls for the 4-router starter, an 8-router
  preset, a 12-router preset, and an empty custom topology.
- Added local router/link add/delete, cost update, topology reset, JSON import
  and export. Input validation reports duplicate/empty IDs, invalid endpoints,
  self-links, and invalid costs. Edits use the separately labelled
  `TopologyMockAdapter` until a backend topology mutation API exists.
- Kept Cytoscape.js, added 8/12-node concentric layout, node selection and
  highlighting, fit/zoom buttons, draggable nodes, active/failed line styles,
  and clearer cost labels when a route is highlighted.
- Added a routing table that asks the current `/api/route` endpoint for every
  destination. It displays destination, next hop, cost, full path, and
  reachability. Local mock topologies clearly report that route calculation is
  unavailable instead of sending requests against the server's unrelated
  topology.
- Added ordered event filtering and forward playback for the server's link
  failure/recovery events. Display speed is separate from backend sequence
  time. No back/seek control is shown because the backend does not provide
  snapshots.
- Added a router LSDB view explicitly labelled Mock. It is a local topology
  projection, not independent LSDB state, and is visually described separately
  from physical link status.
- Added a Kimi diagnosis placeholder with an API-not-connected badge and
  `window.renderKimiDiagnosis(payload)` to render the agreed future display
  fields. No Kimi API or diagnosis logic was added.
- Centralized HTTP requests in `frontend/api-adapter.js`; local topology
  fixtures/validation live in `frontend/mock-adapter.js`.
- Documented the backend API handoff in
  [phase2-api-needs.md](../frontend/phase2-api-needs.md).

## Verification

- `python -m pytest` using the repository `.venv`: **28 passed**, one
  Starlette/AnyIO deprecation warning.
- JavaScript syntax checks: `app.js`, `phase2.js`, `mock-adapter.js`, and
  `api-adapter.js` passed `node --check`.
- Actual browser check: live server connection, 4-router A → B → D route at
  cost 2, routing table, AB failure and recovery, changed route while failed,
  ordered event log and next-event playback all passed. Test link events were
  cleared with `/api/reset` afterward.
- Browser mock checks: 8 routers/12 links, 12 routers/18 links, custom
  two-router topology and weighted link addition, JSON import and JSON export
  passed. UI identified these
  as Local mock and prevented route calculation against the server topology.
- Korean/English switch and server-unavailable message were checked. No
  browser Console errors were observed.
- Screenshot: the actual browser page was captured inline in the Codex task.
  The browser capture interface did not save a PNG into the repository, so
  `docs/screenshots/` does not yet contain a screenshot file.

## API and known gaps

See [the Phase 2 API handoff](../frontend/phase2-api-needs.md). The current
backend supports topology read, route, link toggle/reset, and link-event reads.
Topology persistence/edit APIs, router-local routing table API, independent
per-router LSDB API, LSA/SPF/reconvergence events, simulation snapshots, and
Kimi diagnosis API are not implemented. Consequently the frontend does not
claim real OSPF replay or independent LSDB state. Local 8/12/custom topologies
cannot use the current server route API until the backend accepts topology
updates.

## Run locally

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

In a second terminal, serve the repository root:

```powershell
python -m http.server 5500
```

Open `http://127.0.0.1:5500/frontend/`.

## Git handoff

Changes are on `feature/phase2-frontend`, based on updated `main`. No push or
pull request was created: the project instruction requires a teammate's
approval before pushing, and that approval was not present in this task.
