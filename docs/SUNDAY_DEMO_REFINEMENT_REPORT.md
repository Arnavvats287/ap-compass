# AP Compass Sunday demo refinement

## What changed

- Repeat-upload protection has a local checkpoint at `c373e0f`. Chrome exercised the real upload workflow on an isolated SQLite database using saved extraction replies. A renamed identical copy reused Northstar’s original Ready run, a byte-distinct copy of the same invoice got `ALREADY_SUBMITTED` and linked back to the original, and the separately billed Northstar fixture retained its `EXACT_DUPLICATE` Block.
- Workspace findings with a stored, independently verified page offer **Show source**. Source-located but unverified references offer **Inspect unverified source**. The action selects the matching evidence field, pauses its rotation, opens the referenced page in the original PDF viewer and briefly outlines the frame. Under reduced motion the page and field still change and the pulse is omitted.
- New unmatched-scope findings carry the existing verified item-code reference for each out-of-scope line. They retain their decision and owner. Historical records remain intact and use whatever references were originally stored.

## H02 replay

The unchanged `H02_REPEATED_ITEM_CODE.pdf` PDF matched its saved SHA-256. Replaying its saved extraction claims through the production verifier with no live provider calls reproduced **Review**, with **2 of 18** native-verified references, 15 source-located but unverified and one missing. Tax and gross independently verified. The two same-code item rows have distinct printed service periods. The stored description quotes overlap adjacent invoice metadata, and seller, invoice number, date, PO reference, currency and net evidence also remain unresolved. A narrow repeated-code rule would leave independent gaps, so the grounding policy remains strict and H02 stays in Review.

## Verification

- Focused backend suite passed **145 tests**, covering financial decisions, item-scope evidence, repeated uploads and layout grounding. The earlier repeat-upload checkpoint passed all **624 backend tests**.
- **83 frontend tests** passed. TypeScript and the production build passed. Prettier passed for the changed frontend files.
- Desktop Chrome at 1440px exercised the stored Kaveri surcharge and jumped directly to the verified line-two item code and PDF page one. At 390px, the source jump worked with reduced motion and without horizontal page overflow. The screenshots are local in `tmp/sunday-source-desktop.png` and `tmp/sunday-source-mobile.png`.
- The final Chrome batch accepted six files into five persisted runs. The same rehearsal opened Kaveri’s follow-up draft, showed Aster’s ₹5,000 overrun, confirmed five submissions in Overview, and downloaded an Excel workbook that reopened with five invoice-register rows.
- Zero new Gemini generations. The demo fixture database was disposable.

## Five-minute demonstration

Start with clean Northstar and reuse its existing run by uploading the renamed copy. Then open Kaveri’s Procurement finding and use **Show source** to reveal the ₹2,750 surcharge, followed by **Prepare follow-up**. Show Aster’s ₹5,000 overrun Block and the Overview and Excel export. Keep the Meridian scan and the Brightpath conflicting-payable case available as optional examples of safe Review.
