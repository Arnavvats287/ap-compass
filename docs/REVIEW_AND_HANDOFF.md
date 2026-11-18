# Segment review and ChatGPT → Codex handoff

This file supports the user workflow: **complete one bounded segment → send results to ChatGPT → receive next exact Codex prompt**. Neither Codex nor ChatGPT should assume a stage is finished without observed evidence.

## At beginning of each Codex session

1. Read `AGENTS.md`, `memory.md`, `PROJECT_STATUS.md`, `docs/CONTRACTS.md`, relevant manifests and ONLY the authorized segment prompt.
2. State the current authorized segment, repo head and known blockers, and confirm working files before editing.
3. Limit implementation to the segment and named directories; when two workers run, split ownership and don't amend shared contracts without authorization.

## Before requesting a new prompt

1. Run the segment's acceptance commands and at least one real runtime smoke test if the segment includes runtime behavior.
2. Print actual commands and result counts; failed/not-run tests must remain visible.
3. Record changed files and any contract/API/DB deviations; do not silently "fix" the fixture oracle or seed values.
4. Update `PROJECT_STATUS.md` with observed evidence. Update `memory.md` **only** in `Last handoff` and status/known blockers, not the immutable design decisions; append a new ADR if builder-approved design changes occurred.
5. Send the report using `prompts/SEGMENT_REPORT_TEMPLATE.md` to the builder for ChatGPT review. Don't auto-advance.

## What ChatGPT should do with that report

- If the gate failed: return a **repair-only Codex prompt**, naming exact failing tests/behaviors and forbidding expansion.
- If passed: return the next segment prompt with allowed file ownership, contracts, tests, explicit stop condition and parallelism instructions.
- When reports omit verification, ask Codex to produce missing evidence rather than assume success.
- Avoid speculative full rewrites; a rule change follows `docs/CHANGE_RULE_PROTOCOL.md` with before/after tests and rollback.

## Minimal integration guardrails

- Freeze `contracts/**`, shared database models and API paths after Segment 01 unless the builder approves a change.
- Run independent work in separate branches/worktrees; no two workers modify the same files.
- Integrate one completed branch at a time; run test suite and verify a fresh happy-path PDF after merge.
- Every API response remains typed and tolerant of new optional finding codes; no business policy in frontend components or HTTP routes.
- Before Friday freeze prioritize correctness and working deployment; after freeze only fix reliability, security and demo blockers.

## Evidence isn't the same as claimed progress

A screenshot, model text or a "tests pass" summary isn't sufficient by itself if no commands/logs were captured. The standard report includes actual exit code and test counts, the commands, and at least a succinct real run output. Redact secrets, bank data and personally identifiable values in screenshots/logs.
