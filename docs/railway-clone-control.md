# Railway Clone Control API

This runbook describes how to clone a new Hermes service from an existing Railway
service (`virtuous-bravery`) using the control API.

## 1) Deploy the standalone controller service

Create a dedicated Railway service from this repo and set its start command to:

```bash
python -m controller.main
```

This controller service does not need Hermes messaging runtime tokens.

## 2) Required environment variables

Set these on the standalone controller service:

- `CONTROL_API_ENABLED=true`
- `CONTROL_API_TOKEN=<strong-secret>`
- `CONTROL_API_ALLOWED_IPS=<optional allowlist>`
- `RAILWAY_API_TOKEN=<railway-api-token>`
- `RAILWAY_SOURCE_SERVICE_ID=<source service id>`
- `RAILWAY_TARGET_PROJECT_ID=<optional override target project id>`
- `RAILWAY_TARGET_ENVIRONMENT_ID=<optional>` — if unset, the clone picks the
  project's *production* environment (or the first environment). Required
  inputs for Railway `serviceCreate` include `environmentId`; omitting it
  often surfaces as HTTP 400 / *Problem processing request*.
- `BOTFATHER_SVC_URL=<existing botfather-svc url>`
- `BOTFATHER_SVC_TOKEN=<existing botfather-svc token>`

If `RAILWAY_TARGET_PROJECT_ID` is omitted, the controller infers the project
from `RAILWAY_SOURCE_SERVICE_ID` and creates clones in the same Railway project.

## 3) Start a clone run

```bash
curl -X POST "https://<control-host>/api/control/clone" \
  -H "Authorization: Bearer $CONTROL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_name": "hermes-clone-01",
    "clone_mode": "fresh",
    "bot_display_name": "Hermes Clone 01",
    "idempotency_key": "clone-01-v1"
  }'
```

## 3.5) Operator UI

Open:

- `https://<control-host>/control`

This lightweight page lets you:

- provide `CONTROL_API_TOKEN`,
- submit clone requests,
- view recent run statuses/errors in real time.

Expected response:

```json
{
  "run_id": "clone_ab12cd34ef56",
  "status": "queued"
}
```

## 4) Poll clone status

```bash
curl "https://<control-host>/api/control/clone/<run_id>" \
  -H "Authorization: Bearer $CONTROL_API_TOKEN"
```

Typical statuses:

- `queued`
- `provisioning`
- `copying_variables`
- `telegram`
- `deploying`
- `healthy`
- `failed`

## 5) Fresh-state behavior

Default clone mode is `fresh`. On first boot, the container entrypoint removes
session and history DB artifacts (`state.db`, `response_store.db`, `sessions/*`)
before writing an idempotency marker.

For advanced recovery/testing, `clone_mode=stateful` can be used with an
optional `snapshot_url` field. When present, the clone receives
`HERMES_CLONE_SNAPSHOT_URL` and entrypoint restores that tarball once.

## 6) Failure recovery

- If status is `failed`, inspect `error` in status payload.
- If Telegram provisioning succeeded but deploy failed, revoke the created bot
  token manually from `botfather-svc` or BotFather.
- Retry with a new `idempotency_key` after fixing env/config issues.

## 7) Optional embedded fallback

If you intentionally want control routes inside `gateway/platforms/api_server.py`,
set:

- `CONTROL_API_ENABLED=true`
- `CONTROL_API_EMBEDDED=true`

Production recommendation remains the standalone controller service.

