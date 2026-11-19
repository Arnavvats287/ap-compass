# Private demo security

Local mode is for unauthenticated loopback development. Private mode requires backend Basic credentials and an exact browser origin. Startup rejects missing or invalid access settings before database initialization. Use a separate random credential for this demo, stored in ignored runtime configuration or a secret manager. Keep credentials out of browser URLs.

The HTTP gate covers the app, frontend assets, health, documents, previews, review actions, and unknown resources. Missing or invalid credentials at the configured origin receive the same 401 challenge. Host and ASGI scheme are checked before a challenge is issued. Writes and preview POSTs require the browser’s exact same-origin `Origin`. CLI POSTs must supply it. The application does not use client IP or forwarded headers as identity. The reviewer label remains unauthenticated attribution even after entering with the shared credential.

## Resource and recovery controls

- One event loop reserves each upload slot before consuming the multipart body. A slot stays occupied while reading, storing, queueing and processing an invoice. Capacity defaults to three and accepts one to eight. Excess requests return 429 without creating a file or run. Body reads time out after 30 seconds. The existing 8 MiB PDF limit and 64 KiB multipart allowance apply.
- One inference workflow runs at a time. Set `AP_COMPASS_UPLOADS_ENABLED=false` and restart to reject new uploads with 403 while retaining history, PDFs, previews and demo PO actions. Unfinished persisted work becomes Interrupted on restart.
- Each PDF uses an opaque ID. If creating the run transaction fails, the service removes only that request’s uncommitted PDF and returns a sanitized 503. Accepted persistence settles after a client disconnect. An abrupt process or machine termination between the file write and DB commit can still leave an orphan. Investigate against a stopped, backed-up store. There is no automatic sweep or deletion of records and PDFs.
- The service takes an OS advisory lock next to the SQLite file. A second application on the same path fails before reconciliation. Keep the lock file in place. Multiple workers, replicas, network filesystems and out-of-band writes are unsupported. Terminal decisions and review actions are retained.
- Provider work runs outside DB transactions. With demo escalation disabled, an ordinary transient failure can use one retry on the same primary provider, with the existing 250 ms delay and per-attempt timeout. Exhausted attempts remain technical failures without a financial decision. Any manual reattempt is a separate upload, with the first failed run retained.

## PDF and browser boundary

Saved PDFs are served by run ID through the same authentication gate. Responses use `application/pdf`, `nosniff`, `no-store`, a fixed inline filename, and same-origin framing through CSP `frame-ancestors` and `X-Frame-Options`. The workspace viewer and direct source link remain available. Framing restrictions do not replace browser PDF isolation and patching.

## Remote prerequisites and limits

Use private, single-instance, synthetic-data storage. Remote access requires HTTPS, a configured TLS gateway or direct Uvicorn TLS, and no alternative unprotected backend path. At a gateway, preserve the expected Host, overwrite forwarding headers, and restrict trusted forwarding to the actual gateway. Configure edge connection and time limits, a request-body limit compatible with 8 MiB plus the multipart allowance, auth-attempt and submission rate limits, and a monitored disk quota or capacity. Repeated authenticated submissions can exhaust quota or disk. The app does not enforce a daily generation budget, disk retention, or per-client request rates. For a prepared demo, leave uploads disabled and rotate the shared credential after use.

Neither mode provides production user or tenant isolation, maker-checker controls, PO reservations, payment approval, or posting.
