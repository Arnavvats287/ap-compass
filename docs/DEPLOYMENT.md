# Single-instance deployment

AP Compass supports loopback development and a private synthetic-data demo. The Docker image uses a Node 24 build stage and a Python 3.12 runtime. FastAPI serves the compiled frontend, including `/runs` and `/runs/<id>` after refresh. The runtime user is UID 10001. One Uvicorn worker owns a local SQLite database and its PDF directory.

## Local development

Use the [root README](../README.md) to build and launch on literal loopback with `AP_COMPASS_MODE=local`. When running Vite, bind both servers to loopback. Keep the unauthenticated development server off remote proxies and public networks.

## Private Docker demo

Create an ignored env file such as `tmp/private-demo.env` with `AP_COMPASS_MODE=private`, `AP_COMPASS_PRIVATE_ORIGIN=http://127.0.0.1:8000`, and values for `AP_COMPASS_PRIVATE_USERNAME` and `AP_COMPASS_PRIVATE_PASSWORD`. Generate a random password using a secret manager. ASCII letters, digits, dot, underscore and hyphen are accepted in the username. The password must have 24–128 printable ASCII characters without spaces. Omit the Gemini key and keep `AP_COMPASS_UPLOADS_ENABLED=false` for the prepared workflow. Enable uploads explicitly during controlled preparation. Keep `GEMINI_ESCALATION_ENABLED=false`.

```powershell
docker build -t ap-compass:private-demo .
docker volume create ap-compass-demo
docker run --rm --name ap-compass-demo --env-file tmp/private-demo.env -p 127.0.0.1:8000:8000 --mount type=volume,source=ap-compass-demo,target=/data ap-compass:private-demo
```

Visit the exact configured origin and authenticate at the browser challenge. Health is protected at `/api/health`. Use the same named volume when recreating the container. The volume must be writable to UID 10001. With default settings it holds both `ap-compass.db` and `documents/`. Stop the sole instance before a backup or move, and copy both together. Keep SQLite on a local filesystem with reliable OS file locks. Use disposable storage for verification.

For any remote use, terminate HTTPS on Uvicorn or behind a configured and trusted TLS gateway. If a gateway terminates TLS, it must set the ASGI scheme accurately through explicitly trusted proxy configuration. Keep the raw backend private, restrict ingress to the gateway, strip client-provided forwarded headers, and preserve the configured Host. The image disables proxy header interpretation by default. Treat remote routing as a separate acceptance check before use. See [Private demo security](PRIVATE_DEMO_SECURITY.md) for required edge controls and [the runbook](FIVE_MINUTE_DEMO_RUNBOOK.md) for controlled preparation.
