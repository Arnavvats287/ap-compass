# Phase G.3 · Launch and intake policy

## Design

I considered a centered upload-first page and an editorial split. The split gives AP Compass a recognizable identity and keeps a single upload area and policy selector beside it. The file ledger spans the width immediately below them. On tablet and phone the same content stacks in reading order.

Subtle contour lines reference the compass without competing with the forest intake console. The story cards use one brief staggered horizontal entrance when they first enter view. They remain static under reduced motion and readable without animation. The footer credits Arnav Vats and describes the Zamp AI case study without implying sponsorship.

The design uses Taste’s editorial spacing and restrained motion, Vercel’s visible focus and gesture alternatives, and the existing React batch provider. The original batch route remains available, the dashboard has a direct `/overview` route, and saved invoice links still open their workspaces. [Taste](https://github.com/Leonxlnx/taste-skill) · [Vercel interface guidelines](https://vercel.com/design/guidelines) · [Vercel React practices](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices)

## Chrome captures

[Desktop 1440](../tmp/g3/launch-1440.png) · [Laptop 1024](../tmp/g3/launch-1024.png) · [Tablet 768](../tmp/g3/launch-768.png) · [Phone 390](../tmp/g3/launch-390.png) · [Product story and footer](../tmp/g3/launch-story.png)

[Selected PDFs](../tmp/g3/launch-selected.png) · [Eight completed invoices](../tmp/g3/launch-completed.png) · [Actual 5% upload selection](../tmp/g3/launch-price-selected.png)

At all four widths, Choose PDFs, the tolerance selector and the process action fit inside the first 844 px of the page. Chrome exercised keyboard file selection and radio changes, a touch tap, removal and drop re-add, reduced motion, batch results, invoice links, the Overview deep-link reload, queue navigation and export. Phone checks used Chrome touch emulation. The final visual pass rounded the intake actions to match the existing product.

## Intake policy

`POST /api/runs` still accepts one PDF per request. The optional query parameter `price_tolerance_pct` accepts exactly `0.02` or `0.05`. Omission uses the existing server default. An unsupported value or repeated parameter returns 422.

The browser captures the choice at batch start and reuses it for later files and any resumed status check. The backend stores the immutable effective policy in the existing run JSON before the run leaves Queued. It uses that snapshot for the actual financial decision. A changed tolerance has a distinct deterministic policy version. Other policy controls are copied unchanged. This required no database migration. The workspace shows the recorded tolerance, and the Invoice Register appends a per-run tolerance column. Existing decisions stay as recorded. The original batch route and single-PDF inputs continue to use the default policy when they omit the parameter.

### Controlled price comparison

The real `PRICE_3PCT` development PDF was parsed and grounded, then evaluated against unchanged seeded records using TEST_ONLY extraction. Two submissions in a disposable store used the same unposted fixture. The comparison did not add anything to billed history.

| Intake tolerance | Persisted result | Gross |
| --- | --- | ---: |
| Default 2% | Review, `PRICE_VARIANCE` | ₹12,154 |
| Explicit 5% | Ready | ₹12,154 |

That store’s dashboard was one Ready and one Review with ₹24,308 submitted gross. The register carried both recorded tolerances. The pre-existing run snapshot and billed authority matched before and after. Separate 5% cases confirmed that PO balance and quantity overruns and the exact duplicate stayed Blocked.

In a fresh separate Chrome store, selecting 5% on the homepage and uploading the same development PDF returned 202, then Ready with a persisted 5% policy. The workspace’s read-only 2% preview returned Review while the recorded Ready run stayed unchanged. Moving to Overview with a 5% draft selection created no run, and the draft remained selected on return.

### Eight-invoice rehearsal

All eight original PDFs uploaded serially from the homepage at 2%. The next POST followed the prior terminal state. Source PDF hashes and TEST_ONLY provenance matched.

| Recorded outcome | Count | INR gross |
| --- | ---: | ---: |
| Ready | 3 | 102,660 |
| Review | 3 | 71,685 |
| Blocked | 2 | 47,200 |
| Submitted | 8 | 221,545 |

The authenticated workbook contained eight register rows, 25 findings and eight evidence summaries, with 2% recorded on all eight register rows. The separate workbook for the Chrome price case recorded 5%. Dashboard totals still derive from recorded runs.

## Regression and limits

- 129 focused backend tests passed across intake policy, historical preview, finance projections, orchestration, human resolution, export, private demo and SPA routing. One existing Starlette deprecation warning appeared.
- 71 frontend tests, TypeScript typecheck, production build and `git diff --check` passed.
- A PDF outside the eight-file rehearsal allowlist reached the ordinary Gemini adapter with a local SDK substitute and completed successfully. Zero real Gemini requests were made.
- Chrome used separate local rehearsal storage. The ordinary provider, evidence, seed, financial rules, prior checkpoints and existing databases were preserved. The live provider and physical mobile browsers were outside this phase’s verification.

**Gate · PASS for G.3 local review.** Base `e5e8a183ad7063b815310b7f2e2234048ec6564d`. Local branch `codex/phase-g3-launch-intake` and tag `phase-g3-launch-intake`.
