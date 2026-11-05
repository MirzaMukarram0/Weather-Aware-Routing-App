# Progress

## Milestones

- [x] 0. Docs reconciled with phased build plan
- [x] 1. Scaffold + CI + Docker + provider spike script
- [x] 2. Risk engine + tests
- [x] 3. OSRM routing + Nominatim geocoding, checkpoints, ETAs, `/api/locations`
- [x] 4. Open-Meteo + `/api/plan` + form/cards
- [x] 5. Map UI (MapLibre + deck.gl)
- [x] 6. Heatmap + 49-step slider (client-side hour index)
- [x] 7. README + deploy instructions (hosted URLs: set at deploy time)

## Demo routes (verify with `python backend/scripts/provider_spike.py`)

- Chicago, IL → Denver, CO
- Atlanta, GA → Dallas, TX

## Hosted URLs

- Frontend: _deploy to Vercel_
- Backend: _deploy to Render Free_

## CI

- Backend: `manage.py test`, `ruff check`
- Frontend: `typecheck`, `lint`, `build`

## Deployment preparation — 2026-11-05

- [x] Final local checks: 29 Django tests, Ruff lint/format, TypeScript, ESLint and production Vite build.
- [x] Non-root Cloud Run Dockerfile, PORT-aware Gunicorn, Cloud Build config and upload exclusions.
- [x] Vercel build/SPA/header configuration; deployment guide with Secret Manager, runtime IAM, CORS, budgets and rollback.
- [x] Production Django configuration: fail closed on weak/missing secret, HTTPS proxy handling, CSRF/clickjacking middleware.
- [x] CI now includes formatting and Docker build/runtime smoke checks.
- [x] Docker image build and runtime smoke check: non-root Gunicorn, custom PORT, health JSON, proxy HTTPS and security headers. All 29 backend tests also pass inside the Linux image.
- [ ] Deploy and perform hosted browser/provider acceptance checks; URLs and Loom remain outstanding.

Production checks retain two documented HSTS notices (subdomains/preload). Vite reports large map-library chunks; the map is lazy loaded. Public routing/geocoding services remain assessment-scale dependencies.

## Render deployment — 2026-11-05

- User selected Render Free to avoid enabling GCP billing. GCP project `truck-routing-ahmed-2026` exists with billing disabled.
- Added root `render.yaml` (one free Docker web service, no datastore/disk, manual deploys), Render hostname detection and production HTTPS settings.
- Verified 29 backend tests, Ruff lint/format, and Render-specific health/host/proxy/redirect checks.
- Deployment pending: Render login works, but the connected GitHub installation cannot access `MirzaMukarram0/Weather-Aware-Routing-App`. User must grant access to this repository before deployment can proceed.
