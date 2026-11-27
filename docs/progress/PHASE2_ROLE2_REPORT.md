# Phase 2 — Role 2 Report: OSPF Reconvergence Simulation

**Project:** OSPF/Dijkstra Routing Reconvergence Simulator and Visualizer
**Team:** Ping Pong
**Date:** 2026-11-27
**Branch:** `feature/phase2-ospf` (created from `main` at `ecd06f8`)

## 1. Summary

This phase adds a simplified, single-area, OSPF-style link-state simulation
engine in `backend/ospf/`. It is event-driven and fully deterministic. The
features below are covered by automated tests:

- An independent LSDB for each router, filled from the initial topology.
- Router-LSAs with origin, sequence number, timestamp, and per-link
  neighbor, cost and status.
- Hop-by-hop flooding with configurable delays for each link.
- Rejection of duplicate and outdated LSAs.
- A virtual clock and an event queue with a documented ordering rule for
  events at the same time.
- SPF on each router's *own* LSDB, reusing the existing Dijkstra and
  routing-table code.
- Convergence detection, with network partitions reported separately.
- Reconvergence times measured in virtual time.
- JSON-serializable snapshots.

The engine does not depend on FastAPI or the frontend. No API endpoint,
shared model or frontend file was changed.

## 2. Preparation and baseline

- The working tree was clean on `feature/phase2-ospf`. The branch was
  already up to date with `origin/feature/phase2-ospf` at `main`'s head
  `ecd06f8`, so no uncommitted work needed preserving.
- I inspected the existing code (`backend/main.py`, `backend/models.py`,
  `backend/routing/*`, `backend/simulation/link_manager.py`), the topology
  JSON, the docs and the tests.
- Baseline: `python -m pytest` → **28 passed**, 6 warnings, 0 failed. All
  warnings are deprecation notices from FastAPI/Starlette dependencies
  running on Python 3.14.4.

## 3. Files

### Added

| File | Purpose |
| --- | --- |
| `backend/ospf/__init__.py` | Public exports |
| `backend/ospf/models.py` | `SimulationConfig`, `RouteEntry`, topology validation, connected components |
| `backend/ospf/lsa.py` | `AdvertisedLink`, `LinkStateAdvertisement`, `originate_router_lsa` |
| `backend/ospf/lsdb.py` | `LinkStateDatabase` (one per router), `InstallResult`, two-way-checked local topology |
| `backend/ospf/event_queue.py` | `EventType`, `ScheduledEvent`, deterministic `EventQueue` |
| `backend/ospf/simulator.py` | `OSPFSimulator`, `compute_routing_table` |
| `backend/ospf/demo.py` | Command-line trace; regenerates documentation examples |
| `data/topologies/ring8.json` | 8-router ring with two chords |
| `data/topologies/mesh12.json` | 12-router mesh with non-letter router IDs (city names) and a stub router |
| `tests/test_ospf_lsa_lsdb.py` | 10 tests: LSA model, LSDB, two-way check, local SPF |
| `tests/test_ospf_event_queue.py` | 6 tests: ordering policy |
| `tests/test_ospf_simulator.py` | 34 tests: simulation behaviour |
| `docs/ospf/README.md` | Design, protocol model, ordering and convergence policies, limitations |
| `docs/ospf/public-interface.md` | Python interface and REST integration notes |
| `docs/ospf/data-formats.md` | Snapshot, event, history, LSA formats |
| `docs/ospf/examples/*.json` | 5 real outputs of the BD-failure scenario |
| `docs/progress/PHASE2_ROLE2_REPORT.md` | This report |

### Modified

| File | Change |
| --- | --- |
| `README.md` | OSPF feature status, project tree, test/demo note |

### Not modified

`frontend/*`, `backend/main.py`, `backend/models.py`,
`backend/routing/*`, `backend/simulation/*`, `docs/api-contract.md`,
`data/topologies/basic.json`, and all existing tests.

## 4. Implementation details

Full design: [`docs/ospf/README.md`](../ospf/README.md).

