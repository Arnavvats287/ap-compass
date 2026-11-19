# AP Compass — Five-minute interview demo

## Before recording

- Open the private dashboard on port 8024 using the saved eight-invoice rehearsal. Open the batch page on the separate fresh presentation instance on port 8030. Use the local credentials from each instance's ignored `private.env`.
- Open the `tmp/f3-presentation/invoices/` folder in the file picker. Keep the fresh upload store separate from the eight records used for dashboard totals.
- Open the Ready Meridian invoice (01) and the Aster overrun (07) in separate tabs. Keep the Northstar duplicate (08) or the image-only freight scan (06) as the final exception example.
- The rehearsal supplies source-backed extraction replies labeled **TEST_ONLY**. The PDF verifier, procurement checks, records, and workbook are the actual application. The controlled rehearsal does not measure live Gemini performance.

## Spoken script and cues

| Time | On screen | Spoken |
| --- | --- | --- |
| 0:00–0:40 | Operations overview, then Financial overview | “AP Compass gives an accounts payable analyst one place to inspect invoice decisions before payment or posting. This saved rehearsal has eight invoices and ₹2,21,545 in submitted gross, including tax. Two Ready invoices total ₹55,460 gross. Four need review and two are blocked. The submitted figure includes repeat submissions and duplicates. The spotlight puts a concrete issue, its owner, and the next action in front of the analyst.” |
| 0:40–1:20 | Fresh upload instance. Select the pack, choose **Process selected invoices**, and watch individual statuses. | “I can submit several PDFs together. The browser processes them one at a time, and each file keeps its own record. For this rehearsal I’m using controlled TEST_ONLY extraction from these synthetic PDFs. The application still verifies the source and applies its own financial controls. Each row updates as its real execution state changes.” |
| 1:20–2:00 | Meridian invoice 01. Open **Decision journey**, expand **Reading invoice**, then click **Replay journey**. | “This Meridian invoice passed the supported two-way checks. I can expand a stage to see the stored timings and source context. This invoice has thirteen native-verified references. Replay illustrates the recorded execution. The result and evidence stay available throughout.” |
| 2:00–3:05 | Aster invoice 07. Point to source PDF, the blocking finding, owner, and comparison. | “Here the supplier requests seven units and ₹35,000 net. The PO has five units and ₹25,000 net remaining. That puts the invoice two units and ₹10,000 above the remaining authorization. AP Compass blocks it, shows the commitment and quantity findings, and assigns Procurement the next step. I can still open the original PDF.” |
| 3:05–3:50 | Northstar 08, or Kaveri scan 06 | “Northstar matches an existing billed record and is blocked as an exact duplicate. AP owns the follow-up.” **Scan alternative:** “The Kaveri scan stays in AP review. We can inspect the image, but none of the thirteen references is independently native-verified.” |
| 3:50–4:35 | Invoice Operations → **Export Excel** | “The register exports the latest 100 stored submissions across all filters. It keeps the original decision, any reviewed decision, and execution state separate. The workbook also carries the recorded findings and source verification counts.” |
| 4:35–5:00 | Return to the dashboard | “This makes the first AP review easier. Analysts can see what passed the supported checks, what needs evidence, and who owns an exception. Ready means the invoice passed these checks. Payment, posting, and approval remain separate decisions.” |

Use the saved records if the batch is still processing at the cue change. Show actual terminal states once they appear. Invoice 02 is Review because the tax evidence remains unverified. Invoice 05 is Review with AP ownership, even though the intended routing was Procurement. Invoice 04 has a missing printed PO and two candidates, with PO-1057 ranked first. This script does not show a human confirmation.
