# Weather-Aware Truck Routing

React + Django app that recommends the safest of up to three **HERE truck routes** using **Open-Meteo** weather at each checkpoint’s ETA, load-aware wind rules, and a corridor **heatmap** (hours 0–48 from departure).

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
copy .env.example .env     # add HERE_API_KEY
python manage.py runserver 8080
```

Health: `http://localhost:8080/api/health`

Provider spike (optional, needs key):

```bash
set HERE_API_KEY=your_key
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

- **Backend:** Django REST — `planner/providers` (HERE, Open-Meteo), `planner/domain` (risk, checkpoints, ranking, heatmap grid), `planner/api` (orchestration).
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

### Backend — Google Cloud Run

1. Build and push image (from repo root):

   ```bash
   gcloud builds submit --tag gcr.io/PROJECT_ID/weather-routing backend
   ```

2. Deploy:

   ```bash
   gcloud run deploy weather-routing-api \
     --image gcr.io/PROJECT_ID/weather-routing \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated \
     --memory 512Mi \
     --cpu 1 \
     --min-instances 0 \
     --max-instances 1 \
     --set-env-vars "DEBUG=false,ALLOWED_HOSTS=YOUR_CLOUD_RUN_HOST,CORS_ALLOWED_ORIGINS=https://YOUR_VERCEL_APP.vercel.app" \
     --set-secrets "HERE_API_KEY=here-api-key:latest,SECRET_KEY=django-secret:latest"
   ```

   For demo recording, temporarily `--min-instances 1` to avoid cold starts.

3. Set `$5 budget alert` in GCP Billing → Budgets.

### Frontend — Vercel

1. Import repo; root directory **`frontend`**.
2. Env: `VITE_API_URL=https://YOUR_CLOUD_RUN_URL` (no trailing slash).
3. Deploy; confirm CORS on backend matches Vercel origin.

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

- Fewer than 3 routes when HERE returns duplicates (via-point fallback once; message in UI).
- Heatmap capped at **500 cells** (grid coarsens); first heatmap load can take tens of seconds on long trips.
- Cloud Run **cold start** on first request when min instances = 0.

## Attribution

- Routing/geocoding: [HERE](https://www.here.com/)
- Weather: [Open-Meteo](https://open-meteo.com/)
- Basemap: [OpenFreeMap](https://openfreemap.org/)
