# Phase 6A.1 — Signature product design overhaul

2026-11-19 IST. **Local visual/engineering gate PASS; stop for user architectural/visual review.**
Base95e6e66ea6c9ce7d48f10466f40d9aa4af0e89d1. Branch codex/phase-06a1-signature-ui.
Checkpoint phase-06a1-signature-ui. Full final SHA and independently verified publication are in the chat
handoff (a commit cannot include its own SHA). Previous checkpoints/default branch remain protected.

## Original critique and chosen concept

The actual Chrome baseline, not a source-only audit, showed an empty forest attention plane, a source pane
starting around414px, a large identity header, policy/trace before evidence and five cramped trace cards.
The serif page heading carried most identity while small operational labels weakened the work itself.
Mobile preserved information but amplified stacking. See PHASE_06A1_DESIGN.md, written before implementation.

**Editorial Fintech × Interactive Control Room: the case spread and execution spine.** Keep the coherent
warm cream/forest/mint/citrus palette; change composition and hierarchy. The attention panel now combines
linked workloads, an accessible real-count outcome orbit and a distinct flagged-net ledger band. No new metric.
The upload surface has a stronger full-width action and clear drag/drop boundary; table remains precise.

Workspace is a compact case band, anchored section rail, top-aligned source/primary decision spread,
earlier evidence, then optional audit detail. Reason, backend monetary comparison, owner and action stay
exposed. All findings/PO records are one native disclosure away; ambiguous alternatives open initially.
The desktop source/decision top is323.48px at1440/1024 vs about414px before: approximately91px recovered.
The PDF itself follows its real source heading/help. No placeholder source or fabricated highlighting.

The signature trace is a full-width two-part process map: readable vertical execution spine, distinct
operation icons/completion marks, actual timing, keyboard details and a separate outcome destination.
A completed BLOCKED case has five complete stages and a blocked business outcome, not failed extraction.
Only the actual RUNNING connector/spinner moves. Mobile stacks the destination below the same spine.

Policy has paper recorded/forest hypothetical comparison at full width. The desktop section rail retains
the recorded status while browsing the preview. Actual API response owns the result; no JavaScript finance.
Original decision, current-policy meaning, no-reprocessing language and payment restriction are unchanged.

## Components, patterns and deliberate choices

Original React/CSS/SVG implementation; no new package, copied component collection or Next.js dependency.
Aceternity timeline/bento composition was studied as context, shadcn selection as interaction reference,
Motion accessibility as motion guidance. Native radio/details and existing CSS are sufficient here.
Sources: https://ui.aceternity.com/components/timeline ; https://ui.aceternity.com/components/bento-grid ;
https://ui.aceternity.com/licence ; https://ui.shadcn.com/docs/components/base/toggle-group ;
https://motion.dev/docs/react-accessibility . No Pro code/assets copied. No new licensing obligation.

Typography tokens: secondary working copy14px, small body16px; selective Georgia editorial titles,
Segoe UI/system sans working text and tabular money. Existing semantic palette/radius/motion tokens retained.
New signature.css isolates layout changes; native focus stays immediate, finite feedback160–220ms.
No marketing hero, photos, shader, tilting table, animated counters or decorative loops. Motion package
rejected because it would add weight without improving these native interactions. Full-width vertical trace
chosen over another tight horizontal strip; original overview palette retained deliberately, not by inertia.

## Two rendered iterations and evidence

Ignored local artifacts, rooted at C:/Users/Asus/Documents/ChatGPT/ap-compass/:

| Evidence | Location |
|---|---|
| Original15 real views +7 controlled states | tmp/phase06a1-before/ |
| First redesign, same widths and policy states | tmp/phase06a1-iteration1/ and policy/ |
| Final overview/queue/ready/review/blocked | tmp/phase06a1-after/{view}-{1440,1024,390}[-fold].png |
| Actual PRICE/overbilled recorded and5% preview | tmp/phase06a1-after/policy/ |
| Completed process map crops | tmp/phase06a1-after/signature/completed-trace-{1440,1024,390}.png |
| Controlled active state, visibly labelled | tmp/phase06a1-after/policy/TEST_ONLY-running-{1440,1024,390}.png |
| Actual Chrome interaction frames / recording | tmp/phase06a1-after/signature/frames.json and interaction.gif |

