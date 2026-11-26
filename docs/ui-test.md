# Role 3 browser verification

Run the frontend from the repository root using `python -m http.server 5500`
and the API with `python -m uvicorn backend.main:app --reload`. Open
`http://127.0.0.1:5500/frontend/`.

## Browser results

| Check | Result | Data source |
| --- | --- | --- |
| 4-router initial topology and route A → B → D, cost 2 | Pass | Live API |
| Per-router routing table, including next hop/full path | Pass | Live `/api/route` |
| Link AB failure and recovery; route changes while failed | Pass | Live toggle/route/events APIs |
| Event ordering and next-event playback | Pass | Live link event log |
| 8-router and 12-router graph/options/link counts | Pass (8/12 routers, 12/18 links) | Local mock presets |
| Custom topology, add 2 routers and a weighted link | Pass | Local mock adapter |
| Import starter topology JSON and export current topology JSON | Pass | Local file import/browser download |
| Korean/English switch | Pass | Browser UI |
| LSDB mock label and data separation note | Pass | Local projection; not OSPF state |
| Unsupported route for local mock topologies | Pass (explained in UI) | No route calculation fabricated |
| API unavailable state | Pass | Browser loaded while server was unavailable |
| Browser Console errors | None observed | Browser developer log |

The link failure test created two records (`link_failed`, `link_restored`); the
API reset endpoint was called afterward and the test events were cleared.
The 8/12-router and custom topology tests used only local mock data. No browser
test claimed LSA flooding, independent router LSDBs, or OSPF convergence; those
APIs do not exist yet. Back/seek is not offered because there are no snapshots.

The final UI screenshot was captured during browser verification in the Codex
task. Browser automation provided an inline capture; no image file was written
into `docs/screenshots/` in this environment.
