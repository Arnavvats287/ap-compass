# AP Compass — Codex Starter Pack

**Purpose:** Zamp PS-1; deadline Saturday 2026-11-21 (IST). This pack defines the first implementation segment and the safe extension boundaries. It is NOT a runnable app or evidence of completed implementation.

## How to start now

1. Create a new Git repository `ap-compass` (or open the empty project folder in Codex).
2. Copy the contents of this pack into the repository root. Keep `AGENTS.md` at the root.
3. For a new Codex chat, optionally paste `prompts/SESSION_START.md`, then paste `prompts/SEGMENT_01_FOUNDATION.md`. Codex should read `AGENTS.md`, `memory.md`, and `PROJECT_STATUS.md` at startup. Do **not** implement later segments in the same task.
4. Do not advance until the segment's `DONE` tests pass. Review changed files, actual test output, and the runtime yourself.
5. Complete `prompts/SEGMENT_REPORT_TEMPLATE.md` and send its actual results to ChatGPT; receive the next bounded implementation prompt. Commit the passing checkpoint as `segment-01-foundation`. Continue only after review.

## Authority order

The **official Zamp brief** governs submission requirements. For current implementation work: `AGENTS.md` + `docs/CONTRACTS.md` define safety and interfaces; `data/*_manifest.json` defines immutable synthetic oracle; `docs/SEGMENTS_AND_PARALLELISM.md` and the **explicitly authorized segment prompt** define scope. `memory.md` records context, `PROJECT_STATUS.md` records **verified** progress, and `docs/DECISION_LOG.md` records decisions. `docs/REFERENCE_SPEC_V3.md` is a **design reference**, not permission to build optional features.

## Submission priorities

Must demonstrate a **real** PDF upload, **real** Gemini extraction, deterministic finance decision, persisted real live-run progress, a useful analyst UI and dashboard/history, meaningful business edge cases, an accessible hosted link, and a real five-minute video. Do not simulate processing or financial outcomes.

## Next checkpoints

- Wednesday night: Segment 1 foundation boots, seed fixtures are arithmetically correct, preferably skeleton deployed.
- Thursday: domain engine + extraction integrated into an actual PDF-to-decision app, persisted runs and usable UI.
- Friday: scenario quality, evaluation, reliable deployment, video and freeze.
- Saturday: external smoke test and submission; no new features.

## Project continuity and review files

- `memory.md`: persistent project context, guardrails, current handoff; **not** ChatGPT account memory.
- `PROJECT_STATUS.md`: gate status, actual command/test evidence, commit and blockers.
- `docs/DECISION_LOG.md`: architecture/business decision record; no silent rewrites.
- `docs/EDGE_CASE_BACKLOG.md`: core cases and candidate standout scenarios, selected after the vertical slice.
- `docs/REVIEW_AND_HANDOFF.md`: sequential vs parallel rules and review workflow.
- `docs/SUBMISSION_CHECKLIST.md`: final live/demo acceptance.
- `prompts/SEGMENT_REPORT_TEMPLATE.md`: output to paste back after each Codex run.
- `scripts/verify_manifests.py`: **pre-code fixture consistency check** (not a substitute for app tests).

**Status at package creation:** source documents and manifests only; no application implementation or passed end-to-end run has been verified.
