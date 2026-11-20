# AP Compass repeat-upload detection

The local change is based on `f54b11e` in `codex/phase-g3-launch-intake`.

## Behavior

- Upload computes a SHA-256 of the PDF bytes. For the same policy, the existing queued, running, or completed invoice run is returned under a SQLite transaction. The batch UI identifies the reuse and links to the existing invoice. A failed or interrupted upload can start a fresh run.
- Once a distinct PDF is extracted, verified supplier and invoice-number evidence can establish that the same canonical supplier invoice already has a completed submission. The new run records `ALREADY_SUBMITTED`, requires Review, and links to the earlier invoice. An existing hard financial Block takes precedence. Policy preview and human PO confirmation retain the recorded submission finding.
- Procurement capacity still uses approved PO net and confirmed prior billing. Submissions and their decisions are analysis records.

## Implementation

- `backend/app/db/models.py` and `migrations.py` add a nullable internal PDF fingerprint and SQLite index.
- `backend/app/orchestration/repository.py` and `service.py` resolve repeat uploads and find verified prior submissions. `backend/app/api/runs.py` returns reuse, execution state and any recorded outcome in the upload receipt.
- `backend/app/domain/controls.py` and `decisions.py` define the submission finding and reassessment behavior. The policy preview and PO confirmation orchestration preserve it.
- `frontend/src/BatchUpload.tsx`, `FindingValues.tsx`, `api.ts` and `format.ts` display repeat uploads and link to their earlier runs.

## Limits

The migration leaves old rows intact. Earlier runs can match through verified supplier and invoice number. The byte-for-byte shortcut is available to uploads with a stored fingerprint. A different PDF needs normal extraction and verified identity before its business duplicate can be established. An explicit change in effective policy creates a new analysis, where the verified submission check still applies.

## Verification

- Full backend suite passed 624 tests with one Starlette TestClient deprecation warning.
- Backend focus gate passed 189 tests covering repeat uploads, intake policy, review, private-demo admission, orchestration and financial decisions against disposable SQLite databases. Tests submitted controlled real PDF fixtures through the in-process API. Verified cases include identical concurrent uploads, restart, technical retry, verified identity across different file bytes, an unverified earlier invoice number, the original billed Block, policy preview, and PO confirmation.
- Frontend passed 82 tests, including the batch row that links to an earlier run. TypeScript, the production build, and Prettier on the changed frontend files passed.
- Gemini generations during verification: zero. The patch remains local.
