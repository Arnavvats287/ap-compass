# Phase 6B.2F.3 — Final demo experience

Base `f6fb08b7fe0bd5d04e6749c8e7f914faf0f8097d`. Branch `codex/phase-06b2f3-final-demo`. The F.1 and F.2 worktrees, checkpoints, prior captures and original demo data were preserved.

## Decision journey

The invoice workspace links directly to the five vertically connected persisted stage cards and the recorded result. A stage opens with its measured duration or timestamp difference, its purpose and relevant source, procurement or control details. The Ready end uses a drawn ring and check. Review raises an attention mark and shows the recorded issue, owner and action. Blocked settles a stop emblem above the persisted financial comparison. Technical failure uses a neutral stop reveal and states that no AP decision was produced.

When a historical journey first enters the viewport, the presentation traces its completed rail segments. **Replay journey** restarts the decorative rail and ending without changing timing text, stages, findings or opened disclosures. The first ending reveal is triggered when its icon comes into view. During active execution, the active segment comes from the backend's `RUNNING` state and future stages keep their backend waiting states. The interface displays no progress percentage or estimated completion time.

The animation uses CSS and one viewport observer watching the rail and result icon, with no new animation dependency. Native disclosures support keyboard and touch, controls retain visible focus, and reduced motion disables journey animations. The main workspace still shows the recorded invoice, original versus reviewed assessment where applicable, evidence, policy preview and PO review.

## Financial overview

An additive read-only field on `GET /api/dashboard` uses stored invoice totals including tax, aggregated exactly with Decimal. Each currency has its own total. The submitted card includes all stored submissions with a known gross and currency, including duplicates and repeat submissions. Each outcome card uses the original automated decision. Technical failures and in-progress submissions have no business outcome. Missing values and currencies are counted and excluded from the relevant sums. The overview retains the original counts, Needs Attention and flagged-net projection.

| Rehearsal metric | Runs | Gross |
| --- | ---: | ---: |
| Total submitted | 8 | INR 221,545 |
| Ready | 2 | INR 55,460 |
| Review | 4 | INR 118,885 |
| Blocked | 2 | INR 47,200 |

These totals were asserted from the saved eight-case database and checked in Chrome. A separate technical-only database showed eight exclusions from submitted gross and no financial outcome values. Backend tests verify distinct currencies, exact decimal precision, missing totals, and the existing flagged-net calculation.

## Rehearsal and verification

| Case | Recorded result |
| --- | --- |
| 01 Meridian hosting | Ready |
| 02 Kaveri freight | AP Review, tax evidence unverified |
| 03 Orion supplies | Ready |
| 04 Meridian support | AP Review, no printed PO |
| 05 Brightpath rush fee | AP Review, unresolved source and line mapping |
| 06 Kaveri scan | AP Review, image-only evidence |
| 07 Aster overrun | Procurement Block, INR 10,000 net and two units above remaining authorization |
| 08 Northstar | AP Block, exact duplicate |

The read-only Chrome check used copied persisted rehearsal records and a separate copy of a real technical failure from the earlier rehearsal adapter setup. At 1440 and 390 px, it checked all four endings, stage disclosure, replay, keyboard focus, reduced motion, and page overflow. It compared snapshots before and after and made no write requests. A separate live check used a TEST_ONLY gate at the provider boundary to observe a genuine persisted Running extraction. It verified one animated segment, three waiting stages, no preterminal outcome, and the recorded Ready result after release.

The eight PDFs were also selected and submitted again through Chrome in a fresh disposable F.3 upload store. The original admission and parser paths returned eight serial 202 responses and the same 2 Ready, 4 Review and 2 Blocked outcomes. Each PDF hash matched on retrieval. The browser's downloaded Excel export matched all eight invoice rows, 26 findings, and eight evidence rows.

