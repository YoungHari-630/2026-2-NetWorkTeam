# Role 3 UI Manual Check

## Run locally

From the repository root, start the backend:

    python -m uvicorn backend.main:app --reload

In a second terminal, serve the repository root so the page can read the shared
topology JSON:

    python -m http.server 5500

Open http://127.0.0.1:5500/frontend/. Cytoscape.js is loaded from its CDN.
If the page is served from a different origin than the API, FastAPI CORS must
allow that origin before topology and link-control requests can succeed.

## Checklist

| Check | Expected result | Status |
| --- | --- | --- |
| Initial graph | Routers A, B, C, D and four links are visible. | Passed in browser capture |
| Link costs | AB=1, AC=2, BD=1, CD=3 appear on the graph. | Passed in browser capture |
| Route controls | Source and destination can be selected; defaults are A and D. | Defaults passed in browser capture |
| Initial route | With the role 2 endpoint connected, A → B → D has cost 2 and its two links are highlighted. | Needs role 2 API |
| Preview route | Before the route endpoint is implemented, the default A → D sample is labelled as a preview, not as a backend result. | Passed in browser capture |
| Link control | Selecting a link shows its state; the button toggles failure/recovery through /api/links/toggle. | Needs backend/CORS run |
| Failed link style | An inactive link stays visible as a dashed gray edge. | Needs browser run |
| Unreachable route | A backend response with reachable: false shows no path and no highlighted route. | Needs role 2 API |
| API error | Backend/network errors appear in the status text without breaking the graph. | Passed for unavailable-server state in browser capture |
| Reset | The reset button calls /api/reset and restores all starter links. | Needs backend/CORS run |

## Screenshot

The real browser capture is saved at docs/screenshots/network-ui.png. It shows
the initial A → D example preview because the backend route endpoint is not
implemented yet. Link toggle/reset and unreachable-route checks still need to
be run after backend integration and CORS setup.
