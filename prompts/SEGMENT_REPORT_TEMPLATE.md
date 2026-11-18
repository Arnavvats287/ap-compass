# Codex end-of-segment report — fill in with observed results

Copy into the Codex chat at the END of a requested segment, and paste the completed report back to ChatGPT. Preserve failed/unverified results. Redact secrets. Do not automatically start another segment.

## Segment identity
- Segment: `NN — NAME`
- Branch / commit SHA:
- Files created/modified (paths and purpose):
- Changes to shared contracts/DB/API? If yes, list and explain approval:

## Actual verification (no guessed results)
| Command or action | Actual result (exit code/count) | Log excerpt or output path |
|---|---|---|
| Backend unit tests | | |
| Frontend build/typecheck | | |
| API/frontend startup smoke test | | |
| Segment-specific acceptance tests | | |
| Real end-to-end run, if applicable | | |

## Acceptance gate checklist
- [ ] Every required acceptance case was run and passed (list IDs).
- [ ] No ledger/PO state mutation from analysis (when applicable).
- [ ] No unapproved contract/model/schema deviations.
- [ ] No fake stages, metrics, or financial decisions.
- [ ] `PROJECT_STATUS.md` updated from observed results.
- [ ] `memory.md` handoff block updated truthfully.

## Evidence for domain/runtime behavior
- Actual document/fixture used:
- Actual decision, reason codes and affected amounts (if applicable):
- Actual execution stages/timestamps (if applicable):
- `PROCESSING_FAILED` path checked (if applicable):

## Review request to ChatGPT
- Segment gate: `PASS / FAIL / PARTIAL / NOT VERIFIED`
- Known bugs, failed tests and blockers:
- What is NOT implemented or NOT tested:
- Proposed next segment / independent worktrees (proposal only, not authorization):

STOP after reporting. Await builder/ChatGPT review and an explicit next prompt.
