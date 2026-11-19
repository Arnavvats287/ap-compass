# Phase 6B.2F.2 — Batch upload and Excel export

Branch `codex/phase-06b2f2-batch-excel`, based on the local F.1 tag at `4e1946490e278072bef2ef0b27a344ec14972835`. This worktree carries the two approved cream-sage stylesheet edits from the F.1 preview. The original F.1 tag, its worktree, the primary checkout, and the instance on port 8005 were preserved.

## Implementation

- **Process invoices** opens a dedicated page from Overview and Invoice Operations. The native file picker and drop area accept up to ten PDFs, each nonempty and at most 8 MiB. The selection lists filenames and sizes and allows removal before submission. The existing quick single-file upload still opens its run on acceptance.
- The frontend submits one file through the existing upload endpoint, then reads that run until it reports a terminal execution state. The next upload starts only after that state is observed or the previous upload fails. The status and finished count are derived from actual responses. A terminal processing failure stays separate from both an upload failure and a financial Block. The batch remains visible if the user navigates within the app. Neither a failed POST nor a failed extraction is automatically resubmitted. If the last accepted run cannot be read, the batch pauses and can resume status checks without posting the file again.
- **Export Excel** in Invoice Operations reads `GET /api/exports/invoices.xlsx` through the same private access boundary as the invoice register. It reports progress or errors and saves a download directly. The scope is the latest 100 persisted submissions across all queue filters. The export reads snapshots and review actions with one bounded repository query. It performs no extraction, policy evaluation, or database writes.
- The workbook contains an Invoice Register, Exceptions, and Evidence Summary. The register separates original and reviewed outcomes and retains technical execution separately. The Exceptions sheet includes every recorded automated finding, with its severity and available stored comparison values. The Evidence Summary counts stored references and names the extraction provider. Exact amounts are stored as text to retain decimal precision. Other untrusted strings are serialized as literal text cells. The workbook uses forest headers, cream row bands, labeled outcome colors, frozen identity columns and headings, and filters on every sheet.
- Design uses the F.1 radius and spacing tokens, quiet drag feedback, native controls, visible focus, an announced result count, and reduced-motion support. The dashboard layout and decision trace are unchanged.

## Actual five-file Chrome run

Chrome selected the five development PDFs below in one file picker and activated **Process selected invoices**. The private app used the established `TEST_ONLY-controlled-demo` extraction provider, the normal PDF parser, source verification, financial controls, and a fresh SQLite database and document directory. Admission capacity was set to one. Port 8007 was occupied, so the demo ran on loopback port 8022.

| Development PDF | Persisted run ID | Execution / original decision |
| --- | --- | --- |
| HAPPY_CLEAN | `fb190685dfc14f2eabcb3d1c7e7a8517` | COMPLETED / READY_FOR_AP |
| OVERBILLED_PARTIAL | `017fd991eb4f4d2b90274be36a164bc0` | COMPLETED / BLOCKED |
| MISSING_PO_VALID | `cdd4b829a52d458ba3e4da4b4811d1fa` | COMPLETED / REVIEW_REQUIRED |
| PRICE_3PCT | `bfd98ca500a34d5287d37354af87d430` | COMPLETED / REVIEW_REQUIRED |
| HAPPY_PARTIAL | `4a4f8d17b26648bbb2db89f7315fc1de` | COMPLETED / READY_FOR_AP |

Five upload responses returned 202. The browser observed each completed run before the next acceptance. All five original PDF hashes matched on readback. The queue had five rows and the dashboard counted two Ready, two Review and one Blocked. A separate TEST_ONLY Chrome 429 interception showed the capacity error and created no sixth run. The real storage contained five run rows and 25 stage rows. No genuine Gemini calls were made.

## Workbook evidence

Chrome downloaded `ap-compass-invoice-register-2026-11-19.xlsx` (filename date in UTC), SHA-256 `757f8308b8e57fa7f4e359dfeb6f4ae8ec8481a0776b3c61d3bd0a043d7028db`. The unauthorized export request returned 401. The downloaded workbook was reopened with openpyxl and compared with the saved API snapshots and SQLite. Column values, exact amount text, all findings and stored evidence counts matched. The separate backend test verified a human-reviewed Ready outcome stays separate from its original automated Review.

