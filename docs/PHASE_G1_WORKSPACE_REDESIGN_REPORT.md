# Phase G.1 · Invoice workspace

## Design

The previous workspace repeated the recorded status across the header and anchor bar. Its desktop reading order put the PDF before the exception. On narrow screens the amount and two rows of links delayed the decision. Evidence occupied a long collection of disclosures, and the policy simulator sat below the journey.

I considered a persistent two-pane reader with an independent document scroller and a single scrolling case file with a sticky section rail. I chose the case file. It keeps the source beside the decision at desktop widths, gives the policy and evidence stable URLs, and lets the financial comparison, PDF and evidence use the full width when the screen is narrow.

- The forest header pairs invoice identity and the recorded outcome with a clearly labeled gross amount. The reason, backend comparison, owner and next step lead the reading order. The PDF stays alongside the decision and policy on wider layouts.
- The sage workspace rail collapses to accessible icons. Its highlight follows the current section. Tablet and phone layouts use a native section picker, with a direct viewer shortcut on phones.
- The evidence rail uses native horizontal scrolling, keyboard selection, and a shared inspection pane. Verified, unverified and missing references remain visible and identifiable by text and icon. The selected reference shows its value, quote and page when available, and can point the embedded PDF to the cited page.
- The recorded unit-price tolerance appears on the disclosure next to the decision. The preview remains hypothetical and uses the existing API. Run details carry a quiet demo indicator and explicitly identify TEST_ONLY extraction in diagnostics.

Taste informed spacing, editorial type, restrained lift effects and comparing actual browser output at four sizes. Vercel guidance informed the visible focus, native controls, linkable sections and reuse of the existing data fetch. The Aceternity reference informed the icon-to-label collapse pattern. The styling and motion were written in the existing AP Compass design system. [Taste](https://raw.githubusercontent.com/Leonxlnx/taste-skill/main/skills/taste-skill/SKILL.md) · [Vercel interface guidelines](https://vercel.com/design/guidelines) · [Vercel React practices](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices) · [Aceternity sidebar](https://ui.aceternity.com/blocks/sidebars/collapsible-sidebar)

## Chrome evidence

Captured from the real application with a copy of the saved eight-run TEST_ONLY rehearsal. The baseline and redesign show the same financial data.

| Width | Before | After |
| --- | --- | --- |
| 1440 px | [Blocked invoice](../tmp/g1/before-1440.png) | [Blocked invoice](../tmp/g1/after-1440.png) |
| 1024 px | [Blocked invoice](../tmp/g1/before-1024.png) | [Blocked invoice](../tmp/g1/after-1024.png) |
| 768 px | [Blocked invoice](../tmp/g1/before-768.png) | [Blocked invoice](../tmp/g1/after-768.png) |
| 390 px | [Blocked invoice](../tmp/g1/before-390.png) | [Blocked invoice](../tmp/g1/after-390.png) |

[Ready](../tmp/g1/after-ready.png) · [Review](../tmp/g1/after-review.png) · [Collapsed rail](../tmp/g1/after-collapsed.png) · [Policy preview](../tmp/g1/after-policy.png) · [Desktop evidence](../tmp/g1/after-evidence.png) · [Mobile scan evidence](../tmp/g1/after-mobile-evidence.png)

The first browser pass exposed clipping on the laptop sidebar and a document that left the screen during policy comparison. The final pass gave the rail its full label width and kept the source visible within the split pane. On phones the document stacks below the decision, and the toolbar gives it a direct jump.

## Verification

- Chrome checked expanded and collapsed navigation, all five section links, Ready/Review/Blocked, horizontal rail scrolling via keyboard and touch, selected-reference details, page jump and protected PDF retrieval. No page overflow at 1440, 1024, 768 or 390 px.
- Chrome exercised journey replay and stage disclosure, a real policy preview on the Blocked invoice, and opening and dismissing the eligible PO candidate dialog. The policy preview issued one POST and the recorded outcome remained Blocked. Sidebar and evidence interaction caused no repeat run-detail GET. The eight run IDs, outcome values and update timestamps still matched the saved rehearsal.
- Reduced motion removes the new interface transitions. Evidence selection uses arrow keys and Home/End, with visible focus. The five-stage journey still uses the same recorded states and animations.
- `npm --prefix frontend test` passed 70 tests. `npm --prefix frontend run typecheck`, `npm --prefix frontend run build` and `git diff --check` passed.
- Backend, ledger, seed, API and frozen evaluation files match the release commit. The original databases and PDFs were left intact. Chrome used a disposable copy with uploads disabled. Zero Gemini calls.

Embedded PDF rendering and page fragments depend on the browser’s PDF viewer. The workspace retains a direct authenticated PDF link. At 768 px the preview is suitable for orientation, with full-size reading available through that link. Chrome mobile emulation included a touch gesture. Physical mobile browsers and screen-reader speech were outside this verification.

**Gate · PASS for Phase G.1 local review.** The source checkpoint is `1d08b34736bcc1ceddbf63473a20fe0353b781df`. The UI checkpoint is on `codex/phase-g1-invoice-workspace` with local tag `phase-g1-invoice-workspace`.