| Verification | Result |
| --- | --- |
| `npm --prefix frontend test` | 69 passed in 4 files |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed, 1,763 modules |
| `python -m pytest -q -c backend/pytest.ini backend/tests/test_financial_overview.py backend/tests/test_excel_export.py --basetemp tmp/f3-pytest` | 4 passed, one existing AnyIO deprecation warning |
| `node frontend/scripts/final-demo-qa.mjs tmp/f3-rehearsal/private.env tmp/f3-technical/private.env tmp/f3-visual` | Passed four endings, keyboard, replay, reduced motion, gross totals and immutable snapshots |
| F.3 batch on `8026` and live journey on `8028` | Passed with controlled TEST_ONLY extraction |
| `python scripts/verify_manifests.py`, `python scripts/verify_git_hygiene.py`, `git diff --check` | Passed |

Local screenshots are in ignored directories. `tmp/f3-visual/` contains `overview-1440.png`, `overview-390.png`, `financial-1440.png`, `financial-390.png`, and desktop/mobile captures for `ready-journey`, `review-journey`, `blocked-journey`, and `stopped-journey`. The live-state check exposed light text inherited from the dark processing panel. The inner journey now uses its own dark text token. The final live capture is `tmp/f3-live-final/live-journey.png`. The batch screenshots and downloaded workbook are in `tmp/f3-upload/`.

## Exact local launch

Use PowerShell from the F.3 worktree root. The launcher and input files below are ignored, local copies of the verified rehearsal materials. The original F.2 directories are separate. Use the workspace Python environment and install `backend/requirements.txt` if the shared dependencies are unavailable.

```powershell
$python = (Resolve-Path '../../.venv/Scripts/python.exe').Path
$backend = (Resolve-Path backend).Path
$exportDeps = Resolve-Path '../phase06b2f2-ui/tmp/f2-deps' -ErrorAction SilentlyContinue
$env:PYTHONPATH = if ($exportDeps) { "$backend;$($exportDeps.Path)" } else { $backend }
npm --prefix frontend run build
& $python tmp/f3-rehearsal/run_demo.py preview
```

If the verified preview is already running, open `http://127.0.0.1:8024/` without starting a second process. Sign in using the ignored `tmp/f3-rehearsal/private.env`. That copy has all eight records and uploads disabled.

The verified presentation uploader is at `http://127.0.0.1:8030/runs/upload`. Its credentials and invoice files are in `tmp/f3-presentation/`. To recreate an empty uploader when that port is free, run the following in a second PowerShell after setting the same Python paths.

```powershell
$fresh = New-Item -ItemType Directory -Path ('tmp/f3-present-' + [guid]::NewGuid().ToString('N'))
Copy-Item -LiteralPath 'tmp/f3-upload/sealed-wire.json','tmp/f3-upload/invoices' -Destination $fresh.FullName -Recurse
(Get-Content 'tmp/f3-upload/run_demo.py' -Raw).Replace('8026', '8030') |
  Set-Content -Encoding utf8 (Join-Path $fresh.FullName 'run_demo.py')
& $python (Join-Path $fresh.FullName 'run_demo.py') present
```

Open `http://127.0.0.1:8030/runs/upload` with the new folder's `private.env`. Select the eight PDFs from its `invoices/` folder. The provider recognizes only these sealed input hashes and is visibly marked **TEST_ONLY** in the workspace and workbook.

## Limits and boundary

Replay is a brief presentation of persisted history and does not reproduce processing speed. The tested sample is a controlled synthetic rehearsal. It establishes browser, storage, verifier, and financial workflow behavior for these inputs. No live Gemini extraction, physical-device testing, or Excel desktop execution was part of this verification. The demo script uses the saved decisions and includes no unrecorded human confirmation.

The only backend behavior change is the additive dashboard read projection. Finance, procurement, evidence, provider, admission, private access, frozen evaluations and port 8005 were untouched. **Zero Gemini calls.** No push, deployment, or further feature development.
