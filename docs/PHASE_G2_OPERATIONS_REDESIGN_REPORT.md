# Phase G.2 · Invoice Operations

## Design

The baseline queue gave all eight filters the same weight. The batch page used one panel for file selection, progress and results. I chose a continuous decision strip above the existing queue table and a split intake desk for batches. This gives exceptions a clear entry point while retaining one ordered invoice list, and lets the batch controls sit alongside the file ledger on wide screens.

- The queue puts **Needs attention** first, then **Blocked**, **Needs review**, and **Ready**. Each is a filter with a count from loaded runs matching the current supplier and search. Processing, Failed and Interrupted stay separate from financial outcomes. The table keeps actual supplier, total, issue, owner and workspace links. Export remains visible and retains its latest-100 scope across filters.
- The batch’s forest console changes from file intake to live batch status. The ledger keeps selection order and shows the actual state and link for each accepted file. The console summarizes recorded Ready, Review and Blocked outcomes and reports files that ended without an AP decision separately. The finished count includes terminal failures. No percentage is estimated.
- The first visual pass exposed a tall mobile toolbar and excessive spacing between result controls. I moved search and sort onto one phone row, removed a duplicate mobile row accent, and aligned result badges and links on desktop. Keyboard focus moves to the batch heading at start and returns to the file chooser when starting a new batch.

The G.1 cream, sage and forest palette carries through both surfaces. Taste informed the single visual hierarchy and restrained motion. Vercel guidance informed native inputs, focus behavior, touch targets, linkable queue filters and keeping presentation state separate from data fetching. [Taste](https://github.com/Leonxlnx/taste-skill) · [Vercel interface guidelines](https://vercel.com/design/guidelines) · [Vercel React practices](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices)

## Chrome captures

| Surface | Desktop 1440 px | Tablet 768 px | Phone 390 px |
| --- | --- | --- | --- |
| Queue | [Before](../tmp/g2/before-queue-1440.png) · [After](../tmp/g2/after-queue-1440.png) | [Before](../tmp/g2/before-queue-768.png) · [After](../tmp/g2/after-queue-768.png) | [Before](../tmp/g2/before-queue-390.png) · [After](../tmp/g2/after-queue-390.png) |
| Empty batch | [Before](../tmp/g2/before-batch-1440.png) · [After](../tmp/g2/after-batch-empty-1440.png) | [Before](../tmp/g2/before-batch-768.png) · [After](../tmp/g2/after-batch-empty-768.png) | [Before](../tmp/g2/before-batch-390.png) · [After](../tmp/g2/after-batch-empty-390.png) |
| Batch results | [After](../tmp/g2/after-batch-results-1440.png) | [After](../tmp/g2/after-batch-results-768.png) | [After](../tmp/g2/after-batch-results-390.png) |

[Selected PDFs](../tmp/g2/after-batch-selected-1440.png) · [Live queued or processing state](../tmp/g2/after-batch-processing-1440.png) · [Upload error](../tmp/g2/after-batch-upload-error-1440.png) · [Mobile Review filter](../tmp/g2/after-mobile-review-filter.png)

## Verification

- A fresh isolated batch used the eight original PDFs and sealed **TEST_ONLY** extraction replies. Chrome sent eight real requests, each accepted with HTTP 202. Every stored terminal state arrived before the next POST. All eight source PDF hashes matched, and the decisions remained **3 Ready / 3 Review / 2 Blocked**. No Gemini requests were made. Provider provenance remains available in the unchanged invoice diagnostics and export.
- Chrome exercised the native file chooser via keyboard, removing and adding a file via a drop event, focus transfer at batch start and reset, the G.1 workspace link, and returning to the running app with batch results still available. A separately intercepted 429 rendered an upload error without creating a ninth run.
- Queue checks covered keyboard and touch filtering, search, sort, the owner column, and a real Excel download while a filter was active. The download contained all eight invoice rows, 25 findings and eight evidence summaries. Chrome checked desktop, 1024 px, tablet and phone widths with no page overflow. Reduced-motion checks disabled the new transitions.
- `npm --prefix frontend test` passed 70 tests. `npm --prefix frontend run typecheck`, `npm --prefix frontend run build`, and `git diff --check` passed.
- The existing serial uploader logic, financial rules, procurement, extraction, API and Excel implementation match G.1. The G.1 invoice workspace and earlier databases were preserved.

The queue still covers the latest 100 runs. Exact resolution instructions remain one click away in the invoice workspace. Narrow layouts stack the intake console above the file ledger. Phone QA used Chrome viewport and touch emulation. The 429 check substituted the HTTP response in Chrome and exercised the real UI error state.

**Gate · PASS for G.2 local review.** Base `f786121660650121b69ab5a015bd188c153dab6a`. Local branch `codex/phase-g2-invoice-operations` and tag `phase-g2-invoice-operations`.
