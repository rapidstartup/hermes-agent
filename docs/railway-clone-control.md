# Railway Clone Control API

This runbook describes how to clone a new Hermes service from an existing Railway
service (`virtuous-bravery`) using the control API.

## 1) Required environment variables

Set these on the control-plane Hermes instance:

- `API_SERVER_ENABLED=true`
- `API_SERVER_HOST=0.0.0.0`
- `API_SERVER_PORT=${PORT}` (or leave unset to auto-fallback)
- `CONTROL_API_ENABLED=true`
- `CONTROL_API_TOKEN=<strong-secret>`
- `CONTROL_API_ALLOWED_IPS=<optional allowlist>`
- `RAILWAY_API_TOKEN=<railway-api-token>`
- `RAILWAY_SOURCE_SERVICE_ID=<source service id>`
- `RAILWAY_TARGET_PROJECT_ID=<target project id>`
- `BOTFATHER_SVC_URL=<existing botfather-svc url>`
- `BOTFATHER_SVC_TOKEN=<existing botfather-svc token>`

## 2) Start a clone run

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

## 2.5) Operator UI

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

## 3) Poll clone status

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

## 4) Fresh-state behavior

Default clone mode is `fresh`. On first boot, the container entrypoint removes
session and history DB artifacts (`state.db`, `response_store.db`, `sessions/*`)
before writing an idempotency marker.

For advanced recovery/testing, `clone_mode=stateful` can be used with an
optional `snapshot_url` field. When present, the clone receives
`HERMES_CLONE_SNAPSHOT_URL` and entrypoint restores that tarball once.

## 5) Failure recovery

- If status is `failed`, inspect `error` in status payload.
- If Telegram provisioning succeeded but deploy failed, revoke the created bot
  token manually from `botfather-svc` or BotFather.
- Retry with a new `idempotency_key` after fixing env/config issues.

