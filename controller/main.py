"""Standalone control-plane web app for Railway clone automation."""

from __future__ import annotations

import ipaddress
import logging
import os
from typing import Optional

from aiohttp import web

from gateway.provisioning.railway_clone import CloneRequest, CloneRunStore, RailwayCloneOrchestrator

logger = logging.getLogger(__name__)


def _control_enabled() -> bool:
    return str(os.getenv("CONTROL_API_ENABLED", "true")).lower() in ("1", "true", "yes", "on")


def _control_token() -> str:
    return os.getenv("CONTROL_API_TOKEN", "").strip()


def _allowed_ip_ranges() -> tuple[str, ...]:
    return tuple(part.strip() for part in os.getenv("CONTROL_API_ALLOWED_IPS", "").split(",") if part.strip())


def _ip_allowed(request: web.Request) -> bool:
    allowed = _allowed_ip_ranges()
    if not allowed:
        return True
    remote = request.remote
    if not remote:
        return False
    try:
        remote_ip = ipaddress.ip_address(remote)
    except ValueError:
        return False
    for token in allowed:
        try:
            if "/" in token:
                if remote_ip in ipaddress.ip_network(token, strict=False):
                    return True
            elif remote_ip == ipaddress.ip_address(token):
                return True
        except ValueError:
            continue
    return False


def _check_auth(request: web.Request) -> Optional[web.Response]:
    if not _control_enabled():
        return web.json_response({"error": "Control API is disabled"}, status=404)
    token = _control_token()
    if not token:
        return web.json_response({"error": "CONTROL_API_TOKEN is not configured"}, status=500)
    if not _ip_allowed(request):
        return web.json_response({"error": "Source IP not allowed"}, status=403)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return web.json_response({"error": "Unauthorized"}, status=401)
    presented = auth[7:].strip()
    if presented != token:
        return web.json_response({"error": "Unauthorized"}, status=401)
    return None


