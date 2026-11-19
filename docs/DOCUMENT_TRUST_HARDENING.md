# Defensive hardening of document verification boundaries

## Header consistency

The document adapter compares supported labelled observations for invoice number, net, tax and total across all independently inspected native pages. The label whitelist accepts revised, final and corrected qualifiers. Previous balances, customer balances and explicitly labelled line subtotals are outside that whitelist. Decimal equality accepts equivalent scale and standard grouping, and explicit disagreement between recognized currencies is treated as uncertainty. The check uses parser-bounded text and page counts.

Grounding still requires unique local support. A disputed field can retain the model's extracted value and original cited page, quote and raw value for inspection, but cannot become NATIVE_VERIFIED. The ordinary evaluator can request review for missing independent support or still block on a separate hard control. The adapter never substitutes a new total. EvidenceRefV1 stores one citation per field here. Other observations remain in the source PDF. Same-page identical duplicate locations still have to satisfy the existing uniqueness rules. Unlabelled, unsupported numeric/layout conventions, multiple currencies without explicit prefixes, and arbitrary multi-invoice interpretation are outside this bounded check.

## Raster and payment uncertainty

Phase 6B.2B.1 supersedes the technical gate described in this historical section. See MIXED_DOCUMENT_REVIEW.md for current semantics.

The parser enumerates raster placements for readable text pages. A single small opaque swatch can use native routing only when its bounded, decoded source pixels are uniformly colored and mask checks pass. Dimensions alone cannot establish harmlessness. A normal nonuniform logo can conservatively route as mixed. Mixed pages send bounded page images to extraction and do not independently verify their quotes. Unaffected native pages can still ground non-bank fields.

Chose Option A. A mixed document without a complete bank object fails with existing UNSUPPORTED_PDF after a usable provider reply. The request and measured timing remain accounted for. A supplied bank object across mixed content stays unverified even if its citation points at a native page. This avoids presenting a possible discrepancy as an independently verified mismatch. The existing image-only path remains review-only under source evidence controls. Its missing bank object still has the existing informational absence finding. That finding represents absent extracted details, and does not verify the visual absence of payment text.

Option B requires distinguishing possible payment presence from confirmed absence with a trusted signal. A future additive nullable integrity field on the extracted snapshot could express that uncertainty and provide an explicit financial review reason. Old snapshots could default to unspecified. Persisted run detail, the evaluator and the workspace would need to consume it. This phase uses the existing technical classification for mixed content and requires no shared contract or storage changes.

## Rendered readability

The isolated parser renders readable-text pages in grayscale using at most 0.75 scale and a nominal 640-pixel long edge. A uniform raster causes EMPTY_PDF before extraction. This tests whether any contrast exists at the sampled scale. It does not match glyphs to pixels, recognize text, or establish visibility of individual values. Decorative marks or other visible content can keep a partially obscured page nonuniform. Faint or purely chromatic contrast can be lost in the sample.

The subprocess keeps the 8 MiB file cap, 10-page cap, 512 MiB process memory limit and 12-second timeout. Provider images remain capped at 1600 pixels per edge, 2 million pixels per page, and a 12 MiB aggregate encoded payload. Inspection does not change inference concurrency. See the phase report for measurements and exact verification.
