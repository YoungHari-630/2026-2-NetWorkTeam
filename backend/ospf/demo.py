"""Command-line demo of the OSPF simulator; also regenerates doc examples.

Usage (from the repository root)::

    python -m backend.ospf.demo                      # print a BD-failure trace
    python -m backend.ospf.demo --topology data/topologies/mesh12.json --fail SEL-SUW
    python -m backend.ospf.demo --write-examples docs/ospf/examples

Every example file is produced by actually running the simulator; nothing is
hand-written.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.ospf.models import SimulationConfig
from backend.ospf.simulator import OSPFSimulator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TOPOLOGY = PROJECT_ROOT / "data" / "topologies" / "basic.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_examples(output_dir: Path) -> list[Path]:
    """Run the BD-failure scenario on the basic topology and save examples."""

    output_dir.mkdir(parents=True, exist_ok=True)
    sim = OSPFSimulator(_load(DEFAULT_TOPOLOGY), SimulationConfig())
    written: list[Path] = []

    def save(name: str, data: object) -> None:
        path = output_dir / name
        _dump(path, data)
        written.append(path)

    save("01_initial_snapshot.json", sim.snapshot())
    sim.fail_link("BD")
    save("02_step_link_failure.json", sim.step())
    sim.run_until(0)
    save("03_step_lsa_reception.json", sim.step())
    sim.run_until(1)
    save("04_snapshot_t1_converging.json", sim.snapshot(include_history=False))
    sim.run_until_idle()
    save("05_final_snapshot.json", sim.snapshot())
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--fail", default="BD", help="link ID to fail")
    parser.add_argument("--delay", type=float, default=1, help="per-hop delay")
    parser.add_argument("--write-examples", type=Path, metavar="DIR")
    args = parser.parse_args()

    if args.write_examples:
        for path in write_examples(args.write_examples):
            print(f"wrote {path}")
        return

    sim = OSPFSimulator(_load(args.topology), SimulationConfig(transmission_delay=args.delay))
    sim.fail_link(args.fail)
    for result in sim.run_until_idle():
        for record in result["records"]:
            print(f"t={record['time']:<6} {record['event_type']:<26} {record['description']}")
    print(json.dumps(sim.convergence_status(), indent=2))


if __name__ == "__main__":
    main()