- **LSDB per router.** `OSPFSimulator` holds a dict of separate
  `LinkStateDatabase` objects. Initially, every router in a physically
  connected component receives the sequence-1 LSA of every router in the
  same component. Routers in other components receive nothing.
- **LSA.** One Router-LSA per router lists all of its interfaces. A
  higher sequence number means a newer LSA. `install()` returns
  `INSTALLED`, `DUPLICATE` or `OUTDATED`, and only `INSTALLED` changes the
  database.
- **Flooding.** A router sends an LSA on the interfaces that its own LSA
  says are up, except the interface it arrived on. Rejected LSAs are not
  re-flooded, so flooding always ends. An LSA sent on a link that is down,
  or in transit when the link fails, is dropped. When an interface comes
  back up, the router sends its whole LSDB over it (simplified database
  exchange), which heals partitions.
- **Events.** The heap key is `(time, type priority, insertion order)`.
  Priorities: link changes < LSA generation < LSA reception < SPF.
  `step()` processes one event; `run_until(t)` and `run_until_idle()`
  process several. No real sleep is used.
- **SPF.** `LinkStateDatabase.to_topology()` builds the router's local view.
  A link is kept only if both endpoints advertise it as up (two-way check).
  This view is passed to the existing `build_routing_table`, which uses
  `shortest_path`. Several LSDB changes that arrive before an SPF runs share
  one SPF run. Routing table entries contain `destination`, `next_hop`,
  `path`, `cost` and `reachable`.
- **Convergence.** The network is converged when three conditions hold:
  1. No pending event can still change state.
  2. In each physical component, every router holds the latest LSA of every
     other router in the component, and each router's own LSA matches its
     real interfaces.
  3. Every routing table was computed from the router's current LSDB.

  An episode starts at the first change that happens while the network is
  converged and ends when it is converged again. Its duration is measured
  in virtual time. Partition status is reported on its own: a network can be
  converged and partitioned at the same time.
- **Scalability.** Nothing is hard-coded to A–D. Tests use networks of 4,
  6 (line), 8 and 12 routers.

## 5. Execution instructions

```bash
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
python -m pytest                          # whole suite
python -m pytest tests/test_ospf_*.py     # OSPF tests only
python -m backend.ospf.demo               # trace of a BD failure on basic.json
python -m backend.ospf.demo --topology data/topologies/mesh12.json --fail GWJ-JEJ
python -m backend.ospf.demo --write-examples docs/ospf/examples   # refresh examples
```

```python
from backend.ospf import OSPFSimulator, SimulationConfig
sim = OSPFSimulator(topology, SimulationConfig(transmission_delay=1))
sim.fail_link("BD")
sim.step()              # one event
sim.run_until_idle()    # until the queue is empty
sim.snapshot()          # JSON-serializable state
```

## 6. Test results

Command: `python -m pytest` with `.venv` (Python 3.14.4, pytest 8.4.2),
on Linux (WSL2).

Result: **78 passed, 0 failed**, 6 warnings. These are the 28 original tests
plus 50 new OSPF tests. The warnings are the same dependency deprecation
warnings as in the baseline.

