# API and Data Contract

This document is the shared contract for the backend and team feature branches.
The current implementation includes topology reads, link state toggles, and
reset. Dijkstra routing and the browser UI are planned work.

## Topology JSON

The canonical starter topology lives in `data/topologies/basic.json` and is
loaded by the API at startup. A topology has a `routers` array and a `links`
array:

```json
{
  "routers": [{"id": "A"}, {"id": "B"}],
  "links": [
    {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": true}
  ]
}
```

Router IDs and link IDs are non-empty, case-sensitive strings. Link `source`
and `target` refer to router IDs. Each link is **undirected**: routing code must
make it traversable in both directions. `cost` is a positive integer, and
`active` must be a boolean. Inactive links remain in the topology response but
must not be used to calculate routes.

## API

Local base URL: `http://127.0.0.1:8000`

| Method | Path | Request | Current behavior |
| --- | --- | --- | --- |
| `GET` | `/api/topology` | None | Returns the full current topology. |
| `POST` | `/api/links/toggle` | `{"link_id": "AB"}` | Inverts that link's `active` value and returns the full topology. |
| `POST` | `/api/reset` | None | Restores all routers and links to the startup topology and returns it. |
| `POST` | `/api/route` | `{"source": "A", "destination": "D"}` | Returns HTTP `501` until Role 2's route calculation is integrated. |

### Topology response example

`GET /api/topology`, `POST /api/links/toggle`, and `POST /api/reset` return the
same topology shape:

```json
{
  "routers": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
  "links": [
    {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": true},
    {"id": "AC", "source": "A", "target": "C", "cost": 2, "active": true},
    {"id": "BD", "source": "B", "target": "D", "cost": 1, "active": true},
    {"id": "CD", "source": "C", "target": "D", "cost": 3, "active": true}
  ]
}
```

### Route result expected after Role 2 integration

This is the expected response contract, **not** an implemented algorithm
result. With the initial sample network, `POST /api/route` for A to D should
eventually return:

```json
{
  "source": "A",
  "destination": "D",
  "path": ["A", "B", "D"],
  "total_cost": 2,
  "reachable": true
}
```

Role 3 should treat `/api/route` as unavailable while it returns `501` and
handle API errors as described below.

## Role 2 routing interfaces

Implement these in `backend/routing/` and add focused algorithm tests. Keep
`backend/main.py` as the API integration point; coordinate any signature or
response changes with the team before changing this contract.

```python
def shortest_path(topology, source, destination):
    ...

def build_routing_table(topology, source):
    ...
```

`topology` uses the schema above. Only active, undirected links can be used.
The shortest path result must follow the route result shape above. For an
unreachable destination, return `reachable: false`, `path: []`, and
`total_cost: null`. The routing table should cover every router ID, representing
unreachable destinations consistently with the same convention. Handle
`source == destination` as a reachable zero-cost path containing just the
source.

## Role 3 API use

Role 3's local UI can call the API at `http://127.0.0.1:8000`:

```javascript
const topologyResponse = await fetch("http://127.0.0.1:8000/api/topology");
const topology = await topologyResponse.json();

const toggleResponse = await fetch("http://127.0.0.1:8000/api/links/toggle", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ link_id: "AB" }),
});
const updatedTopology = await toggleResponse.json();
```

The toggle endpoint returns the full updated topology, so the UI can redraw
from that response. If a frontend dev server uses a different origin, enable
that origin in FastAPI CORS configuration as a coordinated backend change.
Route controls can be wired after `/api/route` is implemented.

## Failure and recovery rules

- Toggling a known link flips `active` (`true` to `false`, or `false` to
  `true`). It does not delete the link or change its cost or endpoints.
- Links are undirected; a link failure removes availability in both directions.
- Reset restores the exact initial topology, including all links active and
  original costs.
- The starter server keeps state in process memory. Restarting it also restores
  the initial topology; multi-process persistence is out of scope for this
  foundation.

## Error responses

Errors use FastAPI's JSON `detail` field:

| Status | Meaning | Example |
| --- | --- | --- |
| `404` | Requested link ID does not exist. | `{"detail":"Link 'XY' was not found."}` |
| `422` | Request JSON is missing a required field or has an invalid type/value. | FastAPI validation detail array |
| `501` | Route calculation has not been implemented yet. | `{"detail":"Route calculation is not implemented yet. Role 2 will provide the routing functions."}` |
