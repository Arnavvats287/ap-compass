# AP Compass â€” Decision log

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
| ADR-009 | ACCEPTED | Customer-value UI: decision â†’ evidence â†’ responsible party â†’ next action; dashboard + queue/history | Nontechnical finance stakeholder can act |
| ADR-010 | DEFERRED | Interactive Confirm PO + re-evaluation | High signal after MVP, not required for core |
| ADR-011 | REJECTED FOR SUBMISSION | Learned auto-approval hints, broad batch inbox, big agent framework, ERP posting, elaborate analytics | Too risky/large for 2.5-day build |
| ADR-012 | PROVISIONAL | Exact Gemini model ID and host | Select only from tested account/deployment evidence |
| ADR-013 | ACCEPTED | INR net-of-tax synthetic fixture set (6 vendors/7 POs/3 billed records/10 scenarios) | Reproducible financial oracle and narrative |

## Change-request record template

When proposing a change, append a short entry with:

- **ID / Date / Requester / Status:** PROPOSED â†’ ACCEPTED or REJECTED.
- **Business behavior:** What user-visible outcome changes? Why?
- **Invariant impact:** What hard safety rule still applies?
- **Contracts/data needed:** Is it a policy-only change, an added finding, new optional extraction field, or a genuine breaking change?
- **Affected files/owners:** Explicit minimum file set; do not assume whole-project changes.
- **Before/after acceptance examples:** Expected decisions and reason codes, including one negative case.
- **Rollback:** How can the previous policy/behavior be restored?
- **Approval:** Builder accepts before code or Codex touches shared types.

Do not rewrite past records to pretend a previous design was never chosen. Record a superseding entry.


## ADR-014 — Phase 2 possible-duplicate review heuristic

- **Date / authorization / status:** 2026-11-19; Phase 2 explicitly authorizes deterministic possible-duplicate
  review findings. IMPLEMENTED FOR PHASE 2 REVIEW; not a change to an accepted hard invariant.
- **Business behavior:** A nonexact invoice-number separator variant for the same canonical vendor, or the same
  vendor/PO/currency/net within seven calendar days, produces POSSIBLE_DUPLICATE review. It never proves a duplicate.
- **Rationale:** Transparent, reproducible signals using existing facts, without fuzzy identity, confidence or model judgments.
- **Invariant impact:** Exact billed duplicates always block; value/quantity ceilings remain independent; no authority writes.
- **Contracts/data:** No extension or seed change. Implementation: domain/controls.py; tests: test_finance_engine.py.
- **Acceptance:** Separator variant -> review; equal business facts at seven days -> review, at eight days -> no such signal;
  known exact duplicate -> block at every tested price tolerance. All other required controls still run.
- **Review/rollback:** Reviewer may adjust the heuristic through CHANGE_RULE_PROTOCOL with a failing regression first.
  Removing this review-only heuristic does not remove exact-duplicate or financial controls.


## ADR-015 — User-authorized Phase 3 two-model extraction routing

- **Date / status:** 2026-11-19; ACCEPTED scope by explicit user routing update.
- **Decision:** Flash-Lite is primary; Flash is a bounded extraction-quality escalation. Native/scan model choice
  is environment-configured, using only these two models. This supersedes the earlier one-model stack assumption.
- **Boundaries:** Identical extraction contract and independent evidence verification. No model-owned verification,
  financial decisions, PO selection, ledger writes, security-judgment model or third fallback model.
- **Limits:** At most two explicit attempts per invoice and one stronger attempt. No escalation caused by business
  overbilling, duplicates, bank mismatch, inconsistent stated totals or REVIEW/BLOCK outcomes. Quota/outage is technical failure.
- **Observed selection:** Flash-Lite provisional for scans; it returned real results. Flash metadata is accessible,
  but tested inference returned gateway errors/timeouts, so live escalation and the full Phase 3 gate remain unresolved.
- **Contracts/data:** No public contract, database, finance engine or manifest changes. Review evidence is in
  PHASE_03_REPORT.md and PHASE_03_LIVE_RESULTS.json; no deployment or paid service added.