| Requirement | Tests (in `tests/test_ospf_*.py`) |
| --- | --- |
| Initial LSDB consistency | `test_initial_lsdbs_are_consistent_and_converged`, `test_lsdbs_are_independent_objects`, `test_initially_partitioned_topology_does_not_share_lsas` |
| Single failure and recovery | `test_single_link_failure_reconverges_to_alternate_path`, `test_link_recovery_restores_original_route` |
| Multiple failures | `test_multiple_link_failures`, `test_simultaneous_failures_on_one_router_are_coalesced`, `test_ring8_multiple_failures_and_cost_changes` |
| Link-cost changes | `test_link_cost_change_is_advertised_and_changes_routes`, `test_ring8_multiple_failures_and_cost_changes` |
| Propagation across routers | `test_lsa_propagates_hop_by_hop_across_multiple_routers` (6-router line; installation times 0, 2, 4, 6, 8) |
| Duplicate and outdated rejection | `test_lsdb_installs_newer_and_rejects_duplicate_and_outdated`, `test_duplicate_lsas_are_rejected_and_not_reflooded`, `test_outdated_lsa_arriving_late_is_rejected` |
| Temporary LSDB inconsistency | `test_routers_temporarily_disagree_and_spf_uses_local_lsdb` |
| SPF on the local LSDB | `test_routing_table_is_computed_from_lsdb_contents_only`, `test_routers_temporarily_disagree_and_spf_uses_local_lsdb` (A still routes over the failed BD link until it learns about it) |
| Partition and unreachable destinations | `test_partition_is_reported_separately_and_heals`, `test_mesh12_partition_isolates_jeju`, `test_multiple_link_failures`, `test_lsa_in_transit_is_lost_when_its_link_fails` |
| Reconvergence detection | `test_convergence_status_changes_are_recorded`, `test_not_converged_until_all_lsdbs_agree`, `test_future_scheduled_change_does_not_break_convergence`, `test_in_flight_duplicates_do_not_delay_convergence` |
| Determinism | `test_simulation_is_deterministic`, `test_stepping_and_run_until_idle_give_identical_results`, `test_documented_examples_match_a_real_run` |
| More than four routers | `test_every_single_link_failure_and_recovery_reconverges[ring8/mesh12]`: every link is failed and then recovered, and all routing table costs are compared with global Dijkstra |
| No real-time delays | `test_no_real_time_sleep_is_used` |
| Event queue ordering | 6 tests in `test_ospf_event_queue.py` |

Measured result for the reference scenario (basic topology, default
config, BD fails at t=0): reconverged at **t=3**, which is the B→A→C→D
flooding chain. A's route to D changes at t=1 from `A-B-D` (cost 2) to
`A-C-D` (cost 5).

## 7. Known limitations and incomplete features

These are also listed in `docs/ospf/README.md#limitations`.

- Single area only, Router-LSAs only. No DR/BDR, no Hello protocol, no
  neighbor state machine. Detection uses a fixed delay.
- No LSA aging, refresh, checksums, or sequence-number wrap-around. No
  acknowledgements or retransmissions: a lost LSA is never resent.
- When a router rejects an outdated LSA, it does not send its newer copy
  back. The database exchange sends the full LSDB.
- The two directions of a link share one cost. While the two endpoints
  disagree on the cost, SPF uses the larger one.
- No ECMP. Router failure can only be modelled by failing all of the
  router's links.
- Not thread-safe; the REST layer must add a lock.
- **Not done in this role:** REST endpoints and frontend visualization of
  snapshots. Those belong to the team leader and Role 3.

## 8. Integration requirements (for the team leader)

Details and a suggested endpoint layout are in
[`docs/ospf/public-interface.md`](../ospf/public-interface.md#suggested-rest-integration-for-the-team-leader).

1. Create one `OSPFSimulator(INITIAL_TOPOLOGY)` in `backend/main.py`, next
   to `link_manager`, and protect it with an `RLock`.
2. Decide which object is the source of truth for physical link state. You
   can either drive link toggles through the simulator (`toggle_link`) or
   mirror each `LinkManager` toggle into it. Today the two are independent.
3. Expose endpoints for toggle, step, run, reset and snapshot. Map
   `KeyError` to 404. `snapshot(include_history=False)` gives smaller
   responses.
4. If OSPF responses get a Pydantic `response_model`, agree on it as a new
   shared model. `SimulationEvent` in `backend/models.py` was left unchanged
   because its schema (`step`, `event_id`) belongs to the existing
   `/api/simulation/events` contract.
5. Role 3 can render per-router state from `snapshot["lsdbs"]`,
   `snapshot["routing_tables"]` and `snapshot["event_history"]`, and show
   `convergence.status` and `partition`.

## 9. GitHub status

The changes are on `feature/phase2-ospf`. The team member commits them
under their own Git identity, pushes the branch, and opens the Pull Request
to `main`. The Pull Request must not be merged by its author.
