# Phase 5 design direction — before implementation

Redesign of the existing AP Compass application, not a greenfield landing page.
Base inspected: 13fe35d792c2fb47a84604e21966ad4a2bd2048b. Existing screenshot inspected at 1440px.
Hallmark v2.0.0 installed from Nutlope/hallmark/skills/hallmark into ignored tmp/phase05-skills.
Baseline rendered audit: 69 Floor findings, 39 Reflex findings, 4 warnings. No fabricated audit pass.

Audience: AP analyst/manager. Material: real persisted run summaries, decisions, findings, source PDFs,
stages and evidence; existing forest-green identity and Lucide compass. No invented proof, imagery or figures.
The old shell's identity and no-payment boundary stay. Phase badges, Foundation status, disabled upload and
future-tense claims are explicitly retired by the Phase 5 request.

Visual system: warm off-white canvas, white work surfaces, charcoal/forest navigation, slate body text,
restrained semantic green/amber/red/blue. One system sans family with deliberate weight/size hierarchy,
tabular figures, 4px spacing rhythm, modest 4–8px radii, hairline boundaries and little shadow.
Use a compact horizontal shell for only two destinations; no marketing hero or ornamental sidebar.
One token file owns palette, fonts, scale, spacing, radii, shadows and motion. One primary button style.

Signature: a source-and-decision workbench. The first screen prioritizes the business finding, relevant exact
financial values, resolution owner and recommended next step; the persisted PDF remains beside it on desktop.
Overview uses a metric strip, restrained outcome distribution and attention queue. Queue uses a semantic table
with URL-backed filters/search. Mobile stacks decision/action/findings/evidence before the source document.

Scope/files: replace frontend/src/main.tsx and styles.css; create tokens/base, App/routes, typed API/types,
query hooks, display utilities, shared components, overview/queue/workspace views and focused tests.
Keep the product's navigation intent, brand and source/data wiring; replace obsolete placeholder logic.
No files deleted. Backend changes limited to the explicitly approved optional dashboard projection, if useful.

Interaction: 44px targets, instant visible focus, links for navigation/buttons for actions, stable skeletons,
inline errors, meaningful polite async announcements, no fake percentages/stages, no auto-retry of uploads.
Motion only for real busy states/hover, disabled under reduced motion. Native evidence and scan uncertainty
stay distinct. Financial values are formatted from decimal strings without Number-based money calculations.

Hierarchy of authority: product/financial requirements > Hallmark app/redesign system > Vercel interaction QA
> post-implementation Taste critique. Hallmark app scope explicitly excludes hero/fold/word-budget/photo rules.
Skill requests for unnecessary review agents or confirmation do not override the authorized bounded workflow.
Review remains in-thread; three views, no delegated agents. No marketing or gratuitous motion recommendations.

QA plan: real backend + local Chrome screenshots at 1440/1024/390; Hallmark sweep, Vercel audit, then Taste;
fix relevant findings, rerun tests/build, inspect keyboard/reduced motion and all outcome/empty/error states.
Screenshots and skill artifacts stay ignored. Record actual outcomes in PHASE_05_REPORT.md.
