# Deployment: Vercel + Render Free

The selected backend host is now **Render Free**, replacing Cloud Run at the user's request. The GCP project `truck-routing-ahmed-2026` exists with billing disabled; nothing is deployed there.

## Render deployment (current)

1. Push the reviewed changes, including root `render.yaml`, to GitHub `main`.
2. In Render, create a **Blueprint** from this repository. It defines exactly one Docker web service on `plan: free`, with no database, disk, cron job or paid add-on. Auto-deploy is off to avoid unnecessary builds.
3. Set `SECRET_KEY` to a securely generated value of at least 50 characters. Generate it privately with `python -c "import secrets; print(secrets.token_urlsafe(64))"`; enter it only in Render's secret environment field, never in git or chat.
4. Set `CORS_ALLOWED_ORIGINS` to the exact Vercel production origin. For initial local testing, use `http://localhost:5173`; replace/add the real frontend origin before public testing.
5. Confirm the service says **Free ($0)** and deploy. Do not add a payment method or select a paid plan. The Dockerfile starts Gunicorn; no migrations or database are required.
6. Verify the assigned HTTPS URL's `/api/health` returns `{"status":"ok"}`. Django automatically permits Render's assigned hostname and enables production HTTPS/security checks.
7. Set Vercel's `VITE_API_URL` to that URL without a trailing slash, rebuild the frontend, and perform the acceptance checks below.

Render Free sleeps after 15 idle minutes and can take about a minute to wake. It has usage limits and is intended for demos, not production availability. Without a payment method, applicable quota exhaustion suspends services instead of billing overages. Do not use keep-alive pings to defeat idle sleeping. See [Render Free limitations](https://render.com/docs/free).

## Cloud Run alternative (requires billing; not currently authorized)

Run these commands manually when ready to publish. No cloud resources were created by preparing these files. Examples use **Bash in Google Cloud Shell**, from the repository root; they are not PowerShell commands.

## Before deploying

- Commit the reviewed code and push it to GitHub. Keep secrets and local environment files out of git.
- Have a GCP project with billing/credits enabled and permission to manage Cloud Run, Artifact Registry, Cloud Build, service accounts, and secrets.
- Import the repository into Vercel with **Root Directory = frontend** and framework **Vite**. Reserve its stable production domain for the CORS configuration below.
- Public OSRM provides driving routes, not truck-restriction validation. Nominatim requires explicit user searches, identifying contact information, caching, and at most one request per second across the app. Keep one worker and one instance for this assessment; these public services are not a production availability guarantee. Multiple Cloud Run revisions can briefly overlap during deployment, so avoid geocoding during rollout. For production traffic, use a hosted or self-hosted provider with an appropriate quota.
- Vercel Hobby and Open-Meteo free access have noncommercial-use conditions. Confirm your intended demo fits their terms.

## 1. Prepare GCP (once)

```bash
export PROJECT_ID='YOUR_GCP_PROJECT_ID'
export REGION='us-central1'
export SERVICE='weather-routing-api'
export REPOSITORY='weather-routing'
export RUNTIME_SA="weather-routing-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker --location="$REGION"
gcloud iam service-accounts create weather-routing-runtime --display-name='Weather routing runtime'
```

Skip the create commands if these resources already exist. The runtime account needs no broad project role. The build service account needs Artifact Registry Writer on this repository and the usual Cloud Build logging permissions. If the build is denied, inspect the identity reported by Cloud Build and have the project administrator grant that account the required roles; do not grant Owner to the runtime.

Create the Django secret without printing it or writing it to the checkout:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(64), end="")' | gcloud secrets create django-secret --data-file=-
gcloud secrets add-iam-policy-binding django-secret --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor
```

If the secret exists, retain it; use `gcloud secrets versions add django-secret --data-file=-` only for an intentional rotation. The example below pins secret version **1**; replace it with the intended enabled version.

## 2. Build and deploy the backend

Copy `backend/cloudrun.env.example.yaml` to a private file outside the checkout, e.g. `/tmp/weather-routing-env.yaml`. Replace the Vercel origin and contact address. It contains no secret key. Keep `.run.app` for the initial host restriction, then narrow it after the service URL is assigned.

```bash
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/api:$(git rev-parse --short HEAD)"
gcloud builds submit backend --config=backend/cloudbuild.yaml --substitutions="_IMAGE=${IMAGE}"

gcloud run deploy "$SERVICE" \
  --image="$IMAGE" --region="$REGION" \
  --service-account="$RUNTIME_SA" \
  --allow-unauthenticated \
  --port=8080 --cpu=1 --memory=512Mi \
  --min=0 --max=1 --concurrency=8 --timeout=120 \
  --cpu-throttling \
  --env-vars-file=/tmp/weather-routing-env.yaml \
  --set-secrets=SECRET_KEY=django-secret:1

