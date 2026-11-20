# Final financial dashboard polish

The changes build on release checkpoint `3a836ae3fb53a25ae1f72099e4b666374d00a09b`. Overview retains its existing financial cards and spotlight. Invoice Operations and Invoice Workspace retain their existing routes.

## Data definitions

- **Vendors needing attention.** Up to ten named vendors among the latest 100 submissions. The table counts original automated Review and Blocked outcomes, including repeated submissions. It sums known invoice gross by currency and reports missing gross or currency separately. It ranks by total attention count, then by gross within each comparable single-currency group. Ties within those groups use vendor identity and name. Mixed-currency and incomplete totals use name order when counts tie, after complete single-currency rows. The existing authority matcher groups a raw name with a canonical vendor only when the name resolves uniquely to an approved vendor. Other rows retain the recorded name. Drill-down links pass all recorded names represented by a row.
- **PO capacity.** Authorized PO net minus recorded prior billed net for each PO. Currency groups sort by remaining net descending. Capacity with incompatible billing currency displays an unavailable value. Analysis, Ready and human reassessment do not consume capacity. Closed POs retain their recorded status.
- **Common exceptions.** The five most frequent Review and Block finding codes from recorded decisions among the latest 100 submissions. Codes break count ties. A run can contribute several findings.
- **Existing financial cards.** All persisted runs. Known gross is aggregated independently by currency using exact decimal arithmetic. Missing data stays out of the monetary sums. Current reviewer assessments remain visible in the queue and workspace.

## Independent SQLite reconciliation

Chrome read the actual dashboard endpoint from a private localhost app using a disposable copy of the eight-invoice controlled rehearsal. A separate Python check used read-only SQLite and Decimal to compare all visible counts and amounts with the source snapshots and authority tables. The copied run, stage, review, supplier, PO, PO line and prior billing rows matched the original rehearsal rows exactly. No provider calls were made.

| Recorded outcome | Runs | Gross INR |
|---|---:|---:|
| Ready | 3 | 102,660.00 |
| Review | 3 | 71,685.00 |
| Blocked | 2 | 47,200.00 |
| Submitted | 8 | 221,545.00 |

All eight completed, with zero missing gross and zero technical failures. Review plus Blocked gross was INR 118,885.00. The existing flagged net total separately reconciled to INR 100,750.00.

| Vendor in rank order | Review | Blocked | Flagged gross INR |
|---|---:|---:|---:|
| Aster Systems | 0 | 1 | 41,300.00 |
| Brightpath Consulting | 1 | 0 | 26,845.00 |
| Kaveri Logistics | 1 | 0 | 23,600.00 |
| Meridian Cloud Pvt Ltd | 1 | 0 | 21,240.00 |
| Northstar Supplies | 0 | 1 | 5,900.00 |

| PO | Approved net INR | Prior billed net INR | Remaining net INR |
|---|---:|---:|---:|
| PO-1057 | 180,000 | 0 | 180,000 |
| PO-4002 | 100,000 | 0 | 100,000 |
| PO-1042 | 200,000 | 120,000 | 80,000 |
| PO-5001 | 80,000 | 0 | 80,000 |
| PO-6001 | 50,000 | 0 | 50,000 |
| PO-2010 | 30,000 | 5,000 | 25,000 |
| PO-3015 | 200,000 | 175,000 | 25,000 |

The rehearsal had nine Review or Block findings. The panel showed source evidence missing (3), exact duplicate (1), line mapping unresolved (1), PO balance exceeded (1), and PO line balance exceeded (1). Two more codes tied on one occurrence and fell outside the five displayed.

## Verification

- `python -m pytest backend/tests/test_dashboard_finance.py backend/tests/test_dashboard_projection.py backend/tests/test_excel_export.py backend/tests/test_review_api.py backend/tests/test_intake_policy.py backend/tests/test_orchestration_api.py` with local backend and workbook dependencies — 75 passed, one existing dependency deprecation warning.
- `npm --prefix frontend test` — 72 passed.
- `npm --prefix frontend run build` — TypeScript and production build passed.
- Chrome at 1440 and 390 px showed both tables without page or table overflow. A linked count opened the matching supplier and status in Invoice Operations. Overview returned identical data after navigation and refresh. Local screenshots are in `tmp/dashboard-polish/overview-1440.png` and `tmp/dashboard-polish/overview-390.png`.
- Tests exercised persisted human reassessment, canonical aliases and ambiguity, mixed currencies, failures without gross, repeated invoices, empty results, the latest-100 boundary, PO capacity, and database reopen.

The change is a read-only dashboard projection with no storage migration. Existing extraction, evaluation, invoice history, workbook definitions and procurement authority were preserved.
