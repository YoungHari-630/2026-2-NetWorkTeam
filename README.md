# OSPF/Dijkstra Routing Reconvergence Simulator and Visualizer

A web-based simulator for exploring how link-state routing responds to network
failures. The project starts with a small shared topology and API foundation;
team members will implement shortest-path routing, graph visualization, and
later OSPF event simulation in separate feature branches.

## Project Overview

The simulator models routers connected by weighted, undirected links. Users
will be able to fail or restore a link and see how the network's shortest
routes change. The long-term goal is to make OSPF-style link-state behavior,
route reconvergence, and routing tables easier to understand.

## Project Objectives

- Define a common topology data format for every team member.
- Provide a small backend API for reading and changing link state.
- Implement and test Dijkstra shortest paths and routing tables.
- Visualize routers, links, link failures, and selected paths in a browser.
- Extend the simulator with simplified LSA/LSDB events and route-change
  explanations.

## Main Features

| Feature | Status |
| --- | --- |
| Shared four-router sample topology | Complete |
| `GET /api/topology` | Complete |
| Toggle a link's active/failed state and record an event | Complete |
| Reset topology and simulation event state | Complete |
| `GET /api/simulation/events` | Complete (link changes only) |
| `POST /api/route` with Dijkstra calculation | Planned (HTTP 501 placeholder) |
| Routing table generation and algorithm tests | Planned (Role 2) |
| Browser graph UI and shortest-path highlighting | Planned (Role 3) |
| Toggle a link's active/failed state | Complete |
| Reset to the initial topology | Complete |

| `POST /api/route` with Dijkstra calculation | Complete |
| Routing table generation and algorithm tests | Complete |
| Browser graph UI and route preview | Initial UI complete; API integration pending (Role 3) |

| Simplified OSPF LSA/LSDB simulation engine (`backend/ospf/`) | Engine complete; REST integration pending (team lead) — see [`docs/ospf/`](docs/ospf/README.md) |
| LLM-based route-change explanation | Planned |

## Technology Stack

| Area | Technology |
| --- | --- |
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript, Cytoscape.js |
| Testing | Pytest |
| Version control | Git & GitHub |
| AI tools | Codex and other LLM tools |

## Project Structure

```text
2026-2-NetWorkTeam/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── ospf/                    # Phase 2 OSPF reconvergence simulation engine
│   ├── routing/                 # Role 2 algorithm implementation area
│   └── simulation/
│       └── link_manager.py       # In-memory state and link event log
├── frontend/                    # Role 3 UI implementation area
├── data/topologies/            # basic.json (canonical), ring8.json, mesh12.json
├── tests/                       # Backend API and algorithm tests
├── docs/
│   ├── api-contract.md
│   ├── architecture.md
│   ├── ospf/                    # OSPF engine design, interface, data formats, examples
│   └── progress/
├── .gitignore
├── requirements.txt
└── README.md
```

The canonical topology contains routers A, B, C, and D, with links AB (cost 1),
AC (cost 2), BD (cost 1), and CD (cost 3). Links are undirected and have a
positive integer cost. An inactive link remains visible in topology data but
cannot be used for routing. See [`docs/api-contract.md`](docs/api-contract.md)
before changing shared data or API behavior.

## Team Roles

| Role | Responsibility | Branch |
| --- | --- | --- |
| Role 1 + Role 4 (Team Lead) | Project coordination, backend/API, link failure and recovery, integration, planned OSPF event simulation | `feat/backend-ospf-simulation` |
| Role 2 | Dijkstra shortest paths, routing table generation, algorithm tests | `feat/dijkstra-routing` |
| Role 3 | HTML/CSS/JavaScript UI, Cytoscape.js network visualization, path highlighting, user input and API integration | `feat/network-visualization` |

Role 2 and Role 3 should implement their assigned features in their own
branches. The shared API and data contract is in `docs/api-contract.md`.

## Installation & Setup

Requires Python 3.10 or newer and Git.

```bash
git clone https://github.com/YoungHari-630/2026-2-NetWorkTeam.git
cd 2026-2-NetWorkTeam
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install project dependencies:

```bash
python -m pip install -r requirements.txt
```

## How to Run

Start the development API server from the repository root:

```bash
python -m uvicorn backend.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; interactive documentation is
at `http://127.0.0.1:8000/docs`. To serve the browser UI, start a second
terminal at the repository root and run `python -m http.server 5500`, then
open `http://127.0.0.1:5500/frontend/`. If frontend and API use different
origins, configure FastAPI CORS for the frontend origin. See
`docs/ui-test.md` for the manual verification checklist.

## Testing

Run the test suite from the repository root:

```bash
python -m pytest
```

Current tests cover topology retrieval, link toggling, event logging, reset,
unknown link/router errors, request validation, and the explicit `501` route
placeholder. Dijkstra and frontend tests will be added with their planned
features.

OSPF simulation tests live in `tests/test_ospf_*.py`. To watch a
reconvergence trace, run `python -m backend.ospf.demo`.

## Development Roadmap

1. **Foundation (current):** agree on the shared topology schema and API;
   support topology retrieval, link toggle, and reset.
2. **Role 2:** implement Dijkstra shortest paths and routing tables, then add
   algorithm tests and connect the route API.
3. **Role 3:** initial browser interface and graph visualization are available
   in `frontend/`; complete API integration and manual testing.
4. **Role 1+4:** integrate team branches, add simplified LSA propagation and
   LSDB updates, and demonstrate routing reconvergence after link failures
   and recovery.
5. **Future:** develop LLM-based network fault diagnosis using routing tables,
   LSDB information, and event logs; compare its diagnostic performance with
   rule-based methods.


## GitHub Collaboration Workflow

Create a feature branch from the latest `main` before starting work. Use the
branch assigned to your role in the table above:

```bash
git checkout main
git pull origin main
git checkout -b feat/dijkstra-routing
```

Replace `feat/dijkstra-routing` with `feat/network-visualization` or
`feat/ospf-simulation` as appropriate. After implementing and committing your
work, push your feature branch and open a Pull Request on GitHub targeting
`main`:

```bash
git add .
git commit -m "Implement Dijkstra routing"
git push -u origin feat/dijkstra-routing
```

Open a Pull Request from your pushed branch into `main`. The team lead reviews
and merges approved Pull Requests. Keep changes within your assigned area and
coordinate shared API or schema changes through the contract document.
