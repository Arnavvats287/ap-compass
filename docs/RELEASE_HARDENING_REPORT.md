# Phase 6B.2D.2 release hardening report

## Scope and implementation

The dedicated branch starts from `b06b34d01a07f6543bfe048d22627be115f37033`, tagged `phase-06b2d1-evidence-integrity`. This is a private, single-instance, synthetic-data demonstration checkpoint. No production schema, finance engine, extraction prompt, source evidence, policy preview semantics, or human PO confirmation semantics changed.

| Area | Files and changes |
|---|---|
| Access and request admission | `backend/app/api/private_access.py` adds fail-closed Basic auth, exact configured transport/Host, same-origin POSTs, no-store and browser headers. `backend/app/api/runs.py` reserves capacity before reading, bounds the envelope and body read, reports sanitized operational errors, and limits PDF framing to the same origin. |
| Run lifecycle and storage | `backend/app/main.py`, `backend/app/db/instance.py` and `backend/app/db/session.py` take and release a per-database OS lock around lifespan. `backend/app/orchestration/service.py` tracks admitted work, settles file/row creation before acknowledgement, and releases capacity on completion. `backend/app/orchestration/documents.py` compensates for failed DB creation using only the corresponding uncommitted opaque ID. |
| Browser and demonstration | `frontend/src/components.tsx` explains disabled uploads, upload timeout and full capacity. `frontend/src/Workspace.tsx` labels controlled runs. `scripts/private_demo.py` loads four hash-locked synthetic fixtures via an explicit offline harness. `frontend/scripts/private-demo-qa.mjs` checks private Chrome workflows and durable restart fingerprints. |
| Deployment and handoff | `Dockerfile`, `.dockerignore` and `.env.example` set private defaults, one worker, persistent PDF and DB paths, and backend-only runtime secret configuration. `README.md`, `docs/DEPLOYMENT.md`, `docs/PRIVATE_DEMO_SECURITY.md`, `docs/FIVE_MINUTE_DEMO_RUNBOOK.md`, this report, `PROJECT_STATUS.md` and `memory.md` describe the current operating modes and evidence. |

## Actual verification

