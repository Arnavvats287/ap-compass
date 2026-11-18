# AP Compass — Instructions for Codex

## Goal
Build an operational AP analyst workstation for Zamp PS-1. Customer value first: real invoice PDF -> actual extraction -> deterministic two-way PO checks -> understandable READY_FOR_AP / REVIEW_REQUIRED / BLOCKED outcome, next action, source evidence, persisted real stages and dashboard/history. No payment or ERP posting.

## Source documents (read in order)
- `memory.md` — concise durable project context and last verified handoff; treat claims of completion as unverified until supported.
- `PROJECT_STATUS.md` — authoritative checkpoint status and test evidence; update only from actual commands.
- `docs/CONTRACTS.md` — stable interfaces, invariants, architecture boundaries.
- `data/seed_manifest.json` — exact procurement and billed history used in tests.
- `data/fixture_manifest.json` — expected business scenarios.
- `docs/SEGMENTS_AND_PARALLELISM.md` — dependencies and gates.
- `docs/CHANGE_RULE_PROTOCOL.md` — safely changing financial rules.
- `docs/DECISION_LOG.md` — accepted/provisional architectural and product decisions.
- `docs/REVIEW_AND_HANDOFF.md` — review gates and how to request the next prompt.
- `docs/EDGE_CASE_BACKLOG.md` — scenario ideas, not permission to build extras.
- `docs/REFERENCE_SPEC_V3.md` — extended reference, not a directive to build optional items.

## Nonnegotiable engineering invariants
1. AI only extracts document facts; it never makes binding financial decisions or mutates master data.
2. Use `Decimal` for money. Invoice NET vs PO NET; no tax-inclusive comparison against net commitment.
3. Analysis runs NEVER mutate PO authorized records or the prior billed ledger. Rerunning does not consume balance.
4. PO identification is separate from eligibility. A referenced overbilled PO is still identified and receives PO_BALANCE_EXCEEDED, not PO_NOT_FOUND.
5. Unknown/missing extracted data stays nullable. Never coerce unknown monetary values to zero.
6. Technical failures have execution status PROCESSING_FAILED/INTERRUPTED, not ordinary business decisions. A completed blocked invoice is not a processing failure.
7. Stage progress uses actual backend state changes and timestamps. No fake UI stage timers or fabricated metrics.
8. Source evidence must be honest: native verified versus unverified scanned evidence versus missing. Do not fabricate bounding boxes or confidence.
9. File content is untrusted data; no model tool calling, shell, URL fetching, or direct DB authority. Keys server side.
10. Do not introduce LangGraph, multiagent orchestration, vector DB, queue, auth suite, multi-tenant admin, or payment automation.

## Safe extension discipline
- Typed contracts (`ExtractedInvoiceV1`, `EvaluationContextV1`, `FindingV1`, `DecisionV1`, `RunSnapshotV1`) are module boundaries. Do not scatter Gemini response structures or business rules through routes/components.
- Pure decision evaluation: `evaluate(context, policy) -> Decision`, with findings from isolated rules. New rules should not modify document extraction or UI workflow controls.
- Reason codes are stable; UI gracefully displays unknown future codes using generic severity + explanation.
- Policy is versioned and stored with every evaluation; previous decisions remain immutable. Business policy updates are additive and tested. DB changes use migrations.
- A changed rule must add or update a failing test first and run affected regression fixtures. Read `docs/CHANGE_RULE_PROTOCOL.md`.
- Do not silently alter seed ledger to make expected tests pass.

## Work style
- After any authorized segment, update `PROJECT_STATUS.md` and only the status/handoff portions of `memory.md` using observed evidence, then fill `prompts/SEGMENT_REPORT_TEMPLATE.md`. Stop; wait for the builder to obtain the next Codex prompt from ChatGPT.
- Before each Codex session, check `git status`, actual repo state and the current authorized segment. Do not trust stale completion claims or start the next phase automatically.
- Follow `docs/DECISION_LOG.md` for any builder-approved change; never rewrite accepted business semantics merely to get a test green.
- Work on ONLY the explicitly requested segment; don't pre-build optional items.
- Plan briefly, inspect repo, implement, run actual commands/tests, document results, and stop at gate.
- Minimize overlapping edits when agents work in parallel. Assign directories and use isolated branches/worktrees. Integrate only after CI/tests pass.
- Before every completion: report changed files, test commands/results, known limitations, and whether acceptance criteria are satisfied. Never claim unexecuted tests succeeded.
- No hard-coded dashboard metrics in the shipped application; synthetic fixture labels are allowed only as openly labeled examples.
