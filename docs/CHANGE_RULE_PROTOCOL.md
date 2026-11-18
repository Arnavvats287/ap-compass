# Business-rule change protocol — no cascade rewrites

Goal: answering a customer question like “What if tolerance is 5% instead of 2%?” must not require touching upload logic, model prompts, every API, and UI components.

## Every business rule change follows 7 steps
1. Name the changed business behavior in customer language and identify required input facts. Distinguish **config change** from **new data requirement**.
2. Add a failing unit test and (when relevant) a fixture expectation. Include negative and boundary tests.
3. Change a `PolicyV1` field for a threshold/feature flag, or add one **isolated pure evaluator** that returns `FindingV1`. No LLM prompts for deterministic rules.
4. If a new document field is needed, add it **nullable and versioned** to `ExtractedInvoiceV1`. Existing extracted runs must remain readable. Update only the relevant extraction adapter and contracts tests.
5. If persisted schema must change, use an additive migration/default or an explicit version conversion. Never truncate existing runs to make new code work.
6. Produce an immutable new evaluation revision under a policy snapshot; preserve the original. Re-evaluation from stored extracted facts must make **zero** Gemini calls when all needed fields already exist.
7. Run unit + integration + regression fixtures; inspect the UI for unknown/new codes and ensure the new policy cannot bypass hard controls.

## Frozen hard financial invariants
- No silent READY from missing/unknown critical data.
- Vendor/PO contradiction cannot be resolved by ranking points.
- Exact known billed duplicate cannot become READY by changing price tolerance.
- Invoice cannot exceed available PO value/quantity under this demo policy.
- Technical run failure is not a business decision.
- Reanalysis does not mutate prior billing or PO commitments.

## Change categories

- **Threshold change:** `price_tolerance_pct=0.05`; no new extraction/model calls; compare same line facts against same PO and history; persist policy version and new result.
- **New deterministic rule over existing fields:** add evaluator + reason/action owner; e.g., prohibit closed POs. No document changes.
- **New extracted fact:** e.g., bank details; optional source field, model schema/prompt version increment, evidence test. Old runs with missing bank field remain valid historical results or are marked not evaluated for that new control, never silently asserted safe.
- **New human action:** audited action and new run revision; no overwrite of earlier results or automatic posting.

## Danger signs that trigger a design review
- Business rules inside React components / FastAPI routes / Gemini prompts.
- Many files modified for a simple threshold change.
- A rule method calling DB/AI/network directly.
- A score or model output being interpreted as an approval probability.
- Recalculating prior billed state from demo analysis runs.
- Changing a policy without retaining which version produced an earlier decision.