export API_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
gcloud run services update "$SERVICE" --region="$REGION" --update-env-vars="ALLOWED_HOSTS=${API_URL#https://}"
curl --fail "$API_URL/api/health"
```

`--allow-unauthenticated` intentionally makes this assessment API public. It does not publish your secret. An organization policy may prohibit public access; an administrator must resolve that before a public frontend can use it.

The container runs as a non-root user, binds Cloud Run's `PORT`, and uses one Gunicorn process with eight threads. No database service, migrations, static-file bucket, Redis, or VPC connector is required. Health checks do not call providers. Configure an HTTP startup probe for `/api/health` in Cloud Run if desired; the default TCP startup probe also works.

## 3. Deploy the frontend on Vercel

In the imported Vercel project:

| Setting | Value |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite |
| Install | `npm ci` |
| Build | `npm run build` |
| Output | `dist` |
| Production environment variable | `VITE_API_URL` = the exact HTTPS Cloud Run URL, no trailing slash |

`frontend/vercel.json` contains the build configuration, SPA rewrite and response headers. `VITE_API_URL` is public build-time configuration; never place secrets in a `VITE_` variable. Save the variable and deploy/redeploy. Changing it does not update an existing bundle until rebuilt.

Ensure `CORS_ALLOWED_ORIGINS` on Cloud Run exactly matches the final Vercel production origin (scheme + hostname, no path/trailing slash). Update it with:

```bash
gcloud run services update "$SERVICE" --region="$REGION" --update-env-vars='CORS_ALLOWED_ORIGINS=https://YOUR-PROJECT.vercel.app'
```

Preview deployments have different origins. Leave them disconnected from the production API, or explicitly add a trusted preview origin using the YAML environment file. Do not allow every `*.vercel.app` origin. Changing domains requires updating CORS and redeploying the service. Keep the example YAML synchronized before using it again, including the narrowed ALLOWED_HOSTS value.

## 4. Acceptance checks after deployment

1. Open `/api/health`: expect HTTP 200 and `{"status":"ok"}`.
2. Open the Vercel URL and inspect the browser console for CORS/mixed-content failures.
3. Search Chicago and Denver explicitly; plan departure about one hour ahead with 25,000 lb and 25-mile sampling.
4. Verify all returned route cards, recommendation warnings, mile totals, endpoint arrival times, and checkpoint weather tooltips.
5. Verify the route camera transition, preview pause/replay, selecting alternatives, and map controls.
6. Wait for the corridor forecast, scrub through hour 48, and verify no new API request per slider move. A failed heatmap must preserve route results.
7. Check a narrow mobile viewport and keyboard navigation. Check invalid input and provider failure feedback.
8. Record the two deployed URLs in README and PROGRESS. Record the 5–10 minute walkthrough only after this pass.

Local checks:

```bash
(cd backend && python manage.py test && ruff check . && ruff format --check .)
(cd frontend && npm ci && npm run typecheck && npm run lint && npm run build)
docker build -t weather-routing-api ./backend
docker run --rm -p 8080:8080 weather-routing-api
```

The final command runs a local development container without Cloud Run's production environment marker. Production startup requires a strong SECRET_KEY. Backend settings read process environment variables; copying a `.env` file alone does not load it. Docker Compose can load env files; direct `manage.py` users must export their variables.

## Costs, logs, updates and rollback

Use request-based billing, minimum zero and maximum one instance. Cold starts are expected. Set a $5 monthly billing alert at 50/90/100 percent; an alerts-only budget does not stop spending. Build minutes, Artifact Registry storage, egress and Secret Manager may also consume credits. Keep only recent images with an Artifact Registry cleanup policy after verifying deployment.

```bash
gcloud run services logs read "$SERVICE" --region="$REGION" --limit=50
gcloud run revisions list --service="$SERVICE" --region="$REGION"
# Substitute a verified previous healthy revision:
gcloud run services update-traffic "$SERVICE" --region="$REGION" --to-revisions=PREVIOUS_REVISION=100
```

Use a new commit-tagged image for each backend release. Pin the intended secret version. Frontend releases can be rolled back from Vercel's Deployments page. Redeploy the backend when changing provider endpoints or CORS.

## Official references

- [Cloud Run image deployment](https://docs.cloud.google.com/run/docs/deploying)
- [Cloud Run secrets and runtime IAM](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Vite on Vercel](https://vercel.com/docs/frameworks/frontend/vite)
- [Nominatim public usage policy](https://operations.osmfoundation.org/policies/nominatim/)

## Production security checks

Cloud Run startup refuses DEBUG=true or a missing/short SECRET_KEY. HTTPS redirect trusts the proxy header only when K_SERVICE is present. Health is exempt for HTTP probes. CSRF and clickjacking middleware are enabled. HSTS applies to this host; subdomain coverage and preload are intentionally not enabled for a provider-owned run.app domain. Django's deployment check therefore reports W005 and W021; these are documented choices, not failed application tests.

The container runtime check is also runnable locally after building:

```bash
docker run --rm weather-routing-api python scripts/container_smoke.py
```

It checks non-root execution, a nondefault PORT, health JSON, proxy HTTPS handling and security headers without calling external providers.
