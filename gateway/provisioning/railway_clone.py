"""Railway clone orchestration for control-plane API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from hermes_constants import get_hermes_home
from gateway.provisioning.botfather_client import BotfatherClient

logger = logging.getLogger(__name__)

RAILWAY_GRAPHQL_URL = "https://backboard.railway.com/graphql/v2"

# Cloudflare (in front of backboard.railway.com) often returns HTTP 403 / error 1010
# when it does not like the client signature. Python's default urllib User-Agent
# triggers browser-integrity style blocks; use a conventional API client string.
_DEFAULT_RAILWAY_UA = (
    "Mozilla/5.0 (compatible; HermesRailwayClone/1.0; "
    "+https://github.com/NousResearch/hermes-agent)"
)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class CloneRunStore:
    """Persisted status store for clone runs."""

    def __init__(self) -> None:
        self._path = get_hermes_home() / "clone_runs.json"
        self._lock = threading.Lock()

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return {"runs": {}}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {"runs": {}}

    def _save(self, data: Dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")

    def create(self, run_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            data = self._load()
            data.setdefault("runs", {})[run_id] = payload
            self._save(data)

    def update(self, run_id: str, **fields: Any) -> None:
        with self._lock:
            data = self._load()
            run = data.setdefault("runs", {}).get(run_id)
            if not run:
                return
            run.update(fields)
            run["updated_at"] = _now_iso()
            self._save(data)

    def get(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._load().get("runs", {}).get(run_id)

    def find_by_idempotency(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for run in self._load().get("runs", {}).values():
                if run.get("idempotency_key") == idempotency_key:
                    return run
            return None

    def list_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            runs = list(self._load().get("runs", {}).values())
        runs.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        limit = max(1, min(200, int(limit)))
        return runs[:limit]


class RailwayGraphQLClient:
    """Minimal Railway GraphQL client."""

    def __init__(self, token: str, endpoint: str = RAILWAY_GRAPHQL_URL):
        if not token:
            raise RuntimeError("RAILWAY_API_TOKEN is required")
        self.token = token
        self.endpoint = endpoint

    def _gql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        ua = (os.getenv("RAILWAY_HTTP_USER_AGENT") or "").strip() or _DEFAULT_RAILWAY_UA
        req = urllib.request.Request(
            self.endpoint,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": ua,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Railway API HTTP {exc.code}: {raw}") from exc
        except Exception as exc:
            raise RuntimeError(f"Railway API request failed: {exc}") from exc

        if data.get("errors"):
            raise RuntimeError(f"Railway API error: {data['errors']}")
        return data.get("data", {})

    @staticmethod
    def _extract_vars(data: Any) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        if isinstance(data, dict):
            if "name" in data and "value" in data and isinstance(data["name"], str):
                out.append({"name": data["name"], "value": str(data.get("value", ""))})
            for v in data.values():
                out.extend(RailwayGraphQLClient._extract_vars(v))
        elif isinstance(data, list):
            for item in data:
                out.extend(RailwayGraphQLClient._extract_vars(item))
        return out

    def get_service_variables(self, service_id: str) -> Dict[str, str]:
        query = """
        query GetServiceVars($serviceId: String!) {
          service(id: $serviceId) {
            id
            name
            variables {
              edges {
                node {
                  name
                  value
                }
              }
            }
          }
        }
        """
        data = self._gql(query, {"serviceId": service_id})
        pairs = self._extract_vars(data)
        return {p["name"]: p["value"] for p in pairs if p.get("name")}

    def get_service_project_id(self, service_id: str) -> str:
        """Return the Railway project id for a service id."""
        query = """
        query GetServiceProject($serviceId: String!) {
          service(id: $serviceId) {
            id
            project {
              id
            }
          }
        }
        """
        data = self._gql(query, {"serviceId": service_id})
        service = data.get("service") or {}
        project = service.get("project") or {}
        project_id = project.get("id")
        if project_id:
            return str(project_id)

        # Fallback: recursively search payload for first project.id.
        def _find_project_id(node: Any) -> Optional[str]:
            if isinstance(node, dict):
                if "project" in node and isinstance(node["project"], dict):
                    pid = node["project"].get("id")
                    if pid:
                        return str(pid)
                for value in node.values():
                    found = _find_project_id(value)
                    if found:
                        return found
            elif isinstance(node, list):
                for item in node:
                    found = _find_project_id(item)
                    if found:
                        return found
            return None

        found = _find_project_id(data)
        if not found:
            raise RuntimeError("Could not infer Railway project id from source service")
        return found

    def create_service_clone(
        self,
        *,
        project_id: str,
        name: str,
        source_service_id: Optional[str] = None,
    ) -> str:
        # Uses the most common Railway mutation shape. If Railway schema differs,
        # this returns a clear API error in the run status.
        query = """
        mutation CreateService($input: ServiceCreateInput!) {
          serviceCreate(input: $input) {
            id
            name
          }
        }
        """
        input_obj: Dict[str, Any] = {"projectId": project_id, "name": name}
        if source_service_id:
            input_obj["sourceServiceId"] = source_service_id
        data = self._gql(query, {"input": input_obj})
        service = data.get("serviceCreate") or {}
        service_id = service.get("id")
        if not service_id:
            raise RuntimeError("Railway create service returned no service id")
        return service_id

    def upsert_service_variable(self, *, service_id: str, name: str, value: str) -> None:
        query = """
        mutation UpsertVariable($input: VariableUpsertInput!) {
          variableUpsert(input: $input) {
            id
            name
          }
        }
        """
        self._gql(
            query,
            {
                "input": {
                    "serviceId": service_id,
                    "name": name,
                    "value": value,
                }
            },
        )

    def trigger_deploy(self, *, service_id: str) -> None:
        query = """
        mutation TriggerDeploy($serviceId: String!) {
          serviceInstanceRedeploy(serviceId: $serviceId) {
            id
          }
        }
        """
        # Best effort: not all plans/schemas expose this mutation
        try:
            self._gql(query, {"serviceId": service_id})
        except Exception as exc:
            logger.warning("Railway deploy trigger failed (continuing): %s", exc)


@dataclass
class CloneRequest:
    target_name: str
    clone_mode: str = "fresh"
    bot_display_name: Optional[str] = None
    bot_username: Optional[str] = None
    idempotency_key: Optional[str] = None
    snapshot_url: Optional[str] = None


class RailwayCloneOrchestrator:
    """Coordinates service clone + Telegram provisioning."""

    def __init__(self, store: Optional[CloneRunStore] = None):
        self.store = store or CloneRunStore()

    def start(self, req: CloneRequest) -> str:
        if req.idempotency_key:
            existing = self.store.find_by_idempotency(req.idempotency_key)
            if existing:
                return existing["run_id"]

        run_id = f"clone_{uuid.uuid4().hex[:12]}"
        self.store.create(
            run_id,
            {
                "run_id": run_id,
                "status": "queued",
                "target_name": req.target_name,
                "clone_mode": req.clone_mode,
                "idempotency_key": req.idempotency_key,
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
            },
        )
        asyncio.create_task(asyncio.to_thread(self._run_sync, run_id, req))
        return run_id

    def _run_sync(self, run_id: str, req: CloneRequest) -> None:
        try:
            self.store.update(run_id, status="provisioning")
            railway = RailwayGraphQLClient(os.getenv("RAILWAY_API_TOKEN", ""))
            source_service_id = os.getenv("RAILWAY_SOURCE_SERVICE_ID", "").strip()
            if not source_service_id:
                raise RuntimeError("RAILWAY_SOURCE_SERVICE_ID is required")

            project_id = os.getenv("RAILWAY_TARGET_PROJECT_ID", "").strip()
            if not project_id:
                project_id = railway.get_service_project_id(source_service_id)
                self.store.update(run_id, inferred_target_project_id=project_id)

            service_id = railway.create_service_clone(
                project_id=project_id,
                name=req.target_name,
                source_service_id=source_service_id,
            )
            self.store.update(run_id, target_service_id=service_id)

            self.store.update(run_id, status="copying_variables")
            variables = railway.get_service_variables(source_service_id)
            # Do not copy webhook URL across clones by default.
            exclude = {"TELEGRAM_WEBHOOK_URL"}
            for key, value in variables.items():
                if key in exclude:
                    continue
                railway.upsert_service_variable(service_id=service_id, name=key, value=value)

            # Enforce fresh clone by default; stateful is reserved for future use.
            clone_mode = (req.clone_mode or "fresh").lower().strip()
            if clone_mode not in {"fresh", "stateful"}:
                clone_mode = "fresh"
            railway.upsert_service_variable(service_id=service_id, name="HERMES_CLONE_MODE", value=clone_mode)
            railway.upsert_service_variable(service_id=service_id, name="HERMES_FRESH_STATE", value="1" if clone_mode == "fresh" else "0")
            railway.upsert_service_variable(service_id=service_id, name="HERMES_CLONE_SOURCE_SERVICE_ID", value=source_service_id)
            if clone_mode == "stateful" and req.snapshot_url:
                railway.upsert_service_variable(
                    service_id=service_id,
                    name="HERMES_CLONE_SNAPSHOT_URL",
                    value=req.snapshot_url,
                )

            self.store.update(run_id, status="telegram")
            bot_client = BotfatherClient.from_env()
            bot_display_name = req.bot_display_name or req.target_name
            bot_result = bot_client.provision(
                display_name=bot_display_name,
                explicit_username=req.bot_username,
            )
            if not bot_result.get("success"):
                raise RuntimeError(f"Telegram bot provisioning failed: {bot_result.get('error')}")
            token = bot_result.get("token", "")
            if not token:
                raise RuntimeError("Telegram bot provisioning returned no token")
            railway.upsert_service_variable(service_id=service_id, name="TELEGRAM_BOT_TOKEN", value=token)

            self.store.update(
                run_id,
                telegram_bot_username=bot_result.get("username"),
                telegram_bot_id=bot_result.get("botId"),
            )

            self.store.update(run_id, status="deploying")
            railway.trigger_deploy(service_id=service_id)

            self.store.update(run_id, status="healthy")
        except Exception as exc:
            self.store.update(run_id, status="failed", error=str(exc))

