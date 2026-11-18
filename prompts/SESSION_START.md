# Codex session bootstrap (use for a new Codex chat)

Read `AGENTS.md`, `memory.md`, `PROJECT_STATUS.md`, `docs/CONTRACTS.md`, `docs/REVIEW_AND_HANDOFF.md`, and the currently authorized segment prompt. Inspect current files and `git status` before modifying anything.

Summarize the *verified* current state in at most 10 lines, naming any missing acceptance evidence. Do not assume earlier generated code passed tests. Do not modify the business invariants, seed oracle, shared contracts, policy semantics or deployment architecture without an explicit approved change.

Execute ONLY the segment/task the builder supplies after this bootstrap. Run actual tests and app smoke checks, update `PROJECT_STATUS.md` and the last handoff section of `memory.md` using observed results, then return the completed `prompts/SEGMENT_REPORT_TEMPLATE.md`. Do not auto-start the next segment.