| Command or action | Result |
|---|---|
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests -q --basetemp tmp/pytest06b2d2-final --tb=short` | 488 passed in 127.35 s, including 17 new private-demo tests. No failures, skips or XFAILs. Existing Starlette/AnyIO deprecation warning. |
| `.venv/Scripts/python -m pytest -c backend/pytest.ini backend/tests/test_private_demo.py -q --basetemp tmp/pytest06b2d2-focused --tb=short` | 17 passed in 8.31 s. |
| `npm --prefix frontend test` | 58 passed across 3 files. |
| `npm --prefix frontend run typecheck` and `npm --prefix frontend run build` | Passed. Vite transformed 1,754 modules. |
| `.venv/Scripts/python scripts/verify_manifests.py` and `.venv/Scripts/python scripts/verify_git_hygiene.py` | Passed. Six vendors, seven POs, three billed records, ten original scenarios, 11 exclusion checks and ten Git-byte-verified PDFs. |
| `.venv/Scripts/python -m pip check`, `npm --prefix frontend ls --depth=0`, `npm --prefix frontend audit --audit-level=high` | Dependency checks passed. npm reported zero vulnerabilities. |
| `docker build -t ap-compass:private-demo .` | Passed using Docker Desktop Linux engine 29.9.2. Node production build and Python runtime install succeeded. |
| `docker run` with loopback-published port and isolated volume | Private startup failed as expected without settings. Configured health and compiled frontend worked under UID 10001. A separate Uvicorn process attempting the same database was rejected. One Uvicorn worker was observed. Private credential and Gemini-key environment entries were absent from the built image. Container pip check passed. |
| `.venv/Scripts/python scripts/private_demo.py --env-file <ignored-private-env>` | Four ordered uploads accepted and persisted in each of two disposable Docker volumes. Real parser, source grounding and finance ran with `TEST_ONLY-controlled-demo` wire claims. |
| `node frontend/scripts/private-demo-qa.mjs <ignored-private-env> <ignored-output>` | Chrome saw the unauthenticated challenge. Authenticated shell, API and same-origin PDF frame succeeded. The rendered source was visible during human reassessment. Deep-link reload worked. PO action saved and original snapshot remained identical. The 5% policy preview showed Ready with recorded Review unchanged. |
| Container recreation followed by `node frontend/scripts/private-demo-qa.mjs <ignored-private-env> <ignored-output> --restart` | Passed using the normal image entry point and no harness mounts. Four run snapshots, four original PDF hashes and the saved review-history hash matched exactly. Authenticated health succeeded and new uploads returned 403. |
| `node frontend/scripts/qa.mjs` | Passed against the loopback local-mode container. 15 persisted views, 7 intercepted diagnostic states, visible keyboard focus, PDF access, reduced motion, zero mutations and no uncaught JavaScript errors. |

The new tests verified 401 responses on shell, API and PDF requests, indistinguishable unauthorized responses for existing and unknown record IDs, incorrect Host/transport/Origin rejection, missing private settings, and the upload-off switch. Seven concurrent submissions with capacity two produced two accepted runs and five 429s. One extractor remained active. A slow upload body held the only slot while a rejected request consumed no body and created no PDF or row. During slow extraction, history reads continued and competing PO confirmations produced one 201 and one 409. Forced stage insertion failure rolled back the run and removed only the new PDF. Existing runs and their documents remained unchanged. SQLite uses the existing configuration. No WAL change was needed for the tested contention.

Controlled SDK HTTP 503 and 504 errors and a connection failure each yielded two submissions to the same provider interface, then `PROCESSING_FAILED / PROVIDER_UNAVAILABLE` with no financial decision and remaining stages skipped. The first run kept its original PDF and terminal state after restart. The existing reconciliation tests cover queued and running interruption without replay. Provider prompts, classification, retry limits and escalation logic are unchanged. The demonstrated profile disables escalation.

## Demonstration observations

| Synthetic PDF | Recorded outcome | Business evidence verified in the workflow |
|---|---|---|
| HAPPY_CLEAN | Ready | Source-supported native facts and persisted original PDF. |
| OVERBILLED_PARTIAL | Blocked | PO-3015 had ₹25,000 net remaining against ₹30,000 requested; commitment and quantity findings fired. |
| MISSING_PO_VALID | Needs review | Browser confirmation of PO-1042 produced a separate Ready reassessment. Original decision remained Review and the audit entry survived container recreation. |
| PRICE_3PCT | Needs review at 2% | Browser 5% preview showed Ready from stored facts while the recorded outcome stayed Review. |

The runs and browser evidence were produced in disposable volumes. Existing demo histories were untouched. Live requests to Gemini in this phase **0**. A controlled-model invocation counter refers to calls to the fixture provider. No token fields were fabricated. No remote/public deployment, live provider availability check, TLS gateway test or production actor authentication was performed.

## Frozen-source and authority verification

The ten published first and post-fix JSON result files were compared byte-for-byte to the base commit. Their published digests are in the [historical validation report](PHASE_06B2C4_POSTFIX_VALIDATION.md) and [historical comparison](POSTFIX_V1_OFFLINE_COMPARISON.md). Golden oracles, fixture assets and protected production paths had zero Git diff. LF-normalized procurement seed SHA-256 was `66be24c67f8869e05b997273659fd9ba59d23000ea08a0ed17afda520bffcbed`. The typed runtime authority fingerprint after Docker upload, confirmation and restart was `f6e95512f3e71d59bf512c1afc861e69587c3bbf40a9400c0f6c04739d02bf31`, equal to the published fingerprint. Isolated concurrent tests also compared runtime authority before and after processing and review. No benchmark inference was rerun.

## Operating limitations

This checkout has a verified loopback Docker path. Remote use remains conditional on actual TLS and gateway configuration, edge request and authentication rate limits, disk monitoring and no bypass path to the backend. A shared credential limits app entry; review attribution remains a demo label. Upload capacity limits in-flight work and is independent of disk retention or daily provider quota. Filesystem and SQLite writes cannot share a transaction across abrupt machine termination. The PDF headers regulate framing; browser PDF isolation is still required. Provider outages can still happen. Ready confers no PO reservation or payment/posting authority.

**PRIVATE DEMO HARDENING PASS — READY FOR CONTROLLED DEMONSTRATION.**
