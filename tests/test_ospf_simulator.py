"""Behavioural tests for the event-driven OSPF reconvergence simulator."""

import json
import time
from pathlib import Path

import pytest

from backend.ospf import OSPFSimulator, SimulationConfig
from backend.routing.routing_table import build_routing_table

TOPOLOGY_DIR = Path(__file__).resolve().parents[1] / "data" / "topologies"


def load(name: str) -> dict:
    return json.loads((TOPOLOGY_DIR / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def basic() -> dict:
    return load("basic")


def records(sim: OSPFSimulator, event_type: str, **match) -> list[dict]:
    return [
        record
        for record in sim.get_history()
        if record["event_type"] == event_type
        and all(
            record.get(key, record["details"].get(key)) == value
            for key, value in match.items()
        )
    ]


def line_topology(names: list[str]) -> dict:
    return {
        "routers": [{"id": name} for name in names],
        "links": [
            {"id": f"{a}-{b}", "source": a, "target": b, "cost": 1, "active": True}
            for a, b in zip(names, names[1:])
        ],
    }


def assert_tables_match_physical_dijkstra(sim: OSPFSimulator) -> None:
    """After convergence, every local table must agree with global Dijkstra."""

    physical = sim.get_topology()
    for router_id in sim.router_ids:
        expected = build_routing_table(physical, router_id)
        actual = sim.get_routing_table(router_id)
        for destination, row in expected.items():
            if row["cost"] is None:
                # Unreachable: the router may not even know the destination.
                assert actual.get(destination, {"reachable": False})["reachable"] is False
            else:
                assert actual[destination]["cost"] == row["cost"], (router_id, destination)
                assert actual[destination]["reachable"] is True


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------
def test_initial_lsdbs_are_consistent_and_converged(basic: dict) -> None:
    sim = OSPFSimulator(basic)

    summaries = {r: sim.get_lsdb(r).sequence_summary() for r in sim.router_ids}
    assert all(summary == {"A": 1, "B": 1, "C": 1, "D": 1} for summary in summaries.values())
    assert sim.is_converged()
    assert sim.time == 0
    assert sim.get_pending_events() == []
    assert sim.get_routing_table("A")["D"]["path"] == ["A", "B", "D"]
    assert_tables_match_physical_dijkstra(sim)


def test_lsdbs_are_independent_objects(basic: dict) -> None:
    sim = OSPFSimulator(basic)

    assert len({id(sim.get_lsdb(r)) for r in sim.router_ids}) == len(sim.router_ids)


def test_initially_partitioned_topology_does_not_share_lsas(basic: dict) -> None:
    for link in basic["links"]:
        if link["id"] in {"AB", "CD"}:
            link["active"] = False
    sim = OSPFSimulator(basic)

    assert set(sim.get_lsdb("A").sequence_summary()) == {"A", "C"}
    assert set(sim.get_lsdb("D").sequence_summary()) == {"B", "D"}
    assert sim.partition_status()["components"] == [["A", "C"], ["B", "D"]]
    assert sim.is_converged()


# ---------------------------------------------------------------------------
# Link failure, recovery, cost changes
# ---------------------------------------------------------------------------
def test_single_link_failure_reconverges_to_alternate_path(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")
    sim.run_until_idle()

    assert sim.is_converged()
    assert sim.get_routing_table("A")["D"] == {
        "destination": "D",
        "next_hop": "C",
        "path": ["A", "C", "D"],
        "cost": 5,
        "reachable": True,
    }
    for router_id in sim.router_ids:
        assert sim.get_lsdb(router_id).sequence_summary() == {"A": 1, "B": 2, "C": 1, "D": 2}
    episode = sim.convergence_status()["reconvergence_episodes"][-1]
    # B->A->C->D is the longest flooding chain: 3 hops of 1 time unit.
    assert episode == {
        "started_at": 0,
        "converged_at": 3,
        "duration": 3,
        "trigger_event_ids": ["E00001"],
        "partitioned": False,
    }
    assert_tables_match_physical_dijkstra(sim)


def test_link_recovery_restores_original_route(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")
    sim.run_until_idle()
    sim.recover_link("BD")
    sim.run_until_idle()

    assert sim.is_converged()
    assert sim.get_routing_table("A")["D"]["path"] == ["A", "B", "D"]
    assert sim.get_routing_table("A")["D"]["cost"] == 2
    for router_id in sim.router_ids:
        assert sim.get_lsdb(router_id).sequence_summary() == {"A": 1, "B": 3, "C": 1, "D": 3}
    assert len(sim.convergence_status()["reconvergence_episodes"]) == 2
    exchanges = records(sim, "lsa_transmission", reason="database_exchange")
    assert {r["router_id"] for r in exchanges} == {"B", "D"}


def test_multiple_link_failures(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")
    sim.fail_link("AB", delay=5)
    sim.run_until_idle()

    assert sim.is_converged()
    table = sim.get_routing_table("A")
    assert table["D"]["path"] == ["A", "C", "D"]
    assert table["B"]["reachable"] is False
    assert sim.get_routing_table("B")["D"]["reachable"] is False
    partition = sim.partition_status()
    assert partition["partitioned"] is True
    assert partition["isolated_routers"] == ["B"]
    episodes = sim.convergence_status()["reconvergence_episodes"]
    assert [e["started_at"] for e in episodes] == [0, 5]


def test_simultaneous_failures_on_one_router_are_coalesced(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("AB")
    sim.fail_link("AC")
    sim.run_until_idle()

    assert [r["details"]["lsa"]["sequence_number"] for r in records(sim, "lsa_generation", router_id="A")] == [2]
    advertised = sim.get_lsdb("A").get("A").links
    assert all(not link.active for link in advertised)


def test_link_cost_change_is_advertised_and_changes_routes(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.change_link_cost("BD", 10)
    sim.run_until_idle()

    assert sim.is_converged()
    assert sim.get_topology()["links"][2]["cost"] == 10
    for router_id in sim.router_ids:
        assert sim.get_lsdb(router_id).get("B").link("BD").cost == 10
    assert sim.get_routing_table("A")["D"]["path"] == ["A", "C", "D"]
    assert sim.get_routing_table("A")["D"]["cost"] == 5
    assert sim.get_routing_table("B")["D"]["cost"] == 6  # B-A-C-D


def test_redundant_changes_are_ignored(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.recover_link("AB")
    sim.change_link_cost("AB", 1)
    sim.run_until_idle()

    assert len(records(sim, "link_change_ignored")) == 2
    assert records(sim, "lsa_generation") == []
    assert sim.is_converged()


# ---------------------------------------------------------------------------
# Flooding
# ---------------------------------------------------------------------------
def test_lsa_propagates_hop_by_hop_across_multiple_routers() -> None:
    names = ["L1", "L2", "L3", "L4", "L5", "L6"]
    sim = OSPFSimulator(line_topology(names), SimulationConfig(transmission_delay=2))
    sim.fail_link("L5-L6")
    sim.run_until_idle()

    install_times = {
        r["router_id"]: r["time"]
        for r in records(sim, "lsdb_update", origin_router_id="L5", sequence_number=2)
    }
    assert install_times == {"L5": 0, "L4": 2, "L3": 4, "L2": 6, "L1": 8}
    assert "L6" not in install_times  # unreachable through the failed link
    assert sim.get_routing_table("L1")["L6"]["reachable"] is False


def test_duplicate_lsas_are_rejected_and_not_reflooded() -> None:
    sim = OSPFSimulator(load("ring8"))
    sim.fail_link("R1-R5")
    sim.run_until_idle()

    duplicates = records(sim, "lsa_rejected", reason="duplicate")
    assert duplicates, "a ring must produce duplicate deliveries"
    # Each router sends a given LSA instance at most once per interface.
    sends = [
        (r["router_id"], r["details"]["origin_router_id"], r["details"]["sequence_number"], r["details"]["link_id"])
        for r in records(sim, "lsa_transmission")
    ]
    assert len(sends) == len(set(sends))
    # Each router installs each LSA instance exactly once.
    installs = [
        (r["router_id"], r["details"]["origin_router_id"], r["details"]["sequence_number"])
        for r in records(sim, "lsdb_update")
    ]
    assert len(installs) == len(set(installs))
    assert sim.is_converged()


def test_outdated_lsa_arriving_late_is_rejected() -> None:
    topology = {
        "routers": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
        "links": [
            {"id": "AB", "source": "A", "target": "B", "cost": 1, "active": True},
            {"id": "AC", "source": "A", "target": "C", "cost": 1, "active": True},
            {"id": "CB", "source": "C", "target": "B", "cost": 1, "active": True},
            {"id": "AD", "source": "A", "target": "D", "cost": 1, "active": True},
        ],
    }
    # AB is a very slow link: A's older LSA arrives at B after the newer one.
    sim = OSPFSimulator(topology, SimulationConfig(link_delays={"AB": 10}))
    sim.fail_link("AD")
    sim.recover_link("AD", delay=1)
    sim.run_until_idle()

    outdated = records(sim, "lsa_rejected", router_id="B", reason="outdated")
    assert any(
        r["details"]["origin_router_id"] == "A"
        and r["details"]["sequence_number"] == 2
        and r["details"]["stored_sequence_number"] == 3
        for r in outdated
    )
    assert sim.get_lsdb("B").get("A").sequence_number == 3
    assert sim.is_converged()


def test_lsa_in_transit_is_lost_when_its_link_fails(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("AC")
    sim.fail_link("AB", delay=0.5)
    sim.run_until_idle()

    dropped = records(sim, "lsa_dropped", router_id="B")
    assert any(r["details"]["origin_router_id"] == "A" for r in dropped)
    assert sim.is_converged()
    assert sim.partition_status()["components"] == [["A"], ["B", "C", "D"]]


# ---------------------------------------------------------------------------
# Temporary inconsistency and local SPF
# ---------------------------------------------------------------------------
def test_routers_temporarily_disagree_and_spf_uses_local_lsdb(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")
    sim.run_until(0)

    # B detected the failure itself; A has not heard about it yet.
    assert sim.get_lsdb("B").get("B").sequence_number == 2
    assert sim.get_lsdb("A").get("B").sequence_number == 1
    assert sim.get_lsdb("A").get("D").sequence_number == 1
    assert not sim.is_converged()
    # A's SPF is based on its stale LSDB, so it still routes over the failed BD.
    assert sim.get_routing_table("A")["D"]["path"] == ["A", "B", "D"]
    assert sim.get_routing_table("B")["D"]["path"] == ["B", "A", "C", "D"]
    snapshot = sim.snapshot()
    assert snapshot["convergence"]["status"] == "converging"
    assert snapshot["pending_events"], "flooding must not be instantaneous"

    sim.run_until(1)
    assert sim.get_routing_table("A")["D"]["path"] == ["A", "C", "D"]
    assert sim.get_lsdb("B").get("D").sequence_number == 1  # D's news not yet at B

    sim.run_until_idle()
    assert sim.is_converged()


# ---------------------------------------------------------------------------
# Partitions
# ---------------------------------------------------------------------------
def test_partition_is_reported_separately_and_heals(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("AB")
    sim.fail_link("CD")
    sim.run_until_idle()

    status = sim.convergence_status()
    partition = sim.partition_status()
    assert status["converged"] is True
    assert status["reconvergence_episodes"][-1]["partitioned"] is True
    assert partition == {
        "partitioned": True,
        "component_count": 2,
        "components": [["A", "C"], ["B", "D"]],
        "isolated_routers": [],
    }
    table_a = sim.get_routing_table("A")
    assert table_a["C"]["reachable"] is True
    assert table_a["B"]["reachable"] is False and table_a["D"]["reachable"] is False
    # A keeps stale LSAs from the other side, which is allowed.
    assert sim.get_lsdb("A").get("D").sequence_number == 1

    sim.recover_link("AB")
    sim.run_until_idle()
    assert sim.is_converged()
    assert sim.partition_status()["partitioned"] is False
    summaries = [sim.get_lsdb(r).sequence_summary() for r in sim.router_ids]
    assert all(summary == summaries[0] for summary in summaries)
    assert sim.get_routing_table("C")["D"]["path"] == ["C", "A", "B", "D"]
    assert_tables_match_physical_dijkstra(sim)


# ---------------------------------------------------------------------------
# Convergence detection
# ---------------------------------------------------------------------------
def test_convergence_status_changes_are_recorded(basic: dict) -> None:
    sim = OSPFSimulator(basic, SimulationConfig(transmission_delay=3, spf_delay=1))
    sim.fail_link("BD")
    sim.run_until_idle()

    changes = records(sim, "convergence_status_change")
    assert [c["details"]["converged"] for c in changes] == [False, True]
    assert changes[-1]["time"] == sim.time
    # Last LSA arrives at t=9 (three 3-unit hops); its SPF runs at t=10.
    assert changes[-1]["details"]["duration"] == 10


def test_future_scheduled_change_does_not_break_convergence(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("AB", delay=100)

    assert sim.is_converged()
    assert len(sim.get_pending_events()) == 1
    sim.run_until(50)
    assert sim.time == 50 and sim.is_converged()
    sim.run_until_idle()
    assert sim.convergence_status()["reconvergence_episodes"][-1]["started_at"] == 100


def test_in_flight_duplicates_do_not_delay_convergence() -> None:
    sim = OSPFSimulator(load("mesh12"))
    sim.fail_link("GWJ-JEJ")
    sim.run_until_idle()

    converged_at = sim.convergence_status()["reconvergence_episodes"][-1]["converged_at"]
    last_install = max(r["time"] for r in records(sim, "lsdb_update"))
    late_duplicates = [
        r for r in records(sim, "lsa_rejected", reason="duplicate") if r["time"] > converged_at
    ]
    assert converged_at == last_install
    assert late_duplicates, "scenario should still deliver duplicates after convergence"
    assert sim.is_converged()


def test_not_converged_until_all_lsdbs_agree(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")
    convergence_flags = []
    while sim.step() is not None:
        convergence_flags.append(sim.is_converged())

    assert convergence_flags[-1] is True
    assert convergence_flags.count(True) == 1, "must converge exactly once, at the end"


# ---------------------------------------------------------------------------
# Stepping, reset, snapshots, determinism, validation
# ---------------------------------------------------------------------------
def test_step_processes_exactly_one_event(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    assert sim.step() is None

    event_id = sim.fail_link("BD")
    result = sim.step()

    assert result["event"]["event_id"] == event_id
    assert result["event"]["event_type"] == "link_failure"
    assert [r["event_type"] for r in result["records"]] == [
        "link_failure",
        "convergence_status_change",
    ]
    assert [e["event_type"] for e in sim.get_pending_events()] == [
        "lsa_generation",
        "lsa_generation",
    ]


def test_reset_restores_initial_state(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    initial = sim.snapshot()
    sim.fail_link("BD")
    sim.change_link_cost("AC", 7)
    sim.run_until_idle()

    assert sim.reset() == initial
    assert sim.time == 0


def test_snapshot_is_json_serializable_and_complete(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")
    sim.run_until(1)

    snapshot = json.loads(json.dumps(sim.snapshot()))

    assert set(snapshot) == {
        "time",
        "config",
        "topology",
        "lsdbs",
        "routing_tables",
        "pending_events",
        "event_history",
        "convergence",
        "partition",
    }
    assert snapshot["time"] == 1
    assert snapshot["lsdbs"]["A"]["lsas"][1]["sequence_number"] == 2
    assert snapshot["pending_events"][0]["payload"]["lsa"]["origin_router_id"] in {"B", "D"}
    assert snapshot["event_history"][0]["event_type"] == "simulation_initialized"


def test_snapshot_is_a_defensive_copy(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    snapshot = sim.snapshot()
    snapshot["topology"]["links"][0]["active"] = False
    snapshot["routing_tables"]["A"]["D"]["cost"] = 999

    assert sim.get_topology()["links"][0]["active"] is True
    assert sim.get_routing_table("A")["D"]["cost"] == 2


def run_scenario(topology: dict) -> str:
    sim = OSPFSimulator(topology, SimulationConfig(transmission_delay=1, spf_delay=0.5))
    sim.fail_link("SEL-SUW")
    sim.fail_link("DJN-DGU", delay=1)
    sim.change_link_cost("ULS-BSN", 9, delay=1)
    sim.recover_link("SEL-SUW", delay=4)
    sim.run_until_idle()
    return json.dumps(sim.snapshot(), sort_keys=True)


def test_simulation_is_deterministic() -> None:
    assert run_scenario(load("mesh12")) == run_scenario(load("mesh12"))


def test_stepping_and_run_until_idle_give_identical_results(basic: dict) -> None:
    stepped, batched = OSPFSimulator(basic), OSPFSimulator(basic)
    for sim in (stepped, batched):
        sim.fail_link("BD")
    while stepped.step() is not None:
        pass
    batched.run_until_idle()

    assert stepped.snapshot() == batched.snapshot()


def test_no_real_time_sleep_is_used(monkeypatch: pytest.MonkeyPatch, basic: dict) -> None:
    def forbidden_sleep(_seconds: float) -> None:
        raise AssertionError("simulation must use virtual time only")

    monkeypatch.setattr(time, "sleep", forbidden_sleep)
    sim = OSPFSimulator(basic, SimulationConfig(transmission_delay=1000))
    sim.fail_link("BD")
    sim.run_until_idle()

    assert sim.time == 3000


def test_run_until_idle_enforces_event_limit(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    sim.fail_link("BD")

    with pytest.raises(RuntimeError):
        sim.run_until_idle(max_events=3)


def test_invalid_inputs_are_rejected(basic: dict) -> None:
    sim = OSPFSimulator(basic)
    with pytest.raises(KeyError):
        sim.fail_link("missing")
    with pytest.raises(ValueError):
        sim.change_link_cost("AB", 0)
    with pytest.raises(ValueError):
        sim.fail_link("AB", delay=-1)
    with pytest.raises(ValueError):
        SimulationConfig(transmission_delay=-1)
    with pytest.raises(ValueError):
        OSPFSimulator({"routers": [{"id": "A"}, {"id": "A"}], "links": []})
    with pytest.raises(ValueError):
        OSPFSimulator(
            {
                "routers": [{"id": "A"}],
                "links": [{"id": "AA", "source": "A", "target": "A", "cost": 1, "active": True}],
            }
        )


# ---------------------------------------------------------------------------
# Larger, arbitrary topologies
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name,router_count", [("basic", 4), ("ring8", 8), ("mesh12", 12)])
def test_every_single_link_failure_and_recovery_reconverges(name: str, router_count: int) -> None:
    topology = load(name)
    assert len(topology["routers"]) == router_count

    for link in topology["links"]:
        sim = OSPFSimulator(topology)
        sim.fail_link(link["id"])
        sim.run_until_idle()
        assert sim.is_converged(), link["id"]
        assert_tables_match_physical_dijkstra(sim)

        sim.recover_link(link["id"])
        sim.run_until_idle()
        assert sim.is_converged(), link["id"]
        assert not sim.partition_status()["partitioned"]
        assert_tables_match_physical_dijkstra(sim)


def test_mesh12_partition_isolates_jeju() -> None:
    sim = OSPFSimulator(load("mesh12"))
    sim.fail_link("GWJ-JEJ")
    sim.run_until_idle()

    assert sim.is_converged()
    assert sim.partition_status()["isolated_routers"] == ["Jeju"]
    assert sim.get_routing_table("Seoul")["Jeju"]["reachable"] is False
    assert sim.get_routing_table("Jeju")["Seoul"]["reachable"] is False


def test_ring8_multiple_failures_and_cost_changes() -> None:
    sim = OSPFSimulator(load("ring8"), SimulationConfig(transmission_delay=2, spf_delay=1))
    sim.fail_link("R1-R2")
    sim.fail_link("R3-R7", delay=1)
    sim.change_link_cost("R1-R5", 1, delay=2)
    sim.run_until_idle()

    assert sim.is_converged()
    assert_tables_match_physical_dijkstra(sim)
    assert sim.get_routing_table("R1")["R2"]["path"] == ["R1", "R5", "R4", "R3", "R2"]


def test_documented_examples_match_a_real_run(tmp_path: Path) -> None:
    from backend.ospf.demo import write_examples

    docs_dir = TOPOLOGY_DIR.parents[1] / "docs" / "ospf" / "examples"
    for generated in write_examples(tmp_path):
        committed = docs_dir / generated.name
        assert committed.read_text(encoding="utf-8") == generated.read_text(encoding="utf-8"), (
            f"{committed.name} is stale; run python -m backend.ospf.demo --write-examples docs/ospf/examples"
        )
