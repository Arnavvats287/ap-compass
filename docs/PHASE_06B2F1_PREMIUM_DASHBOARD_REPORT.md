# Phase 6B.2F.1 — Premium dashboard

Base `05e9c9382c76e169132fa6c093c2b133e2ce3ce1` on `codex/phase-06b2f1-premium-dashboard`. The isolated Git worktree preserves the active payable-semantics edits and evaluation reports in the original checkout.

## Visual direction

In the baseline Chrome captures, the dark panel gave two tallies and a second decision chart most of the space. The first exception’s issue and owner only appeared in the table below and its next action required opening the workspace. The queue toolbar had one search control and no sorting. At 390 px, the attention card repeated numbers and explanatory copy before the analyst could reach an invoice.

The revised overview uses a local Georgia display face, a system sans for controls and tabular figures. Rounded 24 px surfaces, 16 px nested tiles, pill controls, shared 16 px gutters and restrained surface shadows carry from the overview into the queue. Forest and citrus frame the selected exception. Sage, amber and coral distinguish chart outcomes with matching text labels. Neutral panels hold the distribution, vendor ranking, and single-PDF upload. The Workspace retains its control and evidence layout with the shared navigation.

In the first redesign capture, the tall KPI cards pushed the priority invoice too far down the 390 px view. The second pass condensed the figures, took the explanatory note out of the header, and made four compact metrics fit at 768 px. The empty state uses the same real zero counts and a shorter execution summary. The queue has a dedicated search and sort toolbar, stronger worklist controls and clearer invoice totals.

## Data and interactions

- Overview totals and decision distribution come from the existing persisted dashboard projection. Running, failed and interrupted states appear in a separate processing section. A human reassessment remains visibly separate in the queue and workspace.
- Needs Attention uses the all-record sum of recorded Review and Blocked outcomes. Within the latest 100 list it selects Blocked first, then Review, sorting each by update time and run ID. One query loads the selected snapshot's actual finding title and next action. Supplier, recorded owner and gross invoice amount come from its list row. Other recent exceptions link directly to their records. If the latest 100 contain no exceptions, the panel distinguishes that condition from an empty store.
- Top 10 groups named vendors by recorded Review + Blocked count within the latest 100 invoices. Supplier name breaks count ties deterministically. Each row opens its exact supplier filter combined with Needs attention. There are no fabricated entries or aggregated currency amounts.
- Flagged net uses the existing backend projection, grouped by currency, with analyses counted separately and unknown net or currency excluded. Priority cards show gross for the selected invoice and label its currency.
- Queue search, recorded outcome and execution filters, exact supplier selection and sorting are URL-backed. Sorting operates on the loaded list by newest update, oldest update or supplier. Mobile keeps native table structure and named invoice links while placing individual records in a stacked reading order.
- Interactive KPI links lift 4 px over 220 ms on fine pointers, with a tactile scale on press. Reduced motion removes those transforms. Static surfaces have no click affordance. Header upload links bring keyboard focus to the single-PDF chooser. The same upload stays mounted through metrics loading and failure, preserving the selected PDF.

## Design guidance

