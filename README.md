# AP Compass

AP Compass is an invoice operations and exception-resolution workspace for the Zamp AI Solutions Associate case study. It helps Accounts Payable understand why invoices pass supported controls, need review, or are blocked by trusted procurement records. All bundled invoices and procurement records are synthetic.

A PDF upload creates a persisted run. The bounded document adapter extracts typed invoice facts and independently checks source support. The deterministic evaluator applies vendor, PO, billed-history and policy controls. The dashboard and queue link to the source PDF, real decision trace and findings. A demo reviewer can confirm an eligible missing PO with a recorded reason. The price tolerance preview evaluates stored facts without spending a model call or writing a decision.

On the homepage, choose up to 10 synthetic PDFs and check the file count, size and any warnings in **Intake readiness** before processing. The upload uses the server’s active unit-price policy, which defaults to 2% in this release. Open the invoice workspace to see the policy recorded for that run.

## Local development

Use Python 3.12 and Node 24. From the repository root in PowerShell:

```
py -3.12 -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
npm --prefix frontend run build
$env:PYTHONPATH = 'backend'
.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
```

Open `http://127.0.0.1:8000`. Local mode is unauthenticated and intended exclusively for loopback development. Set runtime variables on the backend, or use Uvicorn’s `--env-file` with an ignored configuration file. The application defaults to `runtime/ap-compass.db` and `runtime/documents`. For Vite development, see [Operations UI](docs/OPERATIONS_UI.md).

## Private demonstration

Private mode protects the app, API, source PDFs, health and documentation with a browser Basic-auth challenge. Remote access requires HTTPS and the controls in [Private demo security](docs/PRIVATE_DEMO_SECURITY.md). The Docker image defaults to private mode and disables new uploads unless enabled explicitly.

| Setting | Purpose |
|---|---|
| `AP_COMPASS_MODE` | `local` or `private` |
| `AP_COMPASS_PRIVATE_ORIGIN` | Required in private mode. Exact browser origin, including any nondefault port |
| `AP_COMPASS_PRIVATE_USERNAME` and `AP_COMPASS_PRIVATE_PASSWORD` | Required in private mode. Backend runtime configuration only |
| `AP_COMPASS_UPLOADS_ENABLED` | `true` or `false`. Defaults to `true` locally and `false` in private mode |
| `AP_COMPASS_UPLOAD_CAPACITY` | Maximum admitted submissions. Defaults to 3 and accepts 1–8 |
| `AP_COMPASS_DB_PATH` and `AP_COMPASS_DOCUMENT_DIR` | Persistent storage. Image defaults to `/data/ap-compass.db` and `/data/documents` |
| `GEMINI_API_KEY` | Backend key for optional live extraction. Omit for the controlled demonstration |
| `GEMINI_PRIMARY_MODEL` and `GEMINI_ESCALATION_ENABLED` | Primary defaults to `gemini-3.5-flash-lite`. Keep escalation `false` for the demo |

Build and start Docker on a loopback port using [Deployment](docs/DEPLOYMENT.md). The [five-minute runbook](docs/FIVE_MINUTE_DEMO_RUNBOOK.md) prepares four synthetic workflows through the real application using a controlled extraction provider. Each carries a visible `TEST_ONLY` label. Use `HAPPY_CLEAN` for source-supported Ready, `OVERBILLED_PARTIAL` for hard PO controls, `MISSING_PO_VALID` for audited confirmation, and `PRICE_3PCT` for the 2% versus 5% policy preview. The prepared story makes zero Gemini calls.

## Operational and evaluation limits

Ready means supported controls passed at evaluation time. There is no payment approval, PO fund reservation, ERP posting, production identity, or multi-tenant isolation. Scans and ambiguous or mixed-content evidence can require review. Gateway outages can prevent a business decision. A technical failure stays in history. Reattempting requires a separate upload while submissions are enabled.

The published post-remediation sample executed 16/16 controlled PDF submissions. Evidence scores improved, while final decisions matched 9/10 development and 3/6 held-out targets. All three held-out Ready-target invoices still required review. One of four live submissions completed and required review. That sample had no completed live non-Ready target. These are limited synthetic observations. The later currency-evidence repair was verified on separate development-only cases. See the [historical post-fix report](docs/PHASE_06B2C4_POSTFIX_VALIDATION.md) and [currency-evidence report](docs/PHASE_06B2D1_EVIDENCE_INTEGRITY_REPORT.md).

## Verification and architecture

```
.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
.venv/Scripts/python scripts/verify_manifests.py
.venv/Scripts/python scripts/verify_git_hygiene.py
.venv/Scripts/python -m pip check
```

- [Orchestration and API](docs/ORCHESTRATION_API.md), [document engine](docs/DOCUMENT_ENGINE.md), and [financial controls](docs/FINANCE_ENGINE.md)
- [Operations UI](docs/OPERATIONS_UI.md), [audited PO resolution](docs/HUMAN_PO_RESOLUTION.md), and [policy preview](docs/POLICY_PREVIEW.md)
- [Deployment](docs/DEPLOYMENT.md), [private demo security](docs/PRIVATE_DEMO_SECURITY.md), and [release hardening report](docs/RELEASE_HARDENING_REPORT.md)
