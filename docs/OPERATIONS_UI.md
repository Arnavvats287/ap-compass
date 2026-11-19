# AP Compass — Connected Operations UI

## Routes and product purpose

- /: Operations overview. Real persisted counts, outcome distribution, flagged known net by currency,
  recent activity and one-invoice upload.
- /runs: Invoice Operations queue/history. Up to 100 recent analyses, newest first; search supplier or
  invoice number. URL parameters q and status preserve filters (all, ready, review, blocked, processing,
  failed, interrupted). Filters apply only to the loaded bounded list, not all historical rows.
- /runs/:runId: Invoice Decision Workspace. Source document beside a business decision/exception brief;
  financial values, owner/next action, findings, PO alternatives, evidence, history and diagnostics.

React Router owns navigation. The application shell retires Foundation status and Phase 1 placeholder copy.
FastAPI serves the built React entry for the two frontend deep-link route shapes. Unknown API/assets remain
404. Windows-normalized paths are tested. Vite remains supported for development, with /api proxy default
http://127.0.0.1:8000; AP_COMPASS_API_TARGET can select another backend without exposing secrets to clients.

## Frontend architecture

Typed display models: src/types.ts. All application fetch calls live in src/api.ts; FormData uploads use
field file and never set a multipart boundary manually. TanStack Query owns server state and deduplicates
shared query keys. src/queries.ts provides runs/dashboard/detail hooks. UI components do not evaluate rules.
Central display utilities format decimal strings with BigInt grouping and preserve fractional digits,
without Number-based money arithmetic. Unknown amounts/timings/usage stay an em dash, actual zero stays zero.
Identifier strings, including leading zeros, are preserved. Dates use Intl; relative timestamps have exact
localized date/time titles. File sizes use B/KiB/MiB so small PDFs never appear as zero MiB.

One token system: src/tokens.css owns palette, typography, spacing, radii, shadows and motion. base.css and
styles.css consume it. Existing Tailwind and Lucide remain. System sans is deliberate for this app; no remote
fonts/images or chart/motion component libraries. Source is formatted with Prettier; Vitest/RTL tests are separate.

## Upload and actual execution

Select or drop one application/pdf file, up to 8 MiB. Show its actual filename/size/type before submission.
Client checks are guidance; the backend is authoritative. Multiple/invalid replacement files clear stale
selection. The submit control is disabled only during the actual upload, with honest busy text and no percentage.
POST 202 immediately navigates to the returned run. Rejection stays inline and focuses an accessible error.
No upload is automatically retried. The server's original filenames never become document paths.

Detail polls every 1000ms only for QUEUED/RUNNING. Terminal states stop polling; terminal detail invalidates
queue/dashboard queries. List/dashboard poll when their own data indicates active work. Shared keys avoid
overlapping requests. The latest returned detail is already authoritative, so completion does not require
another model call or a simulated progress step. Navigation/reload reads persisted history.

Timeline uses only returned RunStage rows: Invoice received / Reading invoice / Matching procurement records /
Running AP controls / Finalizing decision. Returned QUEUED/RUNNING/PASSED/WARNING/FAILED/SKIPPED map to
Waiting/Running/Complete/Attention/Failed/Skipped. Only RUNNING stages spin. No fake timers or stage percentages.
A polite live region announces meaningful stage/terminal changes, without model prompts or reasoning.

## Business language and decisions

READY_FOR_AP -> Ready to process; REVIEW_REQUIRED -> Needs review; BLOCKED -> Blocked.
Execution failure/interruption are separate technical states, with no financial rejection/decision.
READY displays the actual PASS findings and independently verified evidence count, not fabricated positive
findings for every domain check. The required payment/posting disclaimer remains visible.

BLOCK/REVIEW lead with the backend primary finding, values, owner and recommended next action. Finding values
are formatted, never recomputed. Every finding is available in severity groups; unknown future codes render
from supplied severity/title/explanation/action/values with a generic fallback. Reason codes are secondary.
For scan conflict, source uncertainty stays the backend primary; the independent arithmetic finding and exact
3600 discrepancy are exposed in the same prominent brief. Neither finding is replaced or merged into confidence.
Source-evidence wording in the brief is made business-readable; full original finding explanation remains in controls.