## ADR-016 — Phase 3.1 required primary provider; optional escalation

- **Date / status:** 2026-11-19; ACCEPTED by the explicit Phase 3.1 stabilization request.
- **Revised release gate:** One genuinely working extraction provider supporting native and image-only PDFs,
  independent native evidence verification, conservative scan evidence and safe failures is required.
  Stronger-model escalation is optional and must stay disabled until genuine stronger inference is verified.
  This supersedes ADR-015's required two-model acceptance assumption, not its extraction-only authority boundary.
- **Configuration:** GEMINI_ESCALATION_ENABLED=false by default. Disabled mode requires/checks/constructs only
  the primary provider and uses it for native/scanned inputs; unused optional overrides are ignored.
  Enabled mode keeps the two-attempt/one-stronger limit, with optional metadata checked only when needed.
- **Usable facts versus no extraction:** A schema-valid, grounded primary with meaningful but incomplete or
  source-uncertain facts is retained if optional escalation hits outage, timeout or quota failure. Metadata exposes
  every failed attempt and retained_primary=true. Malformed, empty or unavailable primary without usable facts
  still fails technically. This is fact retention, never model approval or an evidence upgrade.
- **Honest counts:** Adapter-local inference_called distinguishes metadata-only failures from generation attempts;
  request-local tracking handles deadline cancellation without inventing an unstarted stronger inference.
- **Unstated scanned line net:** Without independent verification of an explicit statement, image/mixed-source
  optional line.net remains None; its unverified raw claim may remain for audit. Header totals are untouched.
  Independently verified native line net in a mixed document is retained. No OCR, corrected totals or zero filling.
- **Preserved boundaries:** Same public Pydantic contracts, financial rules, procurement/billed records and fixture
  expectations. No third model, registry, orchestration, UI or deployment. No new Flash probes in this repair.
- **Evidence:** PHASE_03_1_REPORT.md and PHASE_03_1_LIVE_RESULTS.json. Earlier Flash failures remain historical
  evidence; revised acceptance does not assert that stronger-model inference ever succeeded.


## ADR-017 — Phase 4 execution errors, stage ownership and local workflow

- **Date/status:** 2026-11-19 IST, ACCEPTED by the explicit Phase 4 request.
- **Approved shared addition:** RunSnapshotV1.execution_error_code: str | None = None.
  QUEUED/RUNNING/COMPLETED require null; PROCESSING_FAILED/INTERRUPTED accept only sanitized
  allowlisted categories. Historical snapshots without the field remain readable. No messages,
  provider bodies, secrets or account values. No other shared fields or database schema changes.
- **Persistence:** Existing InvoiceRun/RunStage/PolicySnapshot tables. RunStage rows exclusively own
  stages; run JSON persists an empty stage array and detail reconstructs with one atomic joined read.
  Policy version collisions fail closed; authoritative procurement/billed rows are read only.
- **Execution:** Tracked asyncio tasks, one active workflow per process via semaphore, short transactions
  outside inference. Restart interrupts leftover work without model replay. This requires one Uvicorn
  process; no durable/distributed queue or multi-process recovery guarantee.
- **Documents:** AP_COMPASS_DOCUMENT_DIR, opaque generated filenames, bounded PDF upload, atomic local
  writes, controlled run-based serving. Runtime storage and credentials stay ignored by Git.
- **Provider runtime:** Only verified Flash-Lite, escalation disabled. No mandatory per-invoice metadata
  lookup; standalone diagnostics keep explicit verification. Clients close per extraction; typed
  generation failures remain technical, and missing credentials do not prevent boot/health.
- **Evidence:** PHASE_04_REPORT.md / PHASE_04_LIVE_RESULTS.json / PHASE_04_FAILURE_EXAMPLE.json.
  Three real generation requests, expected decisions and reloads, unchanged authoritative-row hash.
- **Boundaries:** Financial rules, identity, evidence grounding, manifests, fixtures and UI unchanged.
  The obsolete Phase 1 assertion that uploads do not exist now asserts 415 on missing multipart data.
  No new financial behavior, contract exception, paid deployment, optional model call or Phase 5 work.
