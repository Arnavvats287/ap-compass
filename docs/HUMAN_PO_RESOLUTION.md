# Audited human purchase-order resolution

Phase6B.1 adds one narrowly scoped human identity workflow. A PO confirmation identifies the intended order;
it does not approve an invoice, verify document evidence, authorize payment/posting or consume PO balance.

## Evaluation boundary

Normal evaluate(context,policy), matching and all existing rules retain their previous behavior. The new
pure evaluate_with_confirmed_po(context,policy,POConfirmation) validates/rederives canonical identity using
trusted snapshots. It requires missing explicit reference, an approved canonical supplier, a same-vendor
candidate PO and an explicit rationale. It substitutes only the po_identity evaluator with a human-provenance
PO_MATCH_CONFIRMED finding. All other DEFAULT_RULES and the same aggregator execute under the same exact
Decimal precision context. Invoice facts/evidence and policy remain unchanged; no provenance string passed
to ordinary evaluate enables the override. Closed/overbilled/cross-currency/duplicate/source-uncertain cases
retain their normal financial/source controls. No model, network, clock, database or PDF work in this entry point.

The application requires a COMPLETED source with recorded extraction,decision,policy. Selection must be both
in the original recorded candidate IDs and in the freshly rederived current same-vendor candidate set. IDs
only are accepted from the browser; authoritative PO objects are loaded server-side. Financial eligibility
is deliberately not a candidate filter. Recorded candidates can become unavailable if authority changes.

## API-local endpoints

POST /api/runs/{id}/po-confirmations accepts JSON:

```json
{"po_id":"PO-1042","reviewer_label":"Demo AP analyst","rationale":"Checked intended order with Procurement.","client_action_id":"eab3b692-2108-465d-a116-9562f8653e51"}
```

Strict strings,extra fields forbidden; canonical UUID key; PO ID1–80 safe identifier characters;
reviewer label1–80,rationale10–2000 characters after whitespace trimming. Request envelope capped at8192bytes.
Validation responses do not echo raw input.201=new action,200=identical idempotent replay,404=unknown run,
409=ineligible source or competing confirmation,422=invalid input/candidate,413=oversize,415=wrong MIME,
503=trusted-record evaluation/storage unavailable. No generic reevaluation endpoint is added.

GET /api/runs/{id}/review-history returns typed actions (zero/one),current_reviewed_assessment,eligibility,
current authoritative candidates and vendor name. GET /api/runs/{id} remains the exact original RunSnapshotV1.
Run summaries add nullable reviewed_outcome,reviewed_at,review_action_id through one outer-joined query.
Recorded outcome/owner/updated timestamps,queue filters and dashboard metrics keep their original basis.
A reviewed-ready case remains in the recorded-review filter, with both statuses explicitly labelled.

## Append-only persistence and migration

Additive migration002-human-po-review creates review_action and schema_migration without replacing an
existing table. Existing baseline initialization stays idempotent. Each action has server UUID ID/source run,
client key/request fingerprint and validated JSON containing action type,authoritative PO ID,rationale,
demo actor label/disclaimer,server UTC timestamp,original DecisionV1,full reassessed DecisionV1/findings,
exact source PolicyV1/version,source snapshot fingerprint,canonical authority SHA256 and selection provenance.
Fingerprint is canonical JSON over sorted validated vendor/PO/billed snapshots (not a financial total).
It records identity of used facts; it is not an archived full procurement master or tamper-proof signature.

One unique run_id enforces first-confirmation-wins. BEGIN IMMEDIATE serializes the short read/evaluate/insert
transaction; there is no network work. Action and full assessment are one atomic row. Identical same-key
request returns the saved row; changed content or competing key conflicts. Triggers reject UPDATE,DELETE
and replacement INSERT. No edit/delete/correction action is exposed. Source run/stage/policy/master/ledger
rows are not written. Failure before commit leaves no partial action; uncertainty after response loss can be
retried with the same key. See SQLite transaction/trigger documentation:
https://www.sqlite.org/lang_transaction.html and https://www.sqlite.org/lang_createtrigger.html .

History remains the stored reassessment even if authority later changes; it is not silently reevaluated on GET.
The source policy is used at action time, current procurement/billed records at action time. Source decision,
extraction and stage rows remain historical facts. Policy preview remains read-only and operates on the
original automated context; it does not inherit a human confirmation or change the reviewed action.

## UI and authorization honesty

Eligible cases offer Review PO candidates. A native modal shows authoritative PO/vendor/status/authorized
net/provenance,requires rationale and a demo label,and makes a deliberate Confirm PO & re-evaluate request.
No default candidate selection. Pending state disables submission and uses a synchronous submission lock.
The same key is retained for uncertain retries. Modal keyboard handling is native; Escape/cancel restore
focus; completed submission focuses the result. Async results and original/current outcomes remain distinct.
Outstanding findings,owner/action,stored time/rationale and provenance remain available. No false success
for a reassessment that still needs review. Existing design tokens are reused; no broad redesign.

**Demo reviewer — identity not authenticated.** Labels are claims supplied by a demo user,not verified
employees. This is not production maker-checker,employee authentication or tamper-evident compliance logging.
**Release requirement:** before any public-facing deployment, restrict these write controls with a basic
access safeguard and request protections appropriate to that deployment. Full auth,approval/payment,
correction/supersession workflows and hosting are not implemented in this phase.

## Regression data and local review

Separate data/human_resolution_manifest.json contains MISSING_PO_VALID only; original seed and frozen10-case
manifest remain unchanged. Meridian alias Meridian Cloud Ltd. resolves to approved Meridian Cloud Pvt Ltd.
Net10000/tax1800/gross11800,qty2/unit5000,dated2026-11-18,PO absent. PO1042 remaining net80000/qty16 supports
it; no existing billed key/amount conflict. Original review becomes ready only after human identity selection.
AMBIGUOUS_PO is reused unchanged; missing item/qty/price keep review after confirmation.

python scripts/generate_review_fixtures.py uses the existing generator with nullable fields represented as
Not stated. Two native PDFs live under tests/fixtures/human_resolution; no frozen PDF bytes are replaced.
Normal integration/browser test extraction is explicitly TEST_ONLY. Real PDF parsing/source grounding,
financial rules,API,stages,action persistence and restart behavior run around it. No live-provider accuracy
claim or Gemini inference is needed for this human workflow. See PHASE_06B1_REPORT.md for actual evidence.
