# AP Compass

AI-assisted Invoice Operations & Exception Resolution for Zamp ASA PS-1.
**Phase 5 connected operations UI passes; architectural review pending.** Deadline: November 21, 2026 (IST).
All supplied vendors, procurement records, billed invoices and fixture PDFs are synthetic.

## Connected operations workspace (Phase 5)

Read `docs/OPERATIONS_UI.md` and `docs/PHASE_05_REPORT.md`.
Routes: `/` overview, `/runs` invoice queue, `/runs/:runId` source-and-decision workspace.
Actual PDF upload, persisted stages, real Flash-Lite extraction, trusted PO/history and deterministic decisions.
Real-data counts/net-by-currency, keyboard filters/search, evidence disclosures and reloadable documents.
**Verified: 280 backend tests + 32 frontend tests; TypeScript/build and browser QA pass.**

```powershell
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest-phase05-acceptance --tb=short
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

One additional genuine UI upload of OVERBILLED_PARTIAL passed COMPLETED/BLOCKED with Procurement action,
source-verified native fields and unchanged authority. One primary inference only. Viewports 1440/1024/390,
keyboard/reduced-motion, actual READY/REVIEW/BLOCK and deterministic failure/empty states were inspected.
The compiled app is served by FastAPI with deep-link reload support. Phase 5 local review: http://127.0.0.1:8005
(open in local Chrome); Vite 5175 proxies that server because an older process already owns port 8000.
See OPERATIONS_UI for the existing live demo DB/document paths; a fresh default database has an honest empty queue.

Required runtime: gemini-3.5-flash-lite, GEMINI_ESCALATION_ENABLED=false, server-side key only in ignored .env.
No per-invoice metadata lookup or stronger calls. Run one Uvicorn worker; persistent DB + document directory.
Source grounding, pure financial engine and authoritative billed ledger are unchanged. Scans remain unverified;
missing optional line net stays unknown. Technical failure is never a financial rejection.
No approval/Confirm PO/reevaluation/payment action, new scenarios, deployment or Phase 6 was added.
Historical backend integration evidence remains in docs/PHASE_04_REPORT.md and ORCHESTRATION_API.md.

## Pure financial engine (Phase 2)

Use `from app.domain import build_context, evaluate` from the backend Python path. Supply immutable typed
invoice facts, trusted vendor/PO/billed snapshots and PolicyV1; no database or provider call occurs during evaluation.
See `docs/FINANCE_ENGINE.md` for evidence keys, rule catalog, trust requirements and deterministic matching.
Synthetic manifest facts are test inputs; actual live extraction/UI evidence is recorded separately in the phase reports.

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
- Connected React/TypeScript/Tailwind/Lucide operations overview, queue and source-and-decision workspace.
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
