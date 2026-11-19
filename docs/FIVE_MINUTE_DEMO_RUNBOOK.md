# Five-minute AP Compass demonstration

Use trusted persisted runs where the recorded provenance meets the demo needs. For a self-contained offline walkthrough, prepare the four frozen synthetic PDFs in a fresh disposable store with the controlled harness below. The browser labels these runs **Controlled extraction (TEST_ONLY)**. The harness supplies typed, source-matched claims to the same extraction adapter. Actual parsing, grounding, finance checks, workflow stages and persistence still run. No external Gemini generation or provider token usage is implied.

## Prepare once and rehearse

1. Build the image and create an ignored runtime env file as described in [Deployment](DEPLOYMENT.md). Use the loopback origin shown there. For this step, set `AP_COMPASS_UPLOADS_ENABLED=true`. Omit provider credentials. Give each presenter a new disposable volume for any walkthrough that will save a PO action.
2. Start the explicitly controlled Docker app. The host mounts are for controlled preparation only. Their files are omitted from the normal runtime image.

```powershell
$demoRoot = (Resolve-Path .).Path
docker volume create ap-compass-demo
$demoArgs = @(
  'run', '-d', '--name', 'ap-compass-prep', '--env-file', 'tmp/private-demo.env',
  '-p', '127.0.0.1:8000:8000',
  '--mount', 'type=volume,source=ap-compass-demo,target=/data',
  '--mount', "type=bind,source=$demoRoot/scripts/private_demo.py,target=/demo/scripts/private_demo.py,readonly",
  '--mount', "type=bind,source=$demoRoot/evaluation,target=/demo/evaluation,readonly",
  '--mount', "type=bind,source=$demoRoot/data/golden_dataset_v1.json,target=/demo/data/golden_dataset_v1.json,readonly",
  '--mount', "type=bind,source=$demoRoot/tests/fixtures,target=/demo/tests/fixtures,readonly",
  'ap-compass:private-demo', 'uvicorn', '--app-dir', '/demo/scripts', 'private_demo:create_demo',
  '--factory', '--host', '0.0.0.0', '--port', '8000', '--workers', '1', '--no-proxy-headers'
)
docker @demoArgs
```

3. Once startup completes, prepare the four runs from the host. The script verifies the controlled harness and all four fixture hashes. It refuses to seed a store that already has runs. It prints run links’ IDs and outcomes. Save them locally.

```powershell
$env:PYTHONPATH = 'backend'
.venv/Scripts/python scripts/private_demo.py --env-file tmp/private-demo.env
docker stop ap-compass-prep
```

4. Change the ignored env file to `AP_COMPASS_UPLOADS_ENABLED=false` and start the normal private image using [Deployment](DEPLOYMENT.md) with the same volume. Log in to the browser and confirm all four run links open with their source PDF. A saved PO confirmation is permanent. To rehearse the write and still show it live, prepare a separate disposable presentation volume. Keep the policy preview and source tabs ready.
5. For local, automated Chrome QA on a fresh prepared volume, run `node frontend/scripts/private-demo-qa.mjs tmp/private-demo.env tmp/private-demo-qa`. This check saves a real demo review action, so use rehearsal storage.

## Presentation script

| Time | Show | Say |
|---|---|---|
| 0:00–0:50 | Overview and `HAPPY_CLEAN` | “AP Compass helps an analyst triage invoices. Extraction proposes invoice facts. Source checks and deterministic procurement controls produce the recorded result. This prepared run uses controlled extraction. The checked evidence, trace and decision are persisted.” |
| 0:50–2:00 | `OVERBILLED_PARTIAL` | “The invoice requests ₹30,000 net against ₹25,000 remaining on PO-3015, and its quantity also exceeds what remains. The invoice is blocked and routed to Procurement. The source PDF and control findings explain why.” |
| 2:00–3:20 | `MISSING_PO_VALID` | “This invoice references no PO. I’ll confirm PO-1042 as the intended order and record my rationale. The app retains the original Review and shows the separately audited Ready reassessment. This demo label is unauthenticated. The action resolves PO identity only.” |
| 3:20–4:20 | `PRICE_3PCT`, Policy impact | “The recorded decision remains Review at 2%. At 5%, the deterministic preview is Ready on these stored facts. Previewing leaves the original decision and active policy untouched. It makes no model request.” |
| 4:20–5:00 | Return to queue | “A provider outage yields a technical failure with no financial decision. Unsupported evidence can also require review when processing completes. Ready means supported controls passed. Funds aren’t reserved and AP Compass doesn’t approve payment or post to an ERP.” |

If a genuine live upload is separately attempted during a presentation, label it live. Show the actual result, including a technical failure. Resume the prepared walkthrough on an outage. This synthetic evaluation did not establish straight-through reliability for arbitrary supplier PDFs.
