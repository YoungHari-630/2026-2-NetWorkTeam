# Frontend

Role 3's browser interface uses plain HTML, CSS, JavaScript, and Cytoscape.js.
It includes dynamic 4/8/12-router topologies, a local topology editor, routing
table, backend link-event log/playback, an explicitly mock LSDB projection, and
a Kimi diagnosis payload display hook. It does not implement Dijkstra or OSPF
in JavaScript.

## Run locally

Start the API from the repository root:

    python -m uvicorn backend.main:app --reload

In a second terminal, serve the repository root:

    python -m http.server 5500

Open http://127.0.0.1:5500/frontend/. The API base URL is
http://127.0.0.1:8000. The browser uses the API for topology, route, link
toggle, and reset requests. If the frontend and API use different origins,
FastAPI must allow the frontend origin through CORS. Before the route API is
available, the default A-to-D result is labelled as an example preview.

The 4-router topology uses the live API. The 8/12-router presets, custom
topologies, and imported/edited JSON use `mock-adapter.js` until a topology
mutation API exists. The UI marks those views as local mock and does not send
route requests for them. The LSDB panel is also a mock projection; no LSA/SPF
animation is presented as a real OSPF run.

See [../docs/api-contract.md](../docs/api-contract.md) for the current API and
[../docs/frontend/phase2-api-needs.md](../docs/frontend/phase2-api-needs.md)
for the requested backend handoff. See [../docs/ui-test.md](../docs/ui-test.md)
for browser verification notes.
