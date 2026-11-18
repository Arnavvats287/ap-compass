# Paste this prompt into Codex to start Segment 01

You are implementing **Segment 01 only** of AP Compass, a time-boxed Zamp AI Solutions Associate PS-1 case study. Read the repository root `AGENTS.md`, `memory.md`, `PROJECT_STATUS.md`, `docs/CONTRACTS.md`, `docs/SEGMENTS_AND_PARALLELISM.md`, `docs/CHANGE_RULE_PROTOCOL.md`, `data/seed_manifest.json`, `data/fixture_manifest.json`, and `docs/REVIEW_AND_HANDOFF.md` before making changes. `docs/REFERENCE_SPEC_V3.md` is background/reference, not permission to expand scope. Do not implement segments 02–07 in this task.

## Objective
Establish a small, runnable repository with stable typed contracts, idempotent authoritative synthetic procurement/ledger seed, minimal FastAPI health API, Vite/React/TypeScript app shell, reproducible test commands, and **four** invoice PDF fixtures generated from the supplied manifest. We are not implementing AI or financial decision logic yet.

## Implementation boundaries
- Suggested structure: `backend/app/contracts`, `backend/app/db`, `backend/app/domain` (interfaces only this segment), `backend/app/api`, `backend/tests`; `frontend/src`; `tests/fixtures`; `docs`.
- Python FastAPI, Pydantic, SQLAlchemy/SQLModel, SQLite; React/TypeScript/Vite/Tailwind and shadcn/ui if quick to initialize. Avoid complex scaffolding, animation, background queues, LangGraph and auth suites.
- Money must be Decimal (or minor-unit integers in DB with explicit conversion). No floats for policy or financial calculations.
- Create Pydantic contracts for `ExtractedInvoiceV1`, `EvidenceRefV1`, `PolicyV1`, `EvaluationContextV1`, `FindingV1`, `DecisionV1`, `RunSnapshotV1` (exact fields may be minimally adapted, but document all deviations).
- Import the seven POs and immutable authoritative historical billed invoices from `data/seed_manifest.json`. Seed is idempotent and never silently rewrites existing authoritative records.
- Generate machine-readable native-text sample PDF fixtures: HAPPY_CLEAN, HAPPY_PARTIAL, OVERBILLED_PARTIAL, DUPLICATE_REISSUED. Ensure values match fixture manifest exactly. Use a PDF generator such as ReportLab in dev tooling; files must be real PDFs, not text renamed `.pdf`.
- Create `.env.example` with placeholder `GEMINI_API_KEY`, DB location, model ID (do NOT include a real secret or assume the model is available). Create `.gitignore`, README with local commands and clear limitations.
- Implement a minimal `/api/health` endpoint and frontend shell showing an AP Compass product title and an empty-state “Process invoice” area. Do not display fake KPIs or fake stage progress.
- Optional: add minimal Dockerfile if straightforward; do not let Docker/hosting block local acceptance. Never falsely claim deployment is complete.

## Acceptance criteria — run these yourself
1. Backend tests execute successfully and verify all **7** seed POs, values, line quantities and canonical vendor mapping.
2. Historical invoices consume the correct remaining net and quantities for Meridian PO-1042, Aster PO-3015 and Northstar PO-2010. Exactly these authoritative historical records are seeded (unless additional records are clearly required and documented).
3. Calling the seed command twice leaves the same counts and values. Running any test must not alter the authoritative billed history.
4. Both backend and frontend start from documented commands. `/api/health` returns an actual successful response and does not reveal secrets.
5. The four generated PDFs are parseable with PyMuPDF and their expected invoice number, PO reference and amount text is extractable.
6. One invariant test proves any future analysis-run table is **not** wired to mutate historical billing state.
7. All sample records and figures are labeled synthetic.

## Process requirements
- Inspect repository first and work with existing files; don't overwrite unrelated work.
- Make a short implementation plan, execute all changes, run tests and start commands to verify actual behavior.
- Before ending, run `python scripts/verify_manifests.py` and report its actual result; run the real implementation acceptance checks. Update `PROJECT_STATUS.md` with verified evidence and only the last handoff/status sections of `memory.md`. Fill `prompts/SEGMENT_REPORT_TEMPLATE.md` with commands, results, changed files, critical assumptions, anything not verified, and proposed next step. Stop after Segment 01. Do not start Gemini integration or domain scoring yet.
