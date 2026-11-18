# Phase 3 — Document adapter

**Scope:** In-memory extraction only. No upload endpoint, persistent document storage, database writes,
financial-rule changes, UI, worker service or run orchestration. Phase 2 contracts remain unchanged.
**Gate:** Revised required-provider acceptance PASS after Phase 3.1; architectural review pending. Escalation is optional and disabled (ADR-016).

## Entry points

```python
from app.ai.gemini import extract_configured_pdf
# Caller explicitly loads its trusted backend environment first.
result = await extract_configured_pdf(pdf_bytes)
invoice = result.invoice  # Existing ExtractedInvoiceV1
metadata = result.metadata  # Adapter-local, immutable technical metadata
```

For deterministic offline tests inject an ExtractionProvider into `app.documents.pipeline.extract_pdf`.
Imports never create clients or make provider calls. No authoritative procurement, billed or policy snapshots
are supplied to Gemini. Returned JSON has no decision, selected authoritative PO, confidence or verification-state field.

## PDF inspection and resource bounds

`inspection.inspect_pdf` checks nonempty bytes, <=8 MiB, exact PDF header, final EOF marker and successful parsing.
A fixed `python -m app.documents._parse_process` command receives PDF bytes on stdin, with shell=False and no
API-key/model environment variables. It is a short-lived resource boundary, not a background worker or full OS sandbox.
The subprocess holds a hard 512 MiB memory cap (Windows Job Object / POSIX RLIMIT_AS) and a 12-second wall timeout.
It never executes PDF instructions, JavaScript, document URLs or embedded content. MuPDF diagnostic output is suppressed.

Reject encryption (including trailer encryption), repaired/corrupt PDFs, blank documents, >10 pages,
embedded-file portfolios/XFA, invalid page dimensions, >30k native characters/page or >150k total.
Page sides above 14,400 points are rejected before rendering. Native text extraction excludes image decoding.

Per-page classification:

- native_text: >=40 printable native characters, no replacement characters, no dominant raster layer.
- image_only: unusable/sparse native text; render actual page pixels.
- mixed: a dominant raster layer plus usable text, or a document with different per-page routes.

Preserve original 1-based page numbers and all bounded per-page native text. Render only unusable/mixed pages,
RGB PNG at <=120 DPI, <=1600 pixels/edge and <=2M pixels/page. The base64 aggregate is capped at 12 MiB.
Mixed pages with a raster layer remain unverified; native pages in a mixed document can independently verify.
Rendered bytes and text stay in memory. Development fixture/report commands are explicit exceptions for synthetic test artifacts.

## Provider and schema

Pinned official `google-genai==3.5.0`, `PyMuPDF==1.26.6`, `python-dotenv==1.2.4`.
The current SDK requires Pydantic >=2.12.5, so the existing dependency pin moved from 2.12.4 to installed/tested
2.14.3. No public model fields changed; all 129 prior tests still pass.

API: `client.aio.models.generate_content`, Gemini Developer API v1beta, fixed
`https://generativelanguage.googleapis.com`. Text goes in explicit untrusted page envelopes; scan/mixed pages use
actual PNG `Part.from_bytes`, never URLs or an uploaded file service. Tools are empty and automatic function calling
is disabled. Returned tool calls are rejected without execution.

A compact JSON generation schema describes one invoice and source claims. Detailed regex/length/count bounds are
removed from the generation grammar after a real provider rejection; they remain enforced by strict local Pydantic
validation. No floats for money, extra fields, invalid dates, model-supplied evidence states or malformed JSON are accepted.
Private limits: 256 KiB response, 50 lines, 260 claims, 600 characters/text, decimal strings with <=18 integer/6 fractional digits.
Unknown source facts remain None. Optional missing line net stays None; extraction never computes it. For image/mixed input, optional line net without independently verified explicit source support is also cleared to None; its raw claim remains unverified for audit. Header totals are never repaired.
The frozen BankInstructionsV1 cannot represent partial nullable bank subfields: incomplete bank instructions fail
technically rather than invent digits. Clearly printed/claimed bank instructions cannot silently become bank=None.

## Independent evidence verification

The provider supplies only field/raw value/page/quote claims. `documents.evidence` creates EvidenceRefV1 itself.
Stable keys exactly match Phase 2: vendor_name_raw, invoice_number, invoice_date, po_reference, currency,
net/tax/total; lines[i].item_code/qty/unit_price_net/net; bank_instructions.account/ifsc. Description evidence is additive.

For NATIVE_VERIFIED require one claim, the stated native page, a unique independently located quote,
coherent raw/normalized value and one field-specific local source location:

