# Segments, dependencies, ownership and acceptance gates

## Schedule: Wednesday night -> Thursday integrated app -> Friday scenarios/rehearsal -> Saturday submit

**Do each segment with its own stop-and-review gate.** Two independent Codex workers maximum until integration is proven. Use separate worktrees if running agents concurrently. Shared files (contracts, API, DB schema) have a single owner.

| Segment | Deliverable | Depends on | Can safely run in parallel? | Gate |
|---|---|---|---|---|
| 01 FOUNDATION | Repo; AGENTS; typed contracts; seed data and assertions; backend health; frontend boots; native sample PDFs; CI/test commands | None | No. Finish first. | Local frontend/backend start; 7 POs correct; immutable ledger seeded; tests pass; initial commit |
| 02 FINANCE ENGINE | Pure matching, amount/qty, duplicate and decision rules; reason action mapping; unit tests | 01 | **Yes** with 03 on separate worktrees, owning `backend/app/domain/` and tests for domain | Happy/partial/overbilled/duplicate policy cases pass; ledger unchanged |
| 03 DOCUMENT ENGINE | PDF inspection; text/scan route; Gemini extraction adapter; validation and evidence states | 01 | **Yes** with 02, owning `backend/app/documents/`, `backend/app/ai/` and document tests | One real text PDF extracted; scan fallback tested; bad PDF rejected; no business decision in model adapter |
| 04 ORCHESTRATION + API | Persist real run stages, connect extractor to evaluator, upload/list/detail/document APIs | 02 + 03 | Backend integration sequential; UI visual shell can start **in parallel** against frozen API contracts | Real PDF -> persisted run -> actual decision; real stages; reload persistence; no ledger mutation |
| 05 OPERATIONS UI | Dashboard, live run same route, evidence, findings, next owner/action; API wiring | 04 for live wiring | UI shell/mockless structure may begin after 01; integration after 04 | Deployed app demonstrates live real run and history; no fake data/stages |
| 06 BUSINESS SCENARIOS | Ambiguity, scanned total conflict, bank-change and injection regression; conservative outcomes | 04 + minimum UI | Fixture generation + UI polish can run parallel if domains do not overlap | >=2 nontrivial scenarios E2E; expected findings; no false-ready in frozen set |
| 07 EVALUATE + RELEASE | Security smoke tests; CLI evaluation; performance/cost only if real; demo rehearsal, deployment | 05 + 06 | Docs/video planning can proceed while fixes happen; do not deploy conflicting branches | External fresh PDF and edge-case run; report real results; video <=5 min; app/video accessible |

## Safe parallelism examples

- After Segment 01: Codex A builds `backend/app/domain/**`, Codex B builds `backend/app/documents/**` + `backend/app/ai/**`. Both import **unchanged** `backend/app/contracts/**`; neither edits database models or API contracts without approval.
- While backend integration is underway: Codex B can work on static layout/components and formatting under `frontend/src/**`, but must not show simulated runs as real. Stub contracts are for local development only and must be removed from deployed behavior.
- Fixture generator and acceptance oracle can be developed parallel to UI so long as they own `tests/fixtures/**` and never change business rules to satisfy tests.
- One integration owner merges changes, runs all tests and exercises actual app after every merge.

## Unsafe parallelism examples

- Multiple agents simultaneously changing Pydantic domain contracts, SQL migrations or policy semantics.
- Matching engine and fixture oracle independently "fixing" the same expected outcome.
- AI pipeline and decision engine both normalizing money differently.
- Frontend depending on invented endpoints while the API author changes response shapes.
- Simultaneous Docker, DB, and runtime refactors right before a demo.

## Feature hierarchy / cuts

MUST: real PDF -> actual extraction -> vendor+PO+financial+duplicate deterministic decision -> stages/history -> analyst decision UI -> two meaningful edge cases -> live deployment/video.
SHOULD: extra two scenarios; bank verification; owner/fix action; native evidence validation; basic policy toggle; evaluation metrics.
ONLY IF STABLE: human confirm-PO -> new audited evaluation; richer source highlighting; cost widgets.
CUT: learned vendor hints, batch inbox, multiagent workflow, auto-payments, full supplier messaging, generic CRM features, chart-rich vendor insights.

## Gate report template

At end of segment, Codex must report: (a) changed files, (b) commands run + pass/fail, (c) observed end-to-end behavior, (d) contracts changed? why?, (e) known blockers, (f) git commit ID/branch if available. Do not start next segment until accepted.