Applied the installed Taste `design-taste-frontend` skill to shape the asymmetric composition and place invoice facts inside the focal panel. The dense table and the repeated operations view take priority over marketing-style one-section layouts, external imagery and decorative effects. [Taste Skill](https://github.com/Leonxlnx/taste-skill)

Applied Vercel guidance for semantics, visible focus, reduced motion, URL-backed state, text equivalents for charts and responsive inputs. Applied the React guidance by keeping the existing parallel dashboard/list reads, TanStack Query cache, and one bounded detail query. Read the official skill instructions directly. No external setup script or new library was needed. [Web Interface Guidelines](https://vercel.com/design/guidelines) · [Web design skill](https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines) · [React Best Practices](https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices)

## Browser evidence

Chrome screenshots are local and ignored by Git. The persisted demo store was created with a controlled provider in disposable SQLite and PDF storage on port 8020. It contains HAPPY_CLEAN Ready, OVERBILLED_PARTIAL Blocked, PRICE_3PCT Review, and MISSING_PO_VALID with an original Review and audited Ready reassessment. Empty, single-record, dense, long-name, loading and error responses were separate TEST_ONLY browser intercepts.

| View | Before | After |
| --- | --- | --- |
| Desktop overview | `tmp/f1/baseline/overview-1440.png` | `tmp/f1/final/overview-1440.png` |
| Laptop and tablet | — | `tmp/f1/final/overview-1024.png`, `overview-768.png` |
| Mobile overview | `tmp/f1/baseline/overview-390.png` | `tmp/f1/final/overview-390.png` |
| Desktop and mobile queue | `tmp/f1/baseline/queue-1440.png`, `queue-390.png` | `tmp/f1/final/queue-1440.png`, `queue-390.png` |
| Spotlight detail | — | `tmp/f1/final/exception-spotlight.png` |
| Empty and single | — | `tmp/f1/final/empty-no-attention.png`, `single-ready.png` |
| Dense and long supplier | — | `tmp/f1/final/dense-long-vendors.png`, `queue-long-supplier.png` |
| Pending and error | — | `tmp/f1/final/dashboard-loading.png`, `dashboard-error.png` |

## Verification

| Command | Result |
| --- | --- |
| `npm --prefix frontend test` | 63 passed across 3 files, including 5 added tests |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed with 1,756 modules |
| `node frontend/scripts/qa.mjs` | 15 persisted views and 7 deterministic states passed. Source PDF, focus, and workspace mobile order verified. |
| `node frontend/scripts/premium-dashboard-qa.mjs` | Four widths, navigation, keyboard focus, card hover/press, touch emulation, reduced motion, dense and async states |
| `python -m pytest -c backend/pytest.ini backend/tests/test_private_demo.py -q --basetemp tmp/f1/pytest-private` | 17 passed. Existing Starlette/AnyIO deprecation warning. |
| `python scripts/verify_manifests.py` | 6 vendors, 7 POs, 3 billed records and 10 manifest cases validated |
| `python scripts/verify_git_hygiene.py` | 11 exclusions and 10 fixture PDF byte checks passed |
| `git diff --check` and protected baseline diff | No whitespace errors or changes to backend, procurement data, frozen evaluations or demo security configuration |

The Chrome commands used `AP_COMPASS_UI_URL=http://127.0.0.1:8020` and an ignored `AP_COMPASS_QA_DIR`. Browser QA issued no API writes and compared persisted records before and after interaction. No changes to public contracts, parser or evidence code, financial authority, private access, admission, PO reviews, policy previews, port 8005 or frozen results. Zero Gemini calls. The complete backend suite was outside the frontend-only gate and no read projection was added.

## Boundaries and reuse

An older recorded exception can contribute to the total without appearing among candidates for the spotlight. Vendor ranking groups by the recorded supplier label, so spelling variants can appear separately. Small screens keep the main exception high but its full owner/action still requires a short scroll. Physical-device and screen-reader testing were outside this check.

F.2 can reuse the existing upload panel, table, URL controls, focus and live feedback. F.3 can reuse the shared palette, radii and reduced-motion conventions. This phase ends at the review gate.

## Changed files

- Product surfaces and worklist logic — `frontend/src/Overview.tsx`, `OperationsBento.tsx`, `Queue.tsx`, `components.tsx`, and `worklist.ts`.
- Styling and entry point — `frontend/src/tokens.css`, `operations.css`, and `main.tsx`.
- Regression — `frontend/src/operations.test.tsx`, `frontend/scripts/qa.mjs`, and `frontend/scripts/premium-dashboard-qa.mjs`.
- Handoff — this report, `PROJECT_STATUS.md`, and `memory.md`.