PO context displays returned candidates, authorized net/status/vendor record and identification provenance.
Provenance is explicitly about identity; eligibility is separately reported by findings. Multiple candidates are
shown as alternatives with Human confirmation required. No arbitrary selection or Confirm PO control exists.

## Evidence and source document

NATIVE_VERIFIED -> Source verified (page + Verified source text quote).
SOURCE_LOCATED_UNVERIFIED -> Source needs review (extraction reference, not verified source text).
MISSING -> Source not confirmed. Unknown normalized values remain unknown even when an unverified raw claim exists.
Image/mixed-source text explicitly says it has not been independently text-verified. No confidence score,
OCR accuracy, bounding boxes, highlights or client-side evidence upgrade. Optional unstated scan net stays None.

The iframe loads the actual /api/runs/:id/document PDF. Fixed dimensions avoid layout movement; browser-native
PDF UI is minimized in the embed. Open source document and Open PDF in a new tab are always available. Mobile
embedding/painting depends on the browser; these links remain the reliable full-view fallback. No filesystem URL,
base64 document or fake PDF preview is constructed. Diagnostics are collapsed and show only real safe metadata.

## Dashboard metric definitions

Counts come directly from GET /api/dashboard; Total invoices means persisted invoice submissions/analysis runs,
not unique billed business keys. Ready/review/blocked are completed business outcomes. In progress is queued +
running; failed and interrupted remain separately visible. The distribution uses actual completed outcome counts,
with accessible numeric text; there is no chart dependency or invented progress/counter animation.

Invoice value requiring attention is the API-local flagged_invoice_net_by_currency projection: sum known
extracted invoice NET for completed REVIEW_REQUIRED/BLOCKED runs, grouped by currency using exact Decimal.
Unknown net/currency rows are excluded, counted by flagged_invoice_net_missing_count and disclosed in UI.
Repeated analyses count separately; it is explicitly not unique payable exposure, savings or prevented loss.
Queue/header display amounts are invoice GROSS/TOTAL including tax, never compared to PO net by the frontend.
No average AP cycle time, ROI, accuracy, hours saved, cost or other unmeasured metric is shown.

## Accessibility and responsive behavior

Semantic nav/links/buttons/table/labels/details precede ARIA. Skip link, instant visible focus, 44px control
hit areas, searchable URL filters, inline errors, native keyboard disclosures, polite announcements, keyboard
row links and accessible status icon+text. Copy-link failure has visible manual-copy guidance. Hash retry links
scroll/focus the upload surface. Reduced motion disables animation/transitions; all stage meaning remains in text.
Loading skeletons, empty/filter-empty, request errors, unknown runs, queued/running/terminal states are explicit.

1440px: capped finance workbench, roughly 45% source / 55% decision. 1024px: compact two-column workspace and
wrapped financial values. Below 900px: compact two-row navigation, stacked overview, every queue row restacked
without losing cells, decision/action/findings/evidence before source document. Long names/references wrap.
No fixed mobile overlay obscures focus. All figures are tabular. No transition:all or layout-shifting animation.

## Local verification and deliberate limits

See PHASE_05_REPORT.md, DESIGN_NOTE/QA and the sanitized live/UI results. No authentication, human approval,
PO confirmation, reevaluation, tolerance editor, model selector, batch, ERP/email/payment action, analytics suite,
new document fixtures, deployment or Phase 6. Original backend one-process semaphore/restart limits still apply.
The history API remains bounded and no server-side filtering/pagination was added. This is not an accessibility
certification or a general extraction accuracy claim. Browser-native PDF behavior varies.

Normal development (repository root):

```powershell
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --env-file .env --host 127.0.0.1 --port 8000
npm --prefix frontend run dev
```

For this verified local demo, an older process owns 8000. The Phase 5 server is at 8005 and Vite at 5175 with
AP_COMPASS_API_TARGET=http://127.0.0.1:8005. The compiled app is also directly usable at http://127.0.0.1:8005.
QA reused runtime/phase04-smoke-0221866e9e214f3a84149d1f79098bd9/runs.db and its documents directory,
then added one genuine overbilled analysis. These runtime files, credentials, screenshots and skill installs
are ignored. No paid/public deployment was performed.
