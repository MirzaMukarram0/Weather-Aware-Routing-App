# AGENTS.md — Weather-Aware Truck Routing

React + Django app that helps a truck driver pick the safest route given weather, load weight, and travel time. Graded assessment: **correctness and clarity over extra features.**

| Weight | Area |
|---|---|
| 40% | Routes, weather, risk & recommendation logic |
| 40% | UI, map & heatmap smoothness and performance |
| 15% | Code quality |
| 5% | Docs & walkthrough |

## Source of truth

1. `fs-assessment-spotter.pdf`
2. `AGENTS.md` (this file)
3. `.cursor/rules/*.mdc`
4. `PROGRESS.md`

## Locked stack

| Concern | Decision |
|---|---|
| Routing + geocoding | **OSRM** (open-source driving routes, public demo server) + **Nominatim** (OSM geocoding). No API key. Load weight affects **risk rules only**, not OSRM geometry. |
| Weather | Open-Meteo hourly, batched, `wind_speed_unit=mph`, `precipitation_unit=inch`. Rain = `rain + showers`. |
| Backend | Django + DRF, stateless, Django cache (in-memory OK on Cloud Run). |
| Frontend | Vite + React + TypeScript, MapLibre (`react-map-gl`) + deck.gl, OpenFreeMap Liberty basemap. |
| Hosting | **Frontend:** Vercel. **Backend:** Docker on **Google Cloud Run** (`us-central1`). |
| Tests | Django `unittest`; CI runs backend tests + ruff, frontend typecheck + lint + build. |

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness (no provider calls) |
| `GET /api/locations?q=` | Nominatim search (US-biased) |
| `POST /api/plan` | Full trip plan + recommendation |
| `POST /api/heatmap` | Corridor grid, 49 hourly risk layers |

## Interpretations (README + tests)

- **Levels:** `LOW=0 … NO_TRAVEL=4`. Checkpoint = max(wind, rain, snow) after load rules. **UNKNOWN** if required weather missing; never LOW by default. Known NO_TRAVEL stays NO_TRAVEL.
- **Boundaries:** lower-inclusive; rain `> 1.00`, snow `> 3.0`, wind `≥ 55` → NO_TRAVEL.
- **Wind for rules:** `max(sustained, gust)`.
- **Forecast hour (checkpoints):** wind → nearest UTC hour, **later hour on tie**. Precip → hour ending at or immediately after ETA (Open-Meteo preceding-hour totals).
- **Time:** client sends ISO8601 with offset + `timezone` (IANA) for display; server computes in UTC.
- **Sampling:** 10 / 25 / 50 mi toggle, default 25; origin + destination always checkpoints.
- **Mile attribution:** half gap to neighbors; sums to route length.
- **Ranking:** all routes ranked `(no_travel_mi, severe_mi, high_mi, avg_risk, duration_s)` ascending. **Always recommend #1.** If winner has NO_TRAVEL miles or incomplete weather, show **prominent warning** + reason; never hide routes.
- **Three routes:** OSRM `alternatives=true`; if <3, one via-point request; dedupe geometries.
- **Heatmap:** ~20 mi corridor half-width, ~10 mi cells, max 500 cells (coarsen + expose resolution). **49 timestamps:** departure + hours 0–48. Slider = corridor forecast at selected hour (not checkpoint ETAs). Categorical colors; UNKNOWN gray.
- **Coverage:** validate forecast through last route ETA and departure+48h; missing future hour → UNKNOWN, no stale substitution.

## Repo layout

See plan in `PROGRESS.md` milestones. `backend/planner/{providers,domain,api,tests}` · `frontend/src/{api,types,components,map,hooks}`.

## Protected

`.env*` · API keys · `fs-assessment-spotter.pdf`