| Sheet | Actual data rows | Frozen pane / filter |
| --- | ---: | --- |
| Invoice Register | 5 | C5 / A4:N9 |
| Exceptions | 15 | C5 / A4:I19 |
| Evidence Summary | 5 | C5 / A4:H9 |

Local screenshots in the ignored `tmp/f2-qa/evidence/` directory:

- `desktop-five-selected.png`, `mobile-five-selected.png`, and `desktop-batch-processing.png`
- `desktop-batch-results.png`, `mobile-batch-results.png`, and `desktop-upload-429-test-only.png`
- `desktop-queue-excel-download.png`
- `workbook-register.png`, `workbook-exceptions.png`, and `workbook-evidence.png` rendered from the downloaded workbook using the bundled spreadsheet runtime

## Launch the isolated demo

Run from the F.2 worktree in PowerShell, using a Python environment with the backend requirements installed and an existing frontend dependency install. Pick an unused loopback port and a fresh ignored storage directory.

```powershell
python -m pip install -r backend/requirements.txt
npm --prefix frontend run build
$env:PYTHONPATH = (Resolve-Path backend).Path
$env:AP_COMPASS_MODE = 'private'
$env:AP_COMPASS_UPLOADS_ENABLED = 'true'
$env:AP_COMPASS_UPLOAD_CAPACITY = '1'
$env:AP_COMPASS_PRIVATE_ORIGIN = 'http://127.0.0.1:8022'
$env:AP_COMPASS_PRIVATE_USERNAME = 'batch-demo'
$env:AP_COMPASS_PRIVATE_PASSWORD = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
$store = New-Item -ItemType Directory -Path ('tmp/f2-manual-' + [guid]::NewGuid().ToString('N'))
$env:AP_COMPASS_DB_PATH = Join-Path $store.FullName 'batch.db'
$env:AP_COMPASS_DOCUMENT_DIR = Join-Path $store.FullName 'documents'
@(
  "AP_COMPASS_PRIVATE_ORIGIN=$env:AP_COMPASS_PRIVATE_ORIGIN"
  "AP_COMPASS_PRIVATE_USERNAME=$env:AP_COMPASS_PRIVATE_USERNAME"
  "AP_COMPASS_PRIVATE_PASSWORD=$env:AP_COMPASS_PRIVATE_PASSWORD"
) | Set-Content -Encoding utf8 (Join-Path $store.FullName 'private.env')
python -m uvicorn scripts.private_demo:create_demo --factory --host 127.0.0.1 --port 8022
```

Open `http://127.0.0.1:8022/runs/upload` using the local demo credentials in that ignored file. The factory uses only the five allowlisted synthetic PDFs above. For a repeatable full QA run on fresh storage, use `node frontend/scripts/batch-excel-qa.mjs <private.env> <ignored-output-directory>`.

## Verification and limits

- `npm --prefix frontend test` — 67 passed across four files.
- `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` — passed. Production build transformed 1,760 modules.
- `python -m pytest -q -c backend/pytest.ini backend/tests/test_excel_export.py backend/tests/test_private_demo.py backend/tests/test_orchestration_api.py backend/tests/test_review_api.py --basetemp tmp/f2-final-pytest` — 77 passed, with one existing Starlette/AnyIO deprecation warning. Covered authenticated and empty exports, exact decimal strings, literal formula-like input, original/reviewed outcomes, technical failure distinction and read-only export.
- `node frontend/scripts/batch-excel-qa.mjs tmp/f2-qa/private.env tmp/f2-qa/evidence` — passed. Inspected desktop and 390 px mobile captures, checked page width, keyboard focus and reduced motion, followed a result to its run, and saved the real download.
- `python scripts/verify_manifests.py`, `python scripts/verify_git_hygiene.py`, `python -m pip check`, and `git diff --check` — passed.

Closing or refreshing the browser clears the batch list and stops it from submitting remaining files. Already accepted runs continue on the server and remain in Invoice Operations. The workbook preserves exact amounts as text, so a spreadsheet formula must explicitly convert any amounts the analyst wants to sum. Workbook formatting was inspected from rendered worksheet previews and through the XLSX reader. Microsoft Excel desktop execution was outside this check.

No production file upload path, parser, prompts, model selection, financial logic, procurement authority, reviewed history semantics, or frozen results were changed. No blind fixture was uploaded. No push or deployment. F.3 remains outside this work.
