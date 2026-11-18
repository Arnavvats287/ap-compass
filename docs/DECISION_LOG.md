# AP Compass — Decision log

Record deliberate **product, business-rule, contract and architecture changes**, not every code edit. This file protects us against unplanned architecture churn. Existing accepted rules are not up for independent Codex reinterpretation.

| ID | Status | Decision | Rationale / trade-off |
|---|---|---|---|
| ADR-001 | ACCEPTED | PS-1 is a two-way invoice-to-PO **operational** decision workstation; no payment/posting authority | Align with actual AP needs and brief |
| ADR-002 | ACCEPTED | AI for extraction only; finance outcomes are deterministic | Testable, auditable controls |
| ADR-003 | ACCEPTED | PO identity separate from financial eligibility | Preserve correct overbilling and mismatch findings |
| ADR-004 | ACCEPTED | Immutable prior billed ledger; analysis history does not consume PO | Safe reruns; no demo-induced financial-state mutation |
| ADR-005 | ACCEPTED | Evidence states distinguish native verified, source located unverified and missing | Avoid false certainty on scans |
| ADR-006 | ACCEPTED | Business decision independent of execution failure; real persisted stage events | Honest live execution |
| ADR-007 | ACCEPTED | Isolated pure rule evaluators, policy version snapshots, additive contracts | Tolerance and future policy changes without cascading rewrites |
| ADR-008 | ACCEPTED | Seven sequential review gates; 02 and 03 may run in parallel after 01 with separate ownership | Speed without integration conflict |
| ADR-009 | ACCEPTED | Customer-value UI: decision → evidence → responsible party → next action; dashboard + queue/history | Nontechnical finance stakeholder can act |
| ADR-010 | DEFERRED | Interactive Confirm PO + re-evaluation | High signal after MVP, not required for core |
| ADR-011 | REJECTED FOR SUBMISSION | Learned auto-approval hints, broad batch inbox, big agent framework, ERP posting, elaborate analytics | Too risky/large for 2.5-day build |
| ADR-012 | PROVISIONAL | Exact Gemini model ID and host | Select only from tested account/deployment evidence |
| ADR-013 | ACCEPTED | INR net-of-tax synthetic fixture set (6 vendors/7 POs/3 billed records/10 scenarios) | Reproducible financial oracle and narrative |

## Change-request record template

When proposing a change, append a short entry with:

- **ID / Date / Requester / Status:** PROPOSED → ACCEPTED or REJECTED.
- **Business behavior:** What user-visible outcome changes? Why?
- **Invariant impact:** What hard safety rule still applies?
- **Contracts/data needed:** Is it a policy-only change, an added finding, new optional extraction field, or a genuine breaking change?
- **Affected files/owners:** Explicit minimum file set; do not assume whole-project changes.
- **Before/after acceptance examples:** Expected decisions and reason codes, including one negative case.
- **Rollback:** How can the previous policy/behavior be restored?
- **Approval:** Builder accepts before code or Codex touches shared types.

Do not rewrite past records to pretend a previous design was never chosen. Record a superseding entry.
