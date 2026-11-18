# Intended single-container deployment

Phase 1 is verified locally with Uvicorn + Vite. No paid service has been created or deployed.
The optional Dockerfile is prepared but NOT build/runtime verified. Docker acceptance is deferred.

Intended layout:

```text
/app/backend/app        FastAPI application and initial schema
/app/data               immutable seed manifest
/app/frontend/dist      compiled React assets served by FastAPI
/data/ap-compass.db      runtime SQLite on a persistent single-instance volume
/data/uploads/          future runtime documents (not implemented)
```

A Node build stage runs `npm ci` and compiles React. The Python stage installs runtime dependencies only,
serves `/api/health` and the static root, and runs as UID 10001. Configure the volume as writable by UID 10001.
`AP_COMPASS_DB_PATH=/data/ap-compass.db`, `PORT` defaults to 8000. Startup initializes/seeds at runtime,
never during image build. Keep one instance; SQLite has no distributed-write deployment plan.
Provider secrets will be runtime backend environment variables only, never build arguments or frontend variables.

Future manual verification (NOT RUN in Phase 1):

```powershell
docker build -t ap-compass:phase-01 .
docker run --rm -p 8000:8000 -v ap-compass-data:/data ap-compass:phase-01
```

Verify `/api/health`, static assets, persistent data across restart and non-root volume permissions before hosting.
A multi-route SPA fallback must be added when future client routes require it; the foundation uses only `/`.
Do not deploy to a paid service without user approval.
