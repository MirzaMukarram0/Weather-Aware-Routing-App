# Progress

## Milestones

- [x] 0. Docs reconciled with phased build plan
- [x] 1. Scaffold + CI + Docker + provider spike script
- [x] 2. Risk engine + tests
- [x] 3. HERE routing, checkpoints, ETAs, `/api/locations`
- [x] 4. Open-Meteo + `/api/plan` + form/cards
- [x] 5. Map UI (MapLibre + deck.gl)
- [x] 6. Heatmap + 49-step slider (client-side hour index)
- [x] 7. README + deploy instructions (hosted URLs: set at deploy time)

## Demo routes (verify with `python backend/scripts/provider_spike.py`)

- Chicago, IL → Denver, CO
- Atlanta, GA → Dallas, TX

## Hosted URLs

- Frontend: _deploy to Vercel_
- Backend: _deploy to Cloud Run_

## CI

- Backend: `manage.py test`, `ruff check`
- Frontend: `typecheck`, `lint`, `build`
