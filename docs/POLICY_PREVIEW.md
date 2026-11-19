# Policy impact simulator

The decision workspace offers a read-only **Policy preview**, separate from worklist filters.
Only unit-price tolerance is selectable:2% or5%. The recorded AP decision and active policy never change.

## API and computation

POST /api/runs/{run_id}/policy-preview accepts {"price_tolerance_pct":"0.05"} (or"0.02").
API-local Pydantic models validate finite Decimal values and reject binary floats, unsupported tolerances
and extra fields. Unknown run404; queued/running/technical or incomplete business analysis409; invalid input422.
The response includes original_policy, preview_policy, original_decision, preview_decision and changed.
Changed compares business fields excluding policy_version; it does not merely compare policy identities.

The coordinator reads the valid stored extracted invoice and recorded immutable PolicyV1, copies every
other control, assigns a deterministic content-derived preview version, loads current trusted vendor/PO/
billed records, calls build_context(...) and then the same evaluate(context,policy). No separate price-rule
paths exist. Current authority can differ from historical authority; the UI says Current trusted records.
Repeated identical inputs/current records return identical responses. An immutable preview is not saved.

## Protected controls

Changing tolerance never overrides PO net commitment, ordered quantities, remaining line authorization,
exact billed duplicates, currency/vendor/PO consistency, required facts or source evidence. Explicit PO is
required under the current framework. Locked controls are informational; there are no toggle workarounds.
No frontend financial arithmetic or rule evaluation occurs. Both tolerance choices call the same API.

## No document reprocessing, no mutation

Preview calls no extractor, Gemini, PDF parser or document store. It creates no inference usage and writes
no run JSON, stage rows, PolicySnapshot, procurement master or billed history. The original outcome remains
prominent. A temporary preview can be ready while the actual recorded decision still requires review.
This does not authorize payment/posting, apply an organization policy or create an approval revision.
There is no automatic preview request on mount/open; selecting a tolerance makes one explicit request.
Controls disable during that request; results appear only after the response. Failures preserve the original.

## Decision trace

received → extracting_invoice → matching_records → evaluating_controls → finalizing map to business-readable
nodes. Complete means that operation executed; supplier/PO ambiguity and financial findings remain separate.
BLOCKED can accompany five PASSED stages. Failed/interrupted execution produces no business outcome.
Use recorded named timings when available, otherwise valid persisted start/finish durations. Missing time
is an em dash, never invented zero or remaining-time prediction. Stage details expose concise explanations
and timestamps, not prompts or reasoning. Horizontal desktop nodes become vertical below900px. Only actual
RUNNING connectors move, using transform; reduced motion leaves text/icon/border state with no movement.
The static preview path is stored extraction → current trusted records → selected policy → controls evaluated;
it never mimics document extraction.

## Frozen demo and limits

PRICE_3PCT uses the existing manifest:PO-2010,qty10,unit1030,net10300,tax1854,gross12154. Remaining PO net25000
and quantity25 accommodate it; only price variance should require review at2%, then ready at5% if every
other control passes. Overbilling and exact duplicates remain blocked at both tolerances. Native fixture:
.venv/Scripts/python scripts/generate_fixtures.py --case PRICE_3PCT (defaults still generate the original four).
No global policy editing, persisted reevaluation, PO confirmation or Phase6B actions are implemented.
