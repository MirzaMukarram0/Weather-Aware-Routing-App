# Weather-Aware Truck Routing

React + Django app that recommends the safest of up to three **OSRM (OpenStreetMap) routes** using **Open-Meteo** weather at each checkpoint’s ETA, load-aware wind rules, and a corridor **heatmap** (hours 0–48 from departure).

**Routing/geocoding:** [OSRM](https://project-osrm.org/) + [Nominatim](https://nominatim.org/) — free, no credit card. Public demo servers are for development; load weight affects **weather risk**, not route geometry (OSRM `driving` profile).

## Live URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | _Set after deploy — `VITE_API_URL` points to backend_ |
| Backend (Cloud Run) | _Set after deploy_ |

## Quick start (local)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
# Export NOMINATIM_USER_AGENT with your contact; Django reads process environment variables.
python manage.py runserver 8080
```

Health: `http://localhost:8080/api/health`

Provider spike (optional, hits live OSRM/Nominatim/Open-Meteo):

```bash
python scripts/provider_spike.py
```

### Frontend

```bash
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`.

### Docker (backend only)

```bash
docker compose up --build
```

## Architecture

- **Backend:** Django REST — `planner/providers` (OSRM, Nominatim, Open-Meteo), `planner/domain` (risk, checkpoints, ranking, heatmap grid), `planner/api` (orchestration).
- **Frontend:** Vite + React + MapLibre + deck.gl. Slider updates heatmap hour **without refetch**.

```
POST /api/plan     → routes, checkpoints, recommendation
POST /api/heatmap  → corridor cells × 49 hourly risk levels
GET  /api/locations?q=
GET  /api/health
```

## Risk & ranking (interpretations)

- Thresholds per assessment PDF; **lower-inclusive** bands; rain `> 1.00`, snow `> 3.0`, wind `≥ 55` → NO_TRAVEL.
- Wind uses **max(sustained, gust)**; rain = **rain + showers**; precip hour = first hour **ending at/after** ETA; wind hour = **nearest** (later on tie).
- Load rules on wind: 45–54 mph & load > 30k lb → NO_TRAVEL; 35–44 & > 40k lb → SEVERE.
- Rank all routes by `(no_travel_mi, severe_mi, high_mi, avg_risk, duration_s)`; **always recommend #1** with warnings if NO_TRAVEL miles or incomplete weather.
- UNKNOWN weather never treated as LOW.

## Deploy

See [DEPLOYMENT.md](DEPLOYMENT.md) for Vercel setup, Cloud Run commands, secrets, CORS, cost controls, smoke tests and rollback.

## Tests & CI

```bash
cd backend && python manage.py test && ruff check .
cd frontend && npm run typecheck && npm run lint && npm run build
```

GitHub Actions: `.github/workflows/ci.yml`

## Loom walkthrough checklist

1. Plan a US trip (e.g. Chicago → Denver), 25 mi sampling, load 25,000 lb.
2. Show **3 routes**, checkpoint risk, **recommendation reason**.
3. Scrub **heatmap slider** (no loading spinner per hour).
4. Note corridor time label vs checkpoint ETAs.

## Known limits

- Fewer than 3 routes when OSRM returns duplicates (via-point fallback once; message in UI).
- Nominatim/OSRM public servers rate-limit heavy use — cache helps; self-host for production scale.

## Attribution

- Routing: [OSRM / OpenStreetMap](https://openstreetmap.org/copyright)
- Geocoding: [Nominatim / OSM](https://nominatim.org/)
- Weather: [Open-Meteo](https://open-meteo.com/)
- Basemap: [OpenFreeMap](https://openfreemap.org/)
