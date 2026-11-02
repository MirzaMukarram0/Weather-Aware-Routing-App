# AGENTS.md — Weather-Aware Truck Routing

React + Django app that helps a truck driver pick the safest route given weather, load weight, and travel time. This is a graded assessment: **correctness and clarity over extra features.**

Grading weights drive every trade-off:

| Weight | Area |
|---|---|
| 40% | Routes, weather, risk & recommendation logic |
| 40% | UI, map & heatmap smoothness and performance |
| 15% | Code quality |
| 5% | Docs & walkthrough |

## Source of truth (read before product or architecture work)

1. `fs-assessment-spotter.pdf` — the original requirements.
2. `AGENTS.md` (this file) — locked decisions and interpretations.
3. `.cursor/rules/*.mdc` — focused guardrails (risk engine, backend, frontend, quality).
4. `PROGRESS.md` — what is built vs remaining. Update it after each meaningful unit.

Do not invent behavior outside these docs and explicit user requests. If a requirement is ambiguous, record the decision in the "Interpretations" section below instead of guessing silently.

## What the app does

1. User enters origin, destination, departure date/time, load weight (lb), sampling interval (10 / 25 / 50 mi).
2. Backend geocodes, fetches **3 truck routes** from HERE Routing v8.
3. Places checkpoints every N miles along each route and computes the truck's **ETA at each checkpoint**.
4. Fetches the hourly forecast for each checkpoint **at its ETA** (Open-Meteo) and classifies risk (weather + load rules).
5. Summarizes each route and **recommends one** by the fixed priority order.
6. Frontend shows routes, checkpoints, risk levels, ETAs, summaries on a map, plus a corridor **weather heatmap with a 0–48 h slider**.

## Locked decisions

| Concern | Decision |
|---|---|
| Routing + geocoding | HERE (Routing v8 `transportMode=truck`, alternatives; Geocoding/Autosuggest). Load weight sent as gross weight (convert lb → kg). |
| Weather | Open-Meteo hourly forecast, batched multi-coordinate requests, `wind_speed_unit=mph`, `precipitation_unit=inch`. |
| Backend | Django + Django REST Framework. Stateless; Django cache for provider responses. |
| Frontend | Vite + React + TypeScript, MapLibre GL via `react-map-gl`, deck.gl layers. |
| Basemap | Keyless style (e.g. OpenFreeMap) unless the user provides a token. |
| Tests | Backend: Django's built-in test runner (`unittest`). No pytest unless asked. |
| Hosting | Backend on Render/Railway/Fly, frontend on Vercel/Netlify. |

## Interpretations (document in README, cover with tests)

- **Levels:** `LOW=0, MODERATE=1, HIGH=2, SEVERE=3, NO_TRAVEL=4`. Checkpoint level = max(wind, rain, snow) after load rules.
- **Boundaries:** ranges are lower-inclusive (`0.25 in/hr rain → HIGH`). Top band is strict: rain `> 1.00` and snow `> 3.0` are NO_TRAVEL; wind `≥ 55` is NO_TRAVEL.
- **Wind:** classify on `max(sustained, gust)`.
- **Sampling:** user-selectable 10 / 25 / 50 mi, default 25. Origin and destination are always checkpoints.
- **Miles per level:** each checkpoint owns half the gap to its neighbors (clipped at route ends); the owned miles sum to route length.
- **Ranking key:** `(no_travel_mi, severe_mi, high_mi, avg_risk, duration_s)`, ascending. Routes with NO_TRAVEL miles are flagged in the UI.
- **Average risk:** distance-weighted mean of level values (0–4).
- **Forecast slider:** 0–48 h measured from departure time.
- **Missing weather:** level `UNKNOWN`, shown explicitly — never defaulted to LOW.
- **Out of scope:** hours-of-service/rest breaks, live traffic, building a routing engine, auth/accounts.

## Repo layout (target)

```
backend/            Django project
  config/           settings, urls
  planner/          the only app
    providers/      here.py, open_meteo.py   (HTTP + caching, no business rules)
    domain/         risk.py, checkpoints.py, ranking.py, heatmap.py  (pure functions)
    api/            serializers.py, views.py  (validation + orchestration)
    tests/
frontend/
  src/
    api/            typed client for backend endpoints
    types/          shared response types
    components/     form, route cards, legend, slider
    map/            map view + deck.gl layer builders
    hooks/
```

## Commands

```bash
# backend
cd backend && python manage.py runserver
cd backend && python manage.py test
cd backend && ruff check . && ruff format --check .

# frontend
cd frontend && npm run dev
cd frontend && npm run typecheck && npm run lint && npm run build
```

## How to work here

- **Ponytail first** (`.cursor/rules/ponytail.mdc`): simplest correct solution, reuse before writing, fewest files, no speculative abstractions.
- **Thermo-nuclear quality bar** (`.cursor/rules/code-quality.mdc`): every change must leave structure simpler; no spaghetti conditionals, no files past ~300 lines, logic in its canonical layer.
- These two agree: both push toward deleting complexity. Ponytail governs *how much* to write; thermo-nuclear governs *where it lives and how it's shaped*.
- One feature unit at a time. "Written but unverified" is not done.

## Definition of done (per unit)

1. Behavior matches the requirements + interpretations above.
2. Non-trivial logic has one runnable check (risk/ranking/checkpoint math always has tests).
3. `manage.py test`, `ruff`, `typecheck`, `lint` pass for the touched side.
4. No secrets on the client; API keys only in backend env.
5. `PROGRESS.md` updated if the change is meaningful.

## Protected

- `.env` files and API keys — never commit, never log.
- `fs-assessment-spotter.pdf`.
