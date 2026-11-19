# Phase 5 design QA record

Priority: business behavior > Hallmark redesign > Vercel interaction > Taste critique.

1. Actual app inspected in local Chrome using real Phase 4 persisted data, 1440px. The old shell screenshot
   was inspected before coding. Baseline Hallmark: 69 Floor findings / 39 Reflex / 4 warnings.
2. Main implementation rendered against the actual backend. First post-build Hallmark sweep: 4 Floor
   findings (768px header overflow, input edge contrast, opacity-only disabled state), 13 Finish warnings.
3. Vercel current command.md reviewed against code and live layout: retain native semantic controls/links,
   real statuses, keyboard focus, polite announcements, URL filters, no automatic financial retry. Found:
   retry hash navigation needed explicit scroll/focus; evidence disclosure needed an expansion affordance;
   invalid replacement file needed to clear stale selection. Fixed in the single review fix batch.
4. Taste Skill 2.5.1 loaded from upstream Leonxlnx/taste-skill/skills/taste-skill only after implementation.
   In-thread aesthetic critique: preserve the horizontal navigation, single stat strip, table-first hierarchy,
   restrained forest/neutral system and business brief rather than icon-card grids. Improve the PDF frame
   by hiding its cramped thumbnail chrome, make evidence disclosure clearer, keep scan discrepancy visible
   alongside the independent source-review finding. Maintain strong shared edges and modest radii.
5. Relevant fixes: header switches before overflow; darker search border; fill/ink/cursor disabled states;
   explicit disclosure indicators; retry focus/scroll; exact business values and required disclaimer retained.

Deliberately rejected Taste recommendations: hero entrance, one section per screen, shader grounds, mandatory
creative moments, looped card animation, photo zooms and marketing images. They conflict with the user's
operational workflow and reduced-motion/restraint requirements. No Taste marketing gate is claimed passed;
this is the requested aesthetic critique, not replacement by its landing-page starter.
Hallmark app scope excludes hero/fold/word-budget rules. No reviewer agents were needed or spawned.

Finish warnings: F25 measures clipped mobile table header coordinates; visible rows are deliberately restacked,
with every data cell retained and a real keyboard link. Confirm in the final 390px geometry/screenshots.
F1 concerns the user-supplied payment disclaimer; preserve it verbatim. Neither is a financial-semantic change.
Final sweep, exact browser checks and post-fix test/build counts will be recorded in PHASE_05_REPORT.md.


Final confirmation: five compiled real-data routes on Uvicorn8005, 0 FAIL / 0 REFLEX / 0 WARN / 3 ANSWERED,
25 Hallmark captures, exit0. A formatter-exposed heading-count accent was fixed by making the count a sibling
of the semantic heading; no business content removed. Final frontend32 tests, typecheck/build and Prettier check
pass. Actual browser15 real views/7 deterministic states, all required widths; reduced-motion/keyboard and
mobile cell bounds pass. One real upload/one primary call with unchanged ledger and successful reload.
A native-PDF popup harness stall was fixed/resumed on the same run, never another inference.
