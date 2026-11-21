# H02 service-period extraction integration

## Local implementation

- Added a native-text parser for the explicit Service period / Item layout. It verifies two separately printed charges even when they share a SKU. It requires a valid service-period caption on each charge, distinct native cells for quantity, rate and net, and a recognized, ordered summary. Additional monetary content, incomplete rows and currency disagreement with the invoice fail the relevant source proof.
- Existing rectangular and stacked layouts retain precedence. Header evidence keeps its own verifier.
- The revised exact-cell prompt is scoped to independently recognized, complete service-period tables on single native-text PDFs. Other documents use the unchanged pre-existing system prompt.
- The canonical extraction schema, money arithmetic, PO authority, financial rules, historical decisions, and default single-attempt Flash-Lite model are preserved. Nothing was pushed or deployed.

## Offline replay on prior real PDFs

The same saved invoice facts and source claims were replayed through the original and integrated verifiers. Their decisions and every individual evidence state matched in all eight control cases. These cases also selected the byte-for-byte previous prompt under the final scoped configuration.

| Case | Original and integrated outcome | Native references |
| --- | --- | --- |
| Northstar Dispatch 071 | Ready | 13 |
| Northstar invoice + statement 082 | Ready | 13 |
| Brightpath 049 competing totals | Review | 10 |
| Northstar billed duplicate | Blocked | 13 |
| Kaveri unauthorized surcharge | Review | 13 |
| Meridian image-only scan | Review | 0 |
| Aster PO overrun | Blocked | 3 |
| Brightpath BP-26-7845 missing SKU | Review | 1 |

With H02's saved exact-cell reply, the integrated verifier raised independently verified references from 4/18 to 14/18. All ten line-item references verified. The four unresolved header facts, supplier, issue date, PO reference and invoice net, still require AP Review. Generated-PDF tests cover omitted and repeated charges, cross-row amounts and quotes, hidden monetary captions, unknown charges, denomination mismatch, and prompt selection.

## Live regression exploratory run

Seven fresh Flash-Lite attempts used isolated databases and the new prompt globally before the final prompt scoping decision. There were no retries. These observations are evidence against shipping the prompt globally.

| Case | Observed | What the run established |
| --- | --- | --- |
| Northstar statement 082 | Ready, 13/13 native | Correct current payable; no statement balance substitution |
| Aster overrun | Blocked, 3/13 native | All three hard overrun findings retained |
| Brightpath BP-26-7845 | Review, 1/15 native | Missed item code again and returned a different date from the oracle |
| Brightpath 049 | Review, 9/13 native | Conflicting total remained unresolved, but a net field dropped |
| Kaveri surcharge | HTTP 503 | No extraction or decision in this fresh attempt |
| Meridian scan | HTTP 503 | No extraction or decision in this fresh attempt |
| Northstar billed duplicate | HTTP 503 | No extraction or decision in this fresh attempt |

The final scoped runtime then processed H02 with one fresh Flash-Lite generation. It matched all 18 evaluated facts, proved 10/10 line-item fields and 14/18 overall, and retained AP Review in 4,721 ms. This was an API upload against untouched synthetic PDF bytes and isolated local storage. The trial made eight generation attempts in total. No Ready was observed among completed non-Ready targets.

Ignored receipts are in tmp/h02-strict-caption/live-regressions-184623 and tmp/h02-strict-caption/live-scoped-184824. The historical H02 comparison receipt is in tmp/h02-strict-caption/live-79cdaee4. These small synthetic tests establish the line-association improvement and preservation of the tested controls. They do not establish uniform provider availability or clear the four H02 header gaps.

## Test results

The final code passed 648 backend tests with one Starlette deprecation warning. The focused extraction subset passed 133 tests, and 16 separate tests using the original H02 PDF passed against the integrated producer. The earlier comparison receipts and original Git checkpoints were preserved.

## Decision preservation gate

Replayed the same PDF bytes and controlled extraction inputs against the pre-H02 verifier and the integrated verifier. The set covered all 12 Blind V2 cases, six held-out cases and eight demo invoices. Both sides used the same procurement authority and policy. The replay checked PDF hashes and the Blind V2 response seal. It made no Gemini calls and wrote no application records.

| Check | Result |
| --- | --- |
| Recorded verdicts reproduced by both verifier versions | 26/26 unchanged: 6 Ready, 16 Review, 4 Blocked |
| Previously correct cases against the external expectations | 20/20 retained their complete decisions, including findings and next actions |
| Complete decision and evidence equality | 25/26; only H02 changed |
| Invalid or review-target invoices incorrectly cleared | 0 in the evaluated set |
| Prompt choice | 25 used the byte-identical original prompt; only H02 used the service-period prompt |
| Original demo pack | 3 Ready, 3 Review, 2 Blocked before and after |

