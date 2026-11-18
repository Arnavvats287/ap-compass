# AP Compass — High-signal business scenarios

**Plan scenarios early; freeze creative details after a functional vertical slice.** Official Zamp brief asks for 2–4 realistic, nontrivial edge cases. Avoid designing a new subsystem for each example. All showcased cases need an actual PDF, authoritative seed records, required findings, correct business decision, and visible next action.

## Two core scenarios — keep regardless of creative discussion

| Scenario | What analyst sees | Required logic | Expected outcome |
|---|---|---|---|
| Ambiguous missing PO (`AMBIGUOUS_PO`) | Two plausible open Meridian POs and no stated PO reference | Canonical vendor, ranked PO candidates, no arbitrary selection | REVIEW_REQUIRED; `PO_AMBIGUOUS`, `PO_REFERENCE_MISSING`; AP confirms PO |
| Partially billed PO overrun (`OVERBILLED_PARTIAL`) | Aster PO original ₹200k; historical billed ₹175k; current invoice ₹30k; remaining ₹25k | Identify explicit PO **before** eligibility; ₹5k net and 1 unit over | BLOCKED; `PO_BALANCE_EXCEEDED`, `PO_QUANTITY_EXCEEDED`; Procurement/Vendor correction |

## Strong candidates for final slots 3 and 4

| Candidate | Why a business head cares | Needs before demo | Implementation burden |
|---|---|---|---|
| Duplicate in a changed layout (`DUPLICATE_REISSUED`) | Prevent accidental second billing of the same invoice | Prior billed ledger lookup; invoice identity normalization | Low |
| Changed payment instructions (`BANK_CHANGED`) | Protect against payment redirection | Verified master bank details, PDF extraction of payment instructions | Medium |
| Scan with conflicting totals (`SCAN_CONFLICT`) | Recognize uncertain source and arithmetic without inventing a fix | Multimodal route + source-evidence uncertainty | Medium |
| Invoice prompt injection (`INJECTION`) | External document cannot override financial controls | Untrusted content separation, overbilling invariants | Low as security regression |
| Price tolerance 2% → 5% (`PRICE_3PCT`) | Adapts to customer policy without code rewrite | Versioned price policy, line net/qty under hard limits | Low–medium |
| Unknown supplier (`UNKNOWN_VENDOR`) | Stops unapproved vendor without failing extraction | Exact vendor master lookup; unknown vendor finding | Low |

## One creative case we can design together after MVP

Candidates to discuss: **duplicate with corrected invoice identifier and near-match ambiguity**, **vendor with a legitimate PO but an unrecognized item**, **a bundled invoice that conceals unauthorised spend**, or **multiple independent exceptions with conflicting ownership**. Don't claim all can be built. Pick the one with the best customer story using existing fields and only expand schema if we can test it safely.

## Selection test for a new scenario

A scenario earns a demo slot only if it:
1. Illustrates a real AP control/decision rather than file upload error.
2. Has a clear and defensible expected action that a finance user recognizes.
3. Runs from a real synthetic PDF all the way through persisted stage events and UI.
4. Includes at least one control that a simplistic `PDF → LLM → JSON` approach would mishandle.
5. Can be added without breaking the happy path, rewriting contracts or missing the feature-freeze deadline.

**Current status:** No new creative case selected; do not begin extra edge-case implementation in Segment 01. Existing `data/fixture_manifest.json` remains the test oracle.
