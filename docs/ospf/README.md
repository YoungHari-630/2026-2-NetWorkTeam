# OSPF Reconvergence Simulation Engine

`backend/ospf/` is a simplified, single-area, OSPF-style link-state routing
simulator. It shows how individual routers learn about a link change, update
their own link-state databases (LSDBs), rerun SPF, and eventually reconverge.

It is an educational model. Real OSPF packet formats, Hello/neighbor state
machines, DR/BDR election, LSA aging, checksums, authentication, and areas
are **not** implemented. See [Limitations](#limitations).

The engine does not depend on FastAPI or the frontend. The team leader's REST
layer is expected to wrap `OSPFSimulator` and return its `snapshot()`.

- Public Python interface: [`public-interface.md`](public-interface.md)
- Snapshot, event and LSA formats: [`data-formats.md`](data-formats.md)
- Real outputs of the BD-failure scenario: [`examples/`](examples/)

## Modules

| File | Content |
| --- | --- |
| `models.py` | `SimulationConfig`, `RouteEntry`, topology validation, connected components |
| `lsa.py` | `AdvertisedLink`, `LinkStateAdvertisement` (Router-LSA), `originate_router_lsa` |
| `lsdb.py` | `LinkStateDatabase` (one per router), `InstallResult`, LSDB-to-topology conversion with a two-way check |
| `event_queue.py` | `EventType`, `ScheduledEvent`, `EventQueue` (deterministic, virtual time) |
| `simulator.py` | `OSPFSimulator`, `compute_routing_table` |
| `demo.py` | Command-line demo, also regenerates `docs/ospf/examples/` |

## Protocol model

1. **Initial state.** In each physically connected component, every router
   holds the sequence-1 LSA of every router in that component. The network
   starts converged. A router never starts with LSAs from a component it
   cannot reach.
2. **Detection.** When a link fails, recovers or changes cost, its two
   endpoints notice after `detection_delay`. Each one originates a new
   Router-LSA describing all of its interfaces with sequence number + 1. If
   several changes are detected before the LSA is generated, they go into one
   LSA.
3. **Flooding.** A router sends an LSA on every interface that *its own* LSA
   says is up, except the interface it arrived on. Each hop takes
   `link_delays[link_id]` (default `transmission_delay`).
4. **Reception.** If the receiver's LSDB holds no LSA from that origin, or an
   older one (lower sequence number), the LSA is installed and re-flooded.
   Same sequence number → rejected as `duplicate`. Lower sequence number →
   rejected as `outdated`. Rejected LSAs are never re-flooded, so flooding
   always stops.
5. **Lost packets.** An LSA sent on a link that is physically down, or still
   in transit when its link fails, is recorded as `lsa_dropped`.
6. **Database exchange.** When an interface comes back up, the router sends
   its whole LSDB over it. This simplified OSPF database exchange lets two
   partitions that are re-joined learn what changed while they were apart.
7. **SPF.** Each LSDB change schedules an SPF run on that router after
   `spf_delay`. Changes that arrive before the SPF runs share one run.
   SPF builds the router's **local** topology from its own LSDB and calls the
   existing `backend.routing.routing_table.build_routing_table` (which uses
   `backend.routing.dijkstra.shortest_path`). The global physical topology is
   never used for SPF.
8. **Two-way check.** A link is used by SPF only if *both* endpoints have an
   LSA in the LSDB and both advertise the link as up towards each other.
   One "link down" LSA from either side is therefore enough to remove a
   link. If the two sides temporarily advertise different costs, the larger
   one is used. This is a documented simplification; after convergence both
   costs are equal.

The physical topology is read only (a) for a router's own interfaces when
it originates an LSA, (b) to decide whether a packet is lost, and (c) for the
observer-side convergence and partition reports.

## Event ordering

Events are kept in a heap keyed by `(time, type priority, insertion order)`:

| Priority | Event types |
| --- | --- |
| 0 | `link_failure`, `link_recovery`, `link_cost_change` |
| 1 | `lsa_generation` |
| 2 | `lsa_reception` |
| 3 | `spf_calculation` |

At equal time, physical changes happen first, then LSA generation, then
receptions, then SPF, so every LSA that arrives at time `t` is installed
before an SPF scheduled for `t` runs. Events with the same time and priority
are processed in the order they were scheduled. The order never depends on
hashing or object identity, so the same inputs always give exactly the same
snapshots (this is tested).

Delays are virtual time units. `time.sleep` is never called (also tested).

## Convergence policy

The network is **converged** when all three conditions hold:

1. **No relevant pending work.** No LSA generation and no SPF is waiting,
   and no in-flight LSA would be installed by its receiver. Duplicate or
   outdated copies still in flight, and copies on a link that is already
   down, cannot change any state, so they do not delay convergence. Link
   changes scheduled in the future do not count either, because they have
   not happened yet.
2. **LSDBs agree with the latest information.** Every router's own LSA
   matches the real state of its interfaces, and inside each physically
   connected component every router holds exactly that latest LSA of every
   other router in the component. Routers in different components are never
   compared, and nothing is expected to cross a failed link.
3. **Routing tables are current.** Every routing table was computed from
   the router's current LSDB version.

`convergence.reasons` lists every condition that is not met.

**Reconvergence time** is measured in virtual time. An episode starts at the
first physical change that occurs while the network is converged. It ends
when the network becomes converged again. Changes that happen during an
episode extend it (their event IDs are listed in `trigger_event_ids`).
Episodes are stored in `convergence.reconvergence_episodes`.

**Partitions** are reported separately in `partition`. They are computed
from the physical active links. A partitioned network can still be
converged: each component agrees internally, and destinations in other
components appear in routing tables as `reachable: false`. A router may keep
stale LSAs from routers it can no longer reach. The two-way check makes them
harmless, and the database exchange replaces them when the partition heals.

## Running

```bash
python -m pytest tests/test_ospf_*.py                       # OSPF tests only
python -m backend.ospf.demo                                 # BD failure trace on basic.json
python -m backend.ospf.demo --topology data/topologies/mesh12.json --fail GWJ-JEJ
python -m backend.ospf.demo --write-examples docs/ospf/examples   # refresh examples
```

The sample topologies are `data/topologies/basic.json` (4 routers),
`ring8.json` (8 routers: ring with two chords) and `mesh12.json` (12 routers
named after Korean cities, including a stub router `Jeju`).

## Limitations

- Single area only, with Router-LSAs only: no network/summary/external LSAs
  and no DR/BDR.
- No Hello protocol or neighbor state machine. Detection is modelled by a
  fixed `detection_delay`.
- No LSA aging (MaxAge), refresh, premature aging, checksums, or sequence
  number wrap-around.
- No acknowledgements or retransmissions: a lost LSA is not resent. Later
  LSAs and the database exchange on recovery still lead to convergence in
  every tested scenario.
- When an LSA is rejected as outdated, the receiver does not send back its
  newer copy (real OSPF does).
- The database exchange sends the full LSDB instead of DBD/LSR/LSU exchanges.
- Only one cost per link is used for SPF (the larger one while the two
  endpoints disagree). Real OSPF uses a cost for each direction.
- Equal-cost paths are not load-balanced (no ECMP). Ties are broken by the
  existing Dijkstra implementation.
- Router failures are modelled only by failing all of a router's links.
- The engine is single-threaded. Callers that share one instance between
  threads must lock around it.