Iteration1 was visually inspected: attention card was still too tall, laptop orbit text crowded the ring,
and the case header remained too generous. Iteration2 tightened card geometry/case framing, corrected
orbit type scale, distinguished operation icons and retained the recorded status in the section rail.
Final screenshots were inspected for1440×1000,1024×900,390×844. Source and decision align; table rows remain
readable; mobile is decision-first; no horizontal overflow/overlap in checked states. Source-open fallback
works. The active screenshots are controlled TEST_ONLY API interception, never claimed as live inference.

Recording uses existing Chrome CDP Page.startScreencast/screencastFrameAck actual JPEG frames plus installed
Pillow for GIF encoding, not invented transition frames or new FFmpeg/Playwright. Recording metadata is
reported in signature/results.json. Final recording: 19 actual frames, 10.54s, 1080×750, 2043827 bytes. It covers overview hover, case navigation, keyboard trace disclosure,
and actual5% policy response. No fake progression. GIF is review evidence, not an embedded app dependency.
CDP reference: https://chromedevtools.github.io/devtools-protocol/tot/Page/ . Large assets stay ignored locally.

## Interaction, accessibility and design review

Hallmark app/redesign audit:0FAIL,0WARN,1WAIVED,3ANSWERED,15 rendered screenshots across three URLs.
The one retained REFLEX80 is an explicitly labelled real-count distribution chart, not a drawn illustration.
Existing answered items: restacked mobile table semantic header; mandated payment disclaimer punctuation;
execution-state markers. Spacing and closed-disclosure measurement findings were corrected, not ignored.

Vercel review against current official Web Interface Guidelines: semantic links/actions/forms/details,
keyboard skip/filter/search/row navigation, visible focus,44px main interaction targets, no covered focused
evidence, meaningful async announcements, anchors with scroll margins, responsive long values and no fake
progress. Reduced-motion checks disable actual connector/spinner/selection/result movement. Chrome AX tree
exposes heading/radio roles. This is focused browser/source QA, not a full screen-reader/WCAG certification.
Source: https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md .

Taste critique after implementation: repeated tiny cards removed from trace, financial comparison remains
sober, warm editorial case frame has stronger hierarchy, optional detail no longer competes with the reason.
Rejected marketing-only full-screen sections/photography/hero entrance/looping moments and universal one-card
geometry because finance repetition, live stage truth and evidence usability take priority. No claim of
visual quality based solely on lint; actual before/after screenshots informed both revisions.

## Exact checks and observed results

Commands run from repository root unless indicated:

| Command | Result |
|---|---|
| .venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06a1-final --tb=short |299 passed,52.90s; one existing Starlette/AnyIO deprecation warning |
| npm --prefix frontend test |48 passed in2 files, final5.72s; original47 plus disclosure-boundary regression |
| npm --prefix frontend run typecheck |PASS, exit0 |
| npm --prefix frontend run build |PASS, Vite7.3.8,1752modules,3.02s |
| .venv/Scripts/python scripts/verify_manifests.py |PASS:6vendors,7POs,3billed records,10cases; PO3015 remaining25000 |
| .venv/Scripts/python scripts/verify_git_hygiene.py |PASS:11exclusions;6fixturePDF bytes safe; no ignored files tracked |
| .venv/Scripts/python -m pip check |No broken requirements |
| npm --prefix frontend audit --audit-level=moderate |0 vulnerabilities |
| node frontend/scripts/qa.mjs |15real views +7controlled states; keyboard/PDF/reducedmotion/long values/unchanged snapshots;0JS errors |
| node frontend/scripts/policy-trace-qa.mjs |12recorded/preview states +3labelled controlled running states;6read-only previews; no uploads |
| node frontend/scripts/signature-qa.mjs |3viewport alignment/focus checks; actual CDP recording; unchanged snapshots;0uploads/JS errors |

