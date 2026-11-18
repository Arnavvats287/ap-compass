# Submission and live-demo checklist

**Target deadline:** Saturday 2026-11-21 IST. **Preferred feature freeze:** Friday evening 2026-11-20. Actual hiring coordinator instructions and any individual deadline take precedence.

## Build readiness — do not claim success without evidence

- [ ] New real native PDF → actual Gemini/PDF extraction → deterministic decision → saved run.
- [ ] Scanned/uncertain input fails safely or returns review with honest evidence state.
- [ ] Unique vendor/PO and partial invoice are correctly reconciled against net remaining commitment and quantities.
- [ ] Exact billed duplicate and over-commitment are blocked. A known technical failure is not a financial decision.
- [ ] All stage progress is actual persisted execution data. Run history survives refresh/restart on deployed storage.
- [ ] At least two distinct nontrivial edge case PDFs pass from upload through UI.
- [ ] Main run workspace tells a nontechnical AP manager: what, why, amount affected, next owner/action, and supporting source.
- [ ] Every dashboard aggregate derives from real persisted synthetic runs, not hardcoded illustrative values.
- [ ] Upload type/size/page limits and prompt injection regression are tested. Logs/build don't expose keys.
- [ ] Core unit/integration/e2e commands and actual outcomes captured.
- [ ] Frozen fixture evaluation report includes sample count, confusion matrix/false-ready count and limitations, not fabricated ROI.

## Demo and external access

- [ ] External browser can open live URL without developer environment setup.
- [ ] Test clean invoice in hosted build using a previously unprocessed file; see genuine new stages.
- [ ] Test one high-value exception live; inspect invoice/PO evidence, explain why not ready.
- [ ] Test history and document viewer after reload. Downloadable sample PDFs work.
- [ ] Demo can be replayed without altering the prior billed ledger or PO balances.
- [ ] Screen recording is at most five minutes, shows real execution, one edge case, and a coherent buyer-focused narrative; no slides needed.
- [ ] Hosting service stays available during review; deploy exact tested Git commit; no rushed redeploy immediately beforehand.
- [ ] Submit both **live runnable link** and **demo video link** to hiring coordinator; save confirmation.

## Contingency

If behind schedule: skip policy UI, additional analytics, extra fancy scan highlights, novel optional cases and human confirmation. Never sacrifice the real PDF→decision path, correct financial controls, real execution history, a usable UI, two meaningful scenarios, or accessible submission links.
