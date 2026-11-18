# AP Compass

AI-assisted Invoice Operations & Exception Resolution for Zamp ASA PS-1.
**Phase 4 vertical slice passes; architectural review pending.** Deadline: November 21, 2026 (IST).
All supplied vendors, procurement records, billed invoices and fixture PDFs are synthetic.

## Persistent API workflow (Phase 4)

Read `docs/ORCHESTRATION_API.md` and `docs/PHASE_04_REPORT.md`. Current suite: **268 passing tests**.
Upload -> persisted real stages -> actual Flash-Lite extraction -> trusted authority/context -> pure evaluation
-> reloadable decision/document. Three genuine API E2E fixtures matched READY / BLOCKED / REVIEW outcomes;
authoritative history stayed unchanged and app recreation made no model requests.

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase04-final --tb=short
# Backend with explicitly loaded local secrets; frontend remains the foundation shell:
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
curl.exe -F "file=@tests/fixtures/HAPPY_CLEAN.pdf;type=application/pdf" http://127.0.0.1:8000/api/runs
```

Poll GET /api/runs/{id}; other APIs: /api/runs, /api/runs/{id}/document, /api/policy, /api/dashboard, /api/health.
Uploads return 202; technical failures have decision=null and sanitized execution_error_code.
Run **one Uvicorn worker**: one active workflow per process, queued work interrupted on restart, no automatic replay.
Persist both AP_COMPASS_DB_PATH and AP_COMPASS_DOCUMENT_DIR (default runtime/documents).
The runtime uses gemini-3.5-flash-lite with GEMINI_ESCALATION_ENABLED=false, no per-invoice metadata lookup.
Keep the key only in ignored server-side .env; boot and health work without it.

The Phase 3 independent evidence verifier and conservative scan behavior remain intact. Native verified fields
may support READY; scan facts remain unverified, unstated line net stays None, printed totals are not repaired.
See `docs/DOCUMENT_ENGINE.md` and historical `docs/PHASE_03_1_REPORT.md` for provider/evidence details.
Optional stronger inference remains unverified and disabled. No Phase 5 UI, approval, reevaluation or deployment.

## Pure financial engine (Phase 2)

Use `from app.domain import build_context, evaluate` from the backend Python path. Supply immutable typed
invoice facts, trusted vendor/PO/billed snapshots and PolicyV1; no database or provider call occurs during evaluation.
See `docs/FINANCE_ENGINE.md` for evidence keys, rule catalog, trust requirements and deterministic matching.
Synthetic manifest facts are test inputs, not actual extraction results. The UI remains the Phase 1 shell.

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase02-final
```

Verified: 129 tests (30 foundation + 99 domain), zero failures. See `docs/PHASE_02_REPORT.md`.

## Local setup (PowerShell, repository root)

Requires Python 3.12+ and Node 24 with npm. No API key is needed for health, history or offline tests; actual extraction requires a backend key.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci --no-audit --no-fund
```

The environment reads `AP_COMPASS_DB_PATH` from the process environment; `.env` is not automatically loaded.
`.env.example` documents server-side configuration. Never put keys into frontend environment variables.
The default DB is `runtime/ap-compass.db`, resolved from repository root regardless of working directory.
On Windows sandbox temp-directory errors, use a writable temporary directory:

```powershell
New-Item -ItemType Directory -Force tmp | Out-Null
$env:TEMP = Join-Path (Get-Location) 'tmp'
$env:TMP = $env:TEMP
.venv/Scripts/python -m ensurepip --upgrade
```

Start backend in one terminal:

```powershell
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Start frontend in another:

```powershell
npm --prefix frontend run dev -- --port 5173 --strictPort
```

Visit http://127.0.0.1:5173. If occupied, use `--port 5174 --strictPort` (verified in this session).
Vite proxies `/api` to port 8000. The status page uses the actual `/api/health` endpoint.
Startup creates missing initial-schema tables and seeds missing authoritative records transactionally.
Existing conflicting seed records cause startup to fail rather than overwrite financial history.

## Reproducible verification

Run from repository root:

```powershell
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/generate_fixtures.py
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest
npm --prefix frontend run build
.venv/Scripts/python -m pip check
$env:PYTHONPATH = 'backend'
.venv/Scripts/python -m app.db.seed
.venv/Scripts/python -m app.db.seed
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

The backend suite uses isolated temporary SQLite files and never the runtime DB.
Windows execution sandbox restricts sockets and the HTTP TestClient event loop in this environment;
run the test/startup/HTTP commands with approved local execution access if needed.
No tests require network, provider keys, or paid services once dependencies are installed.

## What exists

- FastAPI health API with a real database query and allowlisted build metadata.
- Immutable typed Pydantic v1 boundary snapshots; missing extracted amounts stay null; binary floats rejected.
- SQLAlchemy SQLite initial schema. Exact Decimal values stored as TEXT/JSON decimal strings.
- Idempotent seed: 6 vendors, 7 POs/7 lines, 3 prior billed invoices; drift rejected and rolled back.
- React/TypeScript/Vite/Tailwind/Lucide shell, working navigation, disabled and honestly labeled processing CTA.
- Four native-text PDFs and the authorized image-only SCAN_CONFLICT fixture, from the untouched manifest.
- Pure matching, financial reconciliation, duplicate/bank/evidence controls and severity-based decisions.
- Persisted asynchronous invoice orchestration, bounded PDF upload/document storage and run/history/policy/dashboard APIs.

PO balances come exclusively from authorized POs minus prior billed history. Remaining net/qty:

| PO | Net INR | Qty |
|---|---:|---:|
| PO-1042 | 80000 | 16 |
| PO-1057 | 180000 | 30 |
| PO-2010 | 25000 | 25 |
| PO-3015 | 25000 | 5 |
| PO-4002 | 100000 | 10 |
| PO-5001 | 80000 | 8 |
| PO-6001 | 50000 | 50 |

These are synthetic authoritative seed balances, not analysis results or dashboard KPIs.

## Boundaries and limitations

No upload endpoints, run workflow, dashboard aggregates,
payment/posting, auth or deployment exists. Pure-engine decisions are tested against synthetic oracle facts; end-to-end PDF/extraction decisions remain unverified.
TanStack Query and shadcn/ui are deferred until server-state views or reusable interactive controls need them;
the foundation has one health fetch and native accessible controls. No UI framework generator is required.
`create_all` is the initial schema bootstrap, not a migration system. Future schema evolution requires additive migrations.
Run/stage/policy tables are foundation storage boundaries; their workflow/repository APIs are not implemented.
Direct database administration can change records; immutability here means no analysis code/hooks write authority,
not a claim that SQLite is tamper-proof.

See `docs/FOUNDATION_ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, and `docs/PHASE_01_REPORT.md`.
Stop after Phase 3 review; no later work is authorized.