The first run asserted full decision equality for all 26 and flagged H02. Its evidence finding now names the remaining missing headers, because all ten line references verified. Its Review outcome and finding codes are unchanged. The corrected gate asserts unchanged outcomes for every case, full equality for every previously correct case, and the exact H02 evidence improvement from 4/18 to 14/18. It passed. Eight additional archived live extractions also passed their offline preservation checks. The six Ready-target cases still sent to Review are pre-existing gaps, including H02.

Replay commands from the launch worktree: `python tmp/h02-strict-caption/decision-preservation.py` and `python tmp/h02-strict-caption/verify-integrated.py` with the local backend and evaluation directories on PYTHONPATH. Per-case controlled results are in `tmp/h02-strict-caption/decision-preservation.json`. No runtime files changed in this gate. Retain the scoped improvement locally. The next bounded extraction opportunity, if needed, is independent verification of H02's supplier, issue date, purchase order reference and invoice net.

## Service-period header verification

A follow-up offline pass verified the four missing H02 fields with the existing native-text positions. The supplier resolves from a split issuer masthead beside a separately labelled buyer. The issue date and customer PO resolve from a bounded metadata column. Invoice net resolves from the single labelled net row of the already parsed charge summary. Unmatched claims and competing role labels are left unverified. No prompt, policy, or authority data changed.

| Case set | Before | After |
| --- | --- | --- |
| Original H02 PDF and saved Gemini extraction | Review, 14/18 native after line grounding | Ready, 18/18 native |
| 26 controlled cases compared with the pre-H02 verifier | 6 Ready, 16 Review, 4 Blocked | 7 Ready, 15 Review, 4 Blocked. H02 was the only change. |
| Previously oracle-correct decisions | 20 | All 20 complete decisions unchanged. The oracle match count increased to 21. |
| Eight previously saved live edge extractions | Archived decisions and evidence | Identical on offline replay |
| Original demo pack | 3 Ready, 3 Review, 2 Blocked | Identical |
| False Ready across the controlled suite | 0 | 0 |

The offline H02 decision retains PO identification and the bank-details advisory. The source-evidence finding is removed because its four remaining fields now verify. Five other controlled Ready targets still require Review. The tests cover wrong buyer, due-date, arbitrary PO and prior-balance claims, missing labels, competing labels and statement context. This pass made zero Gemini calls and changed no historical records. Results apply to the tested service-period layout and controlled inputs.

The focused band-layout suite passed 21 tests. The full backend suite passed 659 tests with one existing Starlette deprecation warning using a clean workspace test directory. The initial sandboxed attempt stalled in Windows asyncio loopback socket setup. The complete rerun used local test providers and temporary storage outside that network restriction. The frontend was outside this verification segment.

## Expanded replay of earlier invoices

Replayed the 26 controlled cases and inspected 61 earlier run receipts from the initial Blind 7, demo-library, model comparison and follow-up checkpoints. Of those receipts, 39 contained stored extraction facts from 12 distinct PDFs. The other 22 had technical failures and no usable extraction to replay. The archive contains multiple attempts on some PDFs. Both verifier versions received the same saved facts, source claims, invoice PDF and recorded policy on each replay.

- In the controlled set, Ready recall moved from 6 of 12 to 7 of 12. H02 was the only changed verdict. The other 25 complete decisions matched the pre-H02 version, and no non-Ready target became Ready.
- All 32 replayable, non-H02 archived decisions matched the pre-H02 verifier. The two Northstar layout samples and later Northstar Blind 7 and Orion responses still reach Ready, reproducing improvements from earlier grounding work.
- Two of seven archived H02 responses now reach Ready. They are distinct responses for the same PDF with separately supported charge rows. The other five still need Review with their older citations or facts.
- The five unresolved Ready targets in the controlled set are H01 (supplier), H03 (currency, totals and line evidence), V2-03 and V2-04 (line evidence) and V2-05 (two line associations). Brightpath BP-26-7845 also remained Review across saved model replies. In the original reply the item code was absent. The stronger reply extracted it without independently verifying it. The earliest Northstar Blind 7 reply still needs Review, while the later saved replies verify all 13 references.
- Real exception cases remain safe. The duplicate and PO overrun stayed Blocked, Kaveri's surcharge and the image-only scan stayed in Review, and the contradictory payable stayed in Review.

The replay made zero Gemini calls and edited no runtime code or stored invoices. Detailed offline results are in tmp/h02-strict-caption/expanded-controlled-replay.json and tmp/h02-strict-caption/expanded-archived-replay.json. The archive is a regression sample with repeated invoices and selection by saved receipts. It does not measure live extraction accuracy or provider availability.