Browser env: AP_COMPASS_UI_URL=http://127.0.0.1:8006;
AP_COMPASS_QA_DIR=tmp/phase06a1-after;
AP_COMPASS_POLICY_QA_DIR=tmp/phase06a1-after/policy.
Signature output defaults tmp/phase06a1-after/signature. Existing compiled FastAPI application served all
real API/PDF responses. No paid/public deployment. Normal tests used fake provider dependencies, no inference.

Hallmark exact invocation: HALLMARK_PUPPETEER points at frontend, then
node tmp/phase05-skills/hallmark/scripts/sloplint.mjs frontend/src/OperationsBento.tsx
frontend/src/DecisionTrace.tsx frontend/src/PolicyImpact.tsx frontend/src/Workspace.tsx frontend/src/styles.css
frontend/src/control-room.css frontend/src/signature.css frontend/src/tokens.css --scope app --genre modern-minimal
--render --url http://127.0.0.1:8006 --url http://127.0.0.1:8006/runs/d2269cade6cb4dca94e6239e5658d25a
--url http://127.0.0.1:8006/runs/3af82d60d6624971b7aa48de920407d5 .

Encountered failures, resolved: added anchor duplicated Policy impact text, so tests now target the actual
native summary rather than ambiguous text. Existing browser QA now opens the intentional audit disclosure
before its finding. Trace geometry assertion updated to the new vertical spine/two-part map. New focus test
initially used mouse modality; it now enters keyboard modality before checking focus-visible. Wrong working
directory in one formatting command corrected. Audit findings above resolved/documented. No business test
expectation was changed. No outstanding failed required check.

## Business invariants and no-model proof

**0 new Gemini calls.** Runtime guard still has one prior6A generation. No upload performed. All five
persisted snapshots and active policy deep-equal before/after browser previews. Authority SHA256 remains
7fb54a84f32bd0bf75a29396bb50c450878503dd70515b33bafcc330e2a54398.

PRICE_3PCT recorded2% REVIEW_REQUIRED/PRICE_VARIANCE; actual5% preview READY_FOR_AP. Overbilled actual and
5% preview BLOCKED/PO_BALANCE_EXCEEDED. Duplicate hard protection remains verified by unchanged full backend
regression. Scan arithmetic/evidence semantics unchanged. No frontend calculation of money, variance or
eligibility added; SVG ratios are counts for display only. All exceptions use supplied backend values.

Diff from95e6e66: no backend file, API client/types/query behavior, procurement/fixture manifest, PDF,
finance/document/AI/orchestration/DB/shared contract or dependency lockfile changes. No policy API semantics
changed. Mandatory payment/posting disclaimer retained verbatim. No architecture deviation.

## Bundle and remaining weaknesses

Baseline JS316.59kB/gzip99.34 →319.50/gzip100.13: +2.91/+0.79kB.
CSS61.08kB/gzip10.87 →70.59/gzip12.23: +9.51/+1.36kB.1751→1752modules. No new dependency or remote font/image.
No speed/FPS/Lighthouse performance claim; production build and actual browser interactions were verified.

Mobile cases with many evidence references still require vertical reading. Native PDF embedding can be
blank on mobile/headless Chrome; explicit source-open link remains. Original backend explanations contain
plain number strings and remain verbatim; the adjacent financial comparison carries formatted values.
CSS layers retain existing rules for compatibility; no large unrelated style rewrite was attempted.

## Files and handoff

Frontend/product: OperationsBento.tsx,Workspace.tsx,DecisionTrace.tsx,main.tsx,tokens.css,new signature.css.
Tests/QA: operations.test.tsx,policy-trace.test.tsx,scripts/qa.mjs,scripts/policy-trace-qa.mjs,
new scripts/signature-qa.mjs. Documentation: PHASE_06A1_DESIGN.md,this report,OPERATIONS_UI.md,
PROJECT_STATUS.md,memory.md. No unexpected/protected file.

The first four creative criteria are met in the rendered comparison: transformed attention composition,
aligned decision/source, readable signature process map and unmistakably hypothetical policy comparison.
Engineering gate passes. This is the submitted design judgment for user review, not self-authorization
for6B. No further unrelated visual repair, new business workflow or release work was performed.
