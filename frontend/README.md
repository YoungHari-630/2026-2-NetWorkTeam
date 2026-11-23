# Frontend

Role 3's browser interface uses plain HTML, CSS, JavaScript, and Cytoscape.js.
It displays the shared topology, link costs and states, route controls, and
link failure/recovery controls. It does not implement Dijkstra in JavaScript.

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

See ../docs/api-contract.md for the topology schema, API examples, and error
responses. See ../docs/ui-test.md for the manual verification checklist.