def _ui_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hermes Clone Controller</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; background: #0b1020; color: #e8ecff; }
    .card { border: 1px solid #2a335c; border-radius: 10px; padding: 16px; margin-bottom: 16px; background: #121938; }
    h1 { margin-top: 0; }
    input, button, select { padding: 8px; border-radius: 8px; border: 1px solid #374173; background: #0f1530; color: #e8ecff; }
    button { cursor: pointer; }
    .row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; border-bottom: 1px solid #2a335c; padding: 8px 6px; font-size: 14px; vertical-align: top; }
    .muted { color: #a9b4df; font-size: 13px; }
    .pill { padding: 2px 8px; border-radius: 999px; border: 1px solid #3b467a; font-size: 12px; }
    pre { white-space: pre-wrap; background: #0b1020; border: 1px solid #2a335c; border-radius: 8px; padding: 8px; }
  </style>
</head>
<body>
  <h1>Hermes Clone Controller</h1>
  <div class="card">
    <div class="muted">Control API token</div>
    <div class="row">
      <input id="token" type="password" placeholder="CONTROL_API_TOKEN" style="min-width:320px" />
      <button id="saveToken">Save token</button>
      <button id="refresh">Refresh runs</button>
    </div>
  </div>

  <div class="card">
    <h3>Create Clone</h3>
    <div class="row">
      <input id="targetName" placeholder="target_name (e.g. hermes-clone-01)" style="min-width:320px" />
      <input id="botDisplayName" placeholder="bot_display_name (optional)" style="min-width:280px" />
      <select id="cloneMode">
        <option value="fresh" selected>fresh</option>
        <option value="stateful">stateful</option>
      </select>
      <button id="createClone">Create clone</button>
    </div>
    <div class="row">
      <input id="snapshotUrl" placeholder="snapshot_url (optional for stateful)" style="min-width:420px" />
    </div>
    <div id="createResult" class="muted"></div>
  </div>

  <div class="card">
    <h3>Recent Runs</h3>
    <table>
      <thead><tr><th>Run ID</th><th>Status</th><th>Target</th><th>Service</th><th>Project</th><th>Updated</th><th>Error</th></tr></thead>
      <tbody id="runsBody"></tbody>
    </table>
  </div>

<script>
  const tokenInput = document.getElementById('token');
  const runsBody = document.getElementById('runsBody');
  const createResult = document.getElementById('createResult');
  tokenInput.value = localStorage.getItem('controlApiToken') || '';

  function authHeaders() {
    const token = tokenInput.value.trim();
    return token ? { 'Authorization': 'Bearer ' + token } : {};
  }

  async function refreshRuns() {
    runsBody.innerHTML = '';
    try {
      const res = await fetch('/api/control/clone?limit=100', { headers: authHeaders() });
      if (!res.ok) {
        runsBody.innerHTML = '<tr><td colspan="7">Failed to load runs: HTTP ' + res.status + '</td></tr>';
        return;
      }
      const data = await res.json();
      const runs = data.runs || [];
      if (!runs.length) {
        runsBody.innerHTML = '<tr><td colspan="7" class="muted">No clone runs yet.</td></tr>';
        return;
      }
      for (const run of runs) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><code>${run.run_id || ''}</code></td>
          <td><span class="pill">${run.status || ''}</span></td>
          <td>${run.target_name || ''}</td>
          <td>${run.target_service_id || ''}</td>
          <td>${run.inferred_target_project_id || ''}</td>
          <td>${run.updated_at || run.created_at || ''}</td>
          <td>${run.error ? '<pre>' + String(run.error) + '</pre>' : ''}</td>
        `;
        runsBody.appendChild(tr);
      }
    } catch (err) {
      runsBody.innerHTML = '<tr><td colspan="7">Error loading runs: ' + err + '</td></tr>';
    }
  }

  document.getElementById('saveToken').addEventListener('click', () => {
    localStorage.setItem('controlApiToken', tokenInput.value.trim());
    refreshRuns();
  });
  document.getElementById('refresh').addEventListener('click', refreshRuns);

  document.getElementById('createClone').addEventListener('click', async () => {
    createResult.textContent = '';
    const targetName = document.getElementById('targetName').value.trim();
    const botDisplayName = document.getElementById('botDisplayName').value.trim();
    const cloneMode = document.getElementById('cloneMode').value;
    const snapshotUrl = document.getElementById('snapshotUrl').value.trim();
    if (!targetName) {
      createResult.textContent = 'target_name is required.';
      return;
    }
    const body = { target_name: targetName, clone_mode: cloneMode };
    if (botDisplayName) body.bot_display_name = botDisplayName;
    if (snapshotUrl) body.snapshot_url = snapshotUrl;
    try {
      const res = await fetch('/api/control/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        createResult.textContent = 'Failed: HTTP ' + res.status + ' ' + JSON.stringify(data);
        return;
      }
      createResult.textContent = 'Queued clone run: ' + (data.run_id || '(no run_id)');
      await refreshRuns();
    } catch (err) {
      createResult.textContent = 'Error: ' + err;
    }
  });

  refreshRuns();
  setInterval(refreshRuns, 7000);
</script>
</body>
</html>
"""


async def handle_health(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "hermes-controller"})


async def handle_control_ui(_request: web.Request) -> web.Response:
    return web.Response(text=_ui_html(), content_type="text/html")


async def handle_clone(request: web.Request) -> web.Response:
    auth_err = _check_auth(request)
    if auth_err:
        return auth_err
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)
    target_name = str(body.get("target_name", "")).strip()
    if not target_name:
        return web.json_response({"error": "target_name is required"}, status=400)

    run_id = RailwayCloneOrchestrator().start(
        CloneRequest(
            target_name=target_name,
            clone_mode=str(body.get("clone_mode", "fresh")),
            bot_display_name=body.get("bot_display_name"),
            bot_username=body.get("bot_username"),
            idempotency_key=body.get("idempotency_key"),
            snapshot_url=body.get("snapshot_url"),
        )
    )
    return web.json_response({"run_id": run_id, "status": "queued"}, status=202)


async def handle_clone_runs(request: web.Request) -> web.Response:
    auth_err = _check_auth(request)
    if auth_err:
        return auth_err
    limit_raw = request.query.get("limit", "50")
    try:
        limit = int(limit_raw)
    except ValueError:
        limit = 50
    runs = CloneRunStore().list_runs(limit=limit)
    return web.json_response({"runs": runs})


async def handle_clone_status(request: web.Request) -> web.Response:
    auth_err = _check_auth(request)
    if auth_err:
        return auth_err
    run_id = request.match_info["run_id"]
    run = CloneRunStore().get(run_id)
    if not run:
        return web.json_response({"error": "Clone run not found"}, status=404)
    return web.json_response(run)


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_get("/control", handle_control_ui)
    app.router.add_get("/api/control/clone", handle_clone_runs)
    app.router.add_post("/api/control/clone", handle_clone)
    app.router.add_get("/api/control/clone/{run_id}", handle_clone_status)
    return app


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    host = os.getenv("CONTROLLER_HOST", "0.0.0.0")
    port = int(os.getenv("CONTROLLER_PORT", os.getenv("PORT", "8080")))
    web.run_app(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()

