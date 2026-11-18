# AP Compass â€” Project Status / Gate Register

**Updated:** 2026-11-19 (IST)
**Current gate:** Phase 01 â€” LOCAL ACCEPTANCE PASS; ARCHITECTURAL REVIEW PENDING
**Deployment:** None; backend localhost:8000 and Vite localhost:5174 verified.
**Verified base:** Phase 1 accepted by user review; `12e4a5229903213017a852507d049133a1a7b871`.
**Checkpoint reference:** phase-02-finance-engine (resolve tag for final SHA); dedicated branch codex/phase-02-finance-engine.
**Publication:** Phase 1 remote tag verified unchanged. Phase 2 final push result reported in chat after this file is committed.
**Deadline:** Saturday 2026-11-21 (IST); Friday evening feature freeze target.

| Segment | State | Evidence | Blockers |
|---|---|---|---|
| 01 Foundation | ACCEPTED by user review | 30 tests pass; both servers boot; HTTP/proxy/browser health; four parsed/rendered PDFs; exact seed/idempotence/isolation; build/oracle/hygiene pass | None for local acceptance |
| 02 Finance engine | PASS; awaiting review | 99 domain / 129 total tests; ten fixture outcomes + 5% case; exact ledger isolation; no contract changes | None for Phase 2 |
| 03 Document engine | LOCKED (explicit approval) | Not implemented | No authorization; Gemini entitlement unverified |
| 04 Orchestration + API | LOCKED (02,03) | Not implemented | â€” |
| 05 Operations UI | LOCKED (04 for wiring) | Foundation shell only | Real workflow absent |
| 06 Scenarios + evaluation | LOCKED (vertical slice) | Expectations only | Creative case open |
| 07 Delivery + demo | LOCKED (05,06) | Docker scaffold only | Host/links/demo not verified |

## Current work assignment

- Authorized scope: Phase 02 only, completed locally. STOP for architectural review.
- Parallel workers: None used. Do not infer authorization for further phases.
- Full current evidence/commands: `docs/PHASE_02_REPORT.md`; Phase 1 historical evidence: `docs/PHASE_01_REPORT.md`.
- Shared contracts, DB/API, frontend and financial manifests unchanged; ADR-014 documents the review-only possible-duplicate heuristic.

## Execution evidence log

| Date IST | Command/action | Actual result |
|---|---|---|
| 2026-11-19 | pytest final suite | 30 passed, 1 third-party deprecation warning, zero failures, 1.77s |
| 2026-11-19 | npm install; npm run build | Dependencies installed; TypeScript/Vite production build pass |
| 2026-11-19 | Uvicorn, Vite, HTTP root/health/proxy and browser navigation | Starts; HTTP 200; correct JSON; Connected from real API |
| 2026-11-19 | seed twice, exact manifest tests, balances, atomic drift test | 6 vendors / 7 POs / 7 lines / 3 billed; unchanged on repeat |
| 2026-11-19 | fixture generation, PyMuPDF tests, Poppler visual inspection | Four valid native-text PDFs match original values |
| 2026-11-19 | verify_manifests.py; verify_git_hygiene.py; pip check | Oracle pass; 11 exclusions plus PDF index bytes pass; no broken dependencies |
| 2026-11-19 | Official Zamp brief | All 7 pages read; does not expand authorized Phase 1 |

## Phase 2 execution evidence (2026-11-19 IST)

| Command/action | Actual result |
|---|---|
| Domain tests | 99 passed, zero failures, 1.08s |
| Entire backend suite | 129 passed, zero failures, 1 pre-existing warning, 2.22s |
| Fixture smoke | All 10 manifest decisions + PRICE_3PCT at 5% match; synthetic oracle facts only |
| Focused SQLite isolation | 1 passed; 20 evaluations with DB/network blocked; identical file SHA256, rows and snapshots |
| Frontend build / pip check / oracle / hygiene | All pass; no frontend source changes |
| Protected Phase 1 implementation/manifest diff | Empty; no contract/schema/seed changes |
| Red/green regression | Fixed-precision boundary initially failed (1 failed, 77 passed); adaptive precision fix now passes |

## Bug and blocker log

- No failing Phase 1 or Phase 2 tests. Starlette/AnyIO deprecation warning remains nonblocking.
- Sandbox restrictions initially prevented Git/network/temp/socket checks; approved local execution and writable temp resolved them.
- Git PDF text classification corrected with binary attributes; committed/indexed bytes verified.
- Docker build/runtime, deployment, model availability and future end-to-end processing are unverified.
- Initial schema bootstrap is not a migration framework. Future schema changes require migrations and review.

## Handoff

Phase 02 is ready for architectural review, not accepted on the reviewer's behalf. See docs/PHASE_02_REPORT.md.
Resolve checkpoint with `git rev-parse phase-02-finance-engine^{commit}` and verify publication using `git ls-remote origin`.
Phase 1 tag stays unchanged. Do not begin Phase 3 or later without an explicit next prompt.