- Header amounts must occur under the appropriate net/tax/gross label; incidental repeated numbers never suffice.
- Native labelled item blocks must bind quantity/price/net to the same exact item code, never another line.
- Supplier identity requires an explicit vendor label or a unique isolated top supplier heading; buyer/bill-to context
  and ambiguous headings cannot verify supplier identity.
- Duplicate field labels/claims, wrong values, wrong page, unsupported layouts or ambiguous quotes remain unverified/missing.
- Dates support ISO and explicit English month-name formats; ambiguous numeric dates are not independently verified.

There are no fabricated OCR confidence values or bounding boxes. Image/mixed-page quotes retain page and claim
metadata but are SOURCE_LOCATED_UNVERIFIED; nonexistent page/quote or missing facts are MISSING.
Native verification establishes fidelity to the stated invoice, not approved vendor identity or financial eligibility.
Source verification is conservative for known labelled block layouts; arbitrary tables, locales and multi-invoice bundles
are not claimed to have general verified coverage. The existing financial engine requires review for unverified critical scan facts.

## Revised required primary / optional escalation (ADR-016)

Phase 3.1 deliberately revises acceptance: one genuinely working provider with native/image support and honest
independent evidence handling is required. Stronger inference is optional. Earlier Flash gateway failures remain
historical evidence; this revision does not claim Flash ever worked.

Backend configuration (.env loading remains explicit):

```dotenv
GEMINI_PRIMARY_MODEL=gemini-3.5-flash-lite
GEMINI_ESCALATION_ENABLED=false
GEMINI_ESCALATION_MODEL=gemini-3.6-flash
GEMINI_SCAN_MODEL=gemini-3.5-flash-lite
GEMINI_ESCALATION_THINKING_LEVEL=MINIMAL
```

Primary-only is the default. Only primary metadata is checked and only its provider is constructed. Native and
scanned documents use primary; stale optional model/thinking/scan overrides are ignored. The development smoke
utility respects the same active-model set. Invalid boolean spellings fail configuration instead of enabling requests.

Enabled mode retains two attempts total and one stronger attempt, the same schema and grounding, and no
financial-outcome triggers. Optional metadata is checked lazily on use. Keep escalation disabled until genuine
stronger inference is verified; fake-enabled tests are not live proof. No third model or provider registry.

### Usable facts and safe optional failure

A strict-schema-valid grounded extraction with meaningful facts can be incomplete or source-uncertain. If optional
escalation then has outage, timeout or quota failure, return that exact primary snapshot with retained_primary=true,
primary selected_model_id, and failed optional error/status/timing/usage metadata. No evidence is upgraded.
The existing evaluator subsequently determines review/block; retaining facts is not model approval.

Malformed, invalid, entirely empty or unavailable primary with no usable facts still raises a technical error.
Optional failures outside the requested outage/timeout/quota categories remain fail-closed. No business decision
is generated by the adapter; no facts are fabricated to hide primary failure.

### Counts and bounds

Normal invoice: one inference; maximum two attempts and one stronger attempt. SDK automatic retries remain off.
Optional metadata failures have inference_called=false and do not count as generation. Request-local tracking also
handles a whole-attempt deadline cancelling metadata before generation starts. Failed usage stays unknown, not zero.

Record requested/selected model, escalation reason, retained_primary, per-attempt error/status/timing/inference_called,
reported model ID and available tokens. The 30s default / 45s maximum per-call limit and 12s parser limit remain.
Optional metadata gets at most 15s and half its attempt budget. No arithmetic, commitment, duplicate, bank-master
comparison or financial REVIEW/BLOCK outcome triggers escalation. There is no distributed quota scheduler.

## Errors, secrets and verification

Typed errors expose allowlisted codes, attempt metadata and HTTP status only. No raw provider messages, bank
accounts, API keys, model responses or PDF content are logged. Internal result/page/reply dataclasses hide source
payloads in repr. Parser environment excludes keys. There is no model tool or database authority.

See PHASE_03_1_REPORT.md and PHASE_03_1_LIVE_RESULTS.json for current evidence: 229 tests pass, including
all 129 foundation/finance regressions and 100 document tests. One extra real primary-only scan call returned
line.net=None, preserved gross 86200, and the unchanged evaluator returned REVIEW_REQUIRED with discrepancy 3600.
All scan evidence stayed unverified; zero Flash metadata/generation requests occurred in stabilization.
Earlier genuine native successes and failed stronger calls remain in the historical Phase 3 report/results.
No general model-accuracy or live stronger-model claim is made. Phase 4 remains unauthorized.

## Official references consulted

- https://googleapis.github.io/python-genai/ — async generation, JSON schema, image Parts, HTTP timeout/retry configuration.
- https://ai.google.dev/api/models — metadata and supported-generation-method checks.
- https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/thinking — Flash MINIMAL thinking support.
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information — process memory cap.
