# Phase 2 frontend API handoff

The frontend currently uses the implemented FastAPI endpoints for topology
read, route calculation, link toggle/reset, and recorded link events. The
topology editor switches to a separately labelled local mock adapter because
there is no topology mutation API. The mock adapter never reports its state as
server-backed. Routing calculation stays disabled for those local topologies:
the current route API always evaluates the server's in-memory topology.

## Implemented endpoints used by the frontend

| Method | Path | Current frontend use |
| --- | --- | --- |
| `GET` | `/api/topology` | Load current physical topology |
| `POST` | `/api/route` | Request shortest path; routing table requests one destination per router |
| `POST` | `/api/links/toggle` | Fail/recover a selected link |
| `POST` | `/api/reset` | Reset server topology and event history |
| `GET` | `/api/simulation/events` | Load ordered link failure/recovery records |

Event `step` is simulation sequence order, not elapsed simulation or wall-clock
time. Playback in the UI only controls when a stored record is highlighted.
Only `link_failed` and `link_restored` are currently emitted.

## Requested topology API

To persist topology edits, please provide a validated endpoint such as
`PUT /api/topology` accepting the existing topology shape:

```json
{
  "routers": [{"id": "R1"}, {"id": "R2"}],
  "links": [{"id": "R1-R2", "source": "R1", "target": "R2", "cost": 3, "active": true}]
}
```

The response should return the normalized current topology. Validation should
reject duplicate IDs, dangling endpoints, self-links, non-positive/non-integer
costs, and non-boolean link state with `422`. The route and event APIs should
then operate on this topology. A named preset catalog endpoint is optional;
the frontend currently supplies local 4/8/12-router presets.

## Requested routing table API

The frontend currently calls `POST /api/route` for every destination. A
dedicated `GET /api/routers/{router_id}/routes` would reduce requests and
return one consistent snapshot:

```json
{
  "router_id": "R1",
  "entries": [
    {"destination":"R1","next_hop":null,"total_cost":0,"path":["R1"],"reachable":true},
    {"destination":"R2","next_hop":"R2","total_cost":3,"path":["R1","R2"],"reachable":true},
    {"destination":"R3","next_hop":null,"total_cost":null,"path":[],"reachable":false}
  ]
}
```

The response must be based on the routing state of the selected router (or
clearly document if it is a centralized Dijkstra view).

## Requested OSPF simulation and LSDB APIs

No OSPF event stream, per-router LSDB, or simulation snapshot endpoint exists
yet. The frontend does not invent LSA/SPF events. To support real event
playback, provide an ordered event list or stream with stable event IDs,
simulation time/step, event type, router ID, related link, and event details.
For replay and seeking, provide a snapshot keyed by event sequence. Suggested
event types are `lsa_generation`, `lsa_transmission`, `lsa_reception`,
`lsdb_update`, `spf_calculation`, `routing_table_update`, and `reconvergence`.

Suggested read endpoints:

| Method | Path | Response content |
| --- | --- | --- |
| `GET` | `/api/simulation/events` | Extend current events with the event types/fields above and snapshots or snapshot references |
| `GET` | `/api/routers/{router_id}/lsdb` | Router-local LSA origin, sequence, advertised links, link state/cost, update time |
| `GET` | `/api/simulation/snapshot?step={step}` | Physical topology, each router's LSDB/routes, partition and convergence state |
| `POST` | `/api/simulation/start` | Start a run from a supplied link failure/recovery action |
| `POST` | `/api/simulation/reset` | Restore the initial run snapshot |

The current LSDB panel is explicitly marked **Mock** and shows a local
topology-derived projection, not independent router knowledge. The current
playback supports forward display through the backend's stored link events;
it cannot rewind or claim OSPF reconvergence.

## Kimi diagnosis integration

The frontend exposes `window.renderKimiDiagnosis(payload)` for a future UI
integration. Expected fields are `type`, `location`, `evidence`,
`more_info_needed`, `uncertainty`, and `recovery_suggestion`. The UI currently
shows an API-not-connected state and placeholder fields only.
