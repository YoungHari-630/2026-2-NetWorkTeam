# OSPF Engine Public Interface

All names below can be imported from `backend.ospf`.

```python
from backend.ospf import OSPFSimulator, SimulationConfig
```

## Initialization

```python
OSPFSimulator(topology: dict, config: SimulationConfig | None = None)
```

`topology` uses the shared format from `docs/api-contract.md`
(`{"routers": [{"id"}], "links": [{"id", "source", "target", "cost", "active"}]}`).
Router and link IDs can be any non-empty, unique strings. The constructor
raises `ValueError` for duplicate IDs, unknown endpoints, self-loops,
non-positive or non-integer costs, and non-boolean `active` values. The input
dict is copied and never changed.

```python
SimulationConfig(
    detection_delay=0,      # link change -> endpoints originate new LSAs
    transmission_delay=1,   # default one-hop LSA delay
    link_delays={},         # {link_id: delay} overrides per link
    spf_delay=0,            # LSDB change -> SPF run (several changes share one run)
    max_events=100_000,     # safety limit for run_until_idle()
)
```

All delays are non-negative numbers in virtual time units. Integers give the
most readable timestamps.

## Link changes

Each method schedules an event `delay` time units after the current
simulation time and returns its event ID (e.g. `"E00001"`). Nothing happens
until the event is processed by `step()`, `run_until()` or `run_until_idle()`.

| Method | Effect when processed |
| --- | --- |
| `fail_link(link_id, delay=0)` | Link becomes inactive; endpoints detect it after `detection_delay`. |
| `recover_link(link_id, delay=0)` | Link becomes active; endpoints re-advertise it and run a database exchange over it. |
| `change_link_cost(link_id, cost, delay=0)` | Link cost changes; endpoints re-advertise it. |
| `toggle_link(link_id, delay=0)` | `fail_link` if the link is currently up, else `recover_link`. Mirrors `POST /api/links/toggle`. |

An unknown `link_id` raises `KeyError`, which matches `LinkManager`. A bad
`cost` or `delay` raises `ValueError`. A change that does nothing (for
example failing a link that is already down) is recorded as
`link_change_ignored` and does not start a reconvergence episode.

## Stepping and running

| Method | Returns |
| --- | --- |
| `step()` | `{"event": <pending-event dict>, "records": [<history records>]}` for exactly one processed event, or `None` if the queue is empty. |
| `run_until(time)` | List of `step()` results for every event with `event.time <= time`. The clock is then set to `time`. |
| `run_until_idle(max_events=None)` | List of `step()` results until the queue is empty. Raises `RuntimeError` after `max_events` (default `config.max_events`). |

## Reset

`reset()` restores the initial topology, LSDBs, routing tables, sequence
numbers and clock. It clears the queue and the history, and returns the new
snapshot. The configuration is kept.

## Reading state

| Member | Returns |
| --- | --- |
| `snapshot(include_history=True)` | Full JSON-serializable state (see `data-formats.md`). |
| `time` | Current virtual time. |
| `router_ids` | Router IDs in topology order. |
| `config` | The `SimulationConfig`. |
| `get_topology()` | Copy of the physical topology. |
| `get_lsdb(router_id)` | That router's `LinkStateDatabase` (treat it as read-only). |
| `get_routing_table(router_id)` | `{destination: route entry}` copy. |
| `get_history()` | Copy of all processed history records. |
| `get_pending_events()` | Pending events in processing order. |
| `is_converged()` | `bool`, using the convergence policy in `README.md`. |
| `convergence_status()` | The `convergence` part of the snapshot. |
| `partition_status()` | The `partition` part of the snapshot. |

All returned dicts are defensive copies. Changing them does not affect the
simulator.

## Lower-level building blocks

| Name | Purpose |
| --- | --- |
| `LinkStateAdvertisement` / `LSA`, `AdvertisedLink` | Immutable LSA model with `to_dict()` / `from_dict()`, `is_newer_than()`. |
| `originate_router_lsa(router_id, seq, links, timestamp)` | Builds a router's LSA from its own interfaces. |
| `LinkStateDatabase` | `install(lsa) -> InstallResult`, `classify`, `get`, `lsas`, `sequence_summary`, `to_topology`, `to_dict`. |
| `InstallResult` | `INSTALLED`, `DUPLICATE`, `OUTDATED`. |
| `compute_routing_table(lsdb, router_id)` | SPF on one LSDB, reusing `build_routing_table`. |
| `EventQueue`, `EventType`, `ScheduledEvent` | Deterministic event queue. |

## Suggested REST integration (for the team leader)

This is only a suggestion. The engine does not change any existing endpoint,
and none of these endpoints exist yet.

```python
simulator = OSPFSimulator(INITIAL_TOPOLOGY)           # next to link_manager

# POST /api/ospf/links/toggle {"link_id"}  -> simulator.toggle_link(link_id); return snapshot
# POST /api/ospf/step                      -> simulator.step(); return snapshot
# POST /api/ospf/run                       -> simulator.run_until_idle(); return snapshot
# POST /api/ospf/reset                     -> simulator.reset()
# GET  /api/ospf/snapshot                  -> simulator.snapshot()
```

Notes:

- `KeyError` from link methods should map to HTTP 404, as for
  `/api/links/toggle`.
- `OSPFSimulator` is not thread-safe. FastAPI runs sync endpoints in a
  thread pool, so wrap calls in a `threading.RLock`, as `LinkManager` does.
- The OSPF simulator keeps its own physical topology. Either make it the
  single source of truth, or keep it in sync with `LinkManager` by calling
  the matching simulator method whenever a link is toggled.
- `snapshot(include_history=False)` keeps responses small. History can be
  served from a separate endpoint.
