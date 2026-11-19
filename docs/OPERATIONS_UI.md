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


## Phase 6A additions

Policy impact is a separate,explicitly hypothetical workspace disclosure,not a worklist filter or active-policy
editor. Native2%/5% controls request the read-only policy-preview API; wait for its response,keep the recorded
badge/decision unchanged,and show locked hard controls. No automatic extraction/request on disclosure.
Decision trace replaces the basic history timeline with actual persisted nodes,timings and separate business
outcome. Horizontal desktop/vertical mobile; only RUNNING connectors move; reduced-motion disables movement.
The user's creative override adds an attention-focused asymmetric overview and editorial/control-room tokens,
with original native-control/CSS patterns and no new design dependency. All metrics remain real with existing
NET/currency/repeated-analysis caveats. Read PHASE_06A_DESIGN.md,POLICY_PREVIEW.md and PHASE_06A_REPORT.md.
The verified6A local server is8006,reusing existing persisted data; older8005 remains a prior server. No hosting.


## Phase 6A.1 — signature workbench

The overview uses an accessible real-count outcome orbit beside review/blocked links and a separate flagged
net ledger band. Same API metrics and currency/repeated-analysis definitions; no new metric or financial rule.
A compact case header and section anchors lead to an aligned PDF/primary-decision spread. Reason, financial
comparison, owner and next action stay exposed. Source evidence precedes optional audit detail; all findings
and procurement records remain available through one native disclosure, open initially for ambiguous POs.

The full-width trace now uses a readable vertical execution spine beside a separate business-outcome
surface, stacking on mobile. Distinct operation icons carry completion marks. Returned state owns emphasis;
only RUNNING has moving connector/spinner, disabled under reduced motion. Existing measured/timestamp
logic is unchanged. The trace anchor works for completed, active and failed executions.

Policy comparison occupies the full width after evidence and trace, with paper recorded/forest hypothetical
columns. A desktop sticky rail retains the recorded outcome. Selection and async preview behavior are unchanged.
Mobile rail is static, decision-first ordering remains, native PDF fallback stays available. Secondary working
text is14px; small body16px; original cream/forest/mint/citrus semantic tokens, Georgia/system-sans pairing.
See PHASE_06A1_DESIGN.md and PHASE_06A1_REPORT.md for rendered iterations, audits and actual checks.


## Phase 6B.1 human review

Missing-reference completed cases load server-authoritative review eligibility/candidates. Review PO candidates
opens a native keyboard-operable modal with PO/vendor/status/authorized net/provenance,required rationale and
explicitly unauthenticated demo actor. No candidate preselected. A deliberate confirmation requests deterministic
reassessment; disabled pending state and stable idempotency key prevent accidental duplicate submission.
Original automated decision remains visible,with a separately labelled current reassessment,stored action time,
rationale and outstanding findings. Ready means supported controls pass,not payment/posting approval.
Queue labels original and current reviewed statuses separately; filters/overview counts retain original basis.
Policy impact still previews original automated facts without the human selection. The visual system is intact.
See HUMAN_PO_RESOLUTION.md and PHASE_06B1_REPORT.md; no auth/approval/correction/deployment workflow added.
