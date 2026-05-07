"""Tests for Railway clone orchestration helpers."""

from gateway.provisioning.botfather_client import sanitize_telegram_username
from gateway.provisioning.railway_clone import CloneRequest, CloneRunStore, RailwayCloneOrchestrator


class _FakeRailway:
    def __init__(self, *_args, **_kwargs):
        self.upserts = []

    def create_service_clone(self, **_kwargs):
        return "svc_target_123"

    def get_default_environment_id(self, _project_id):
        return "env_fake_default"

    def get_service_variables(self, _service_id):
        return {
            "OPENROUTER_API_KEY": "sk-x",
            "TELEGRAM_WEBHOOK_URL": "https://old.example/telegram",
        }

    def upsert_service_variable(self, **kwargs):
        self.upserts.append(kwargs)

    def trigger_deploy(self, **_kwargs):
        return None

    def get_service_project_id(self, _service_id):
        return "proj_inferred_999"


class _FakeBotfather:
    def provision(self, **_kwargs):
        return {"success": True, "token": "123:abc", "username": "demo_bot", "botId": "1001"}


def test_sanitize_telegram_username_shapes_suffix():
    assert sanitize_telegram_username("Sarah HR Manager").endswith("_bot")
    assert sanitize_telegram_username("Sarah HR Manager", suffix=2).endswith("_02_bot")


def test_clone_run_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    store = CloneRunStore()
    store.create("clone_1", {"run_id": "clone_1", "status": "queued"})
    assert store.get("clone_1")["status"] == "queued"
    store.update("clone_1", status="healthy")
    assert store.get("clone_1")["status"] == "healthy"


def test_orchestrator_idempotency(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    store = CloneRunStore()
    orch = RailwayCloneOrchestrator(store=store)
    store.create("clone_existing", {"run_id": "clone_existing", "idempotency_key": "key-1", "status": "queued"})
    run_id = orch.start(CloneRequest(target_name="demo", idempotency_key="key-1"))
    assert run_id == "clone_existing"


def test_run_sync_success_copies_vars_and_sets_fresh(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-token")
    monkeypatch.setenv("RAILWAY_SOURCE_SERVICE_ID", "svc_source_123")
    monkeypatch.setenv("RAILWAY_TARGET_PROJECT_ID", "proj_target_123")
    monkeypatch.setenv("BOTFATHER_SVC_URL", "https://botfather.example")
    monkeypatch.setenv("BOTFATHER_SVC_TOKEN", "token")

    store = CloneRunStore()
    orch = RailwayCloneOrchestrator(store=store)
    store.create("clone_1", {"run_id": "clone_1", "status": "queued"})

    import gateway.provisioning.railway_clone as rc

    fake_railway = _FakeRailway()
    monkeypatch.setattr(rc, "RailwayGraphQLClient", lambda *_args, **_kwargs: fake_railway)
    monkeypatch.setattr(rc.BotfatherClient, "from_env", classmethod(lambda _cls: _FakeBotfather()))

    orch._run_sync("clone_1", CloneRequest(target_name="demo-hermes", clone_mode="fresh"))
    run = store.get("clone_1")
    assert run["status"] == "healthy"
    upserts = {(x["name"], x["value"]) for x in fake_railway.upserts}
    # copied source vars (except webhook URL)
    assert ("OPENROUTER_API_KEY", "sk-x") in upserts
    assert ("TELEGRAM_WEBHOOK_URL", "https://old.example/telegram") not in upserts
    # fresh clone flags
    assert ("HERMES_CLONE_MODE", "fresh") in upserts
    assert ("HERMES_FRESH_STATE", "1") in upserts
    # telegram token injected
    assert ("TELEGRAM_BOT_TOKEN", "123:abc") in upserts


def test_run_sync_fails_without_required_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.delenv("RAILWAY_TARGET_PROJECT_ID", raising=False)
    monkeypatch.delenv("RAILWAY_SOURCE_SERVICE_ID", raising=False)
    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-token")

    store = CloneRunStore()
    orch = RailwayCloneOrchestrator(store=store)
    store.create("clone_2", {"run_id": "clone_2", "status": "queued"})
    orch._run_sync("clone_2", CloneRequest(target_name="demo"))
    run = store.get("clone_2")
    assert run["status"] == "failed"
    assert "RAILWAY_SOURCE_SERVICE_ID" in run["error"]


def test_run_sync_stateful_sets_snapshot_url(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-token")
    monkeypatch.setenv("RAILWAY_SOURCE_SERVICE_ID", "svc_source_123")
    monkeypatch.setenv("RAILWAY_TARGET_PROJECT_ID", "proj_target_123")
    monkeypatch.setenv("BOTFATHER_SVC_URL", "https://botfather.example")
    monkeypatch.setenv("BOTFATHER_SVC_TOKEN", "token")

    store = CloneRunStore()
    orch = RailwayCloneOrchestrator(store=store)
    store.create("clone_3", {"run_id": "clone_3", "status": "queued"})

    import gateway.provisioning.railway_clone as rc

    fake_railway = _FakeRailway()
    monkeypatch.setattr(rc, "RailwayGraphQLClient", lambda *_args, **_kwargs: fake_railway)
    monkeypatch.setattr(rc.BotfatherClient, "from_env", classmethod(lambda _cls: _FakeBotfather()))

    orch._run_sync(
        "clone_3",
        CloneRequest(
            target_name="demo-hermes-stateful",
            clone_mode="stateful",
            snapshot_url="https://snapshots.example/demo.tgz",
        ),
    )
    upserts = {(x["name"], x["value"]) for x in fake_railway.upserts}
    assert ("HERMES_CLONE_MODE", "stateful") in upserts
    assert ("HERMES_FRESH_STATE", "0") in upserts
    assert ("HERMES_CLONE_SNAPSHOT_URL", "https://snapshots.example/demo.tgz") in upserts


def test_run_sync_infers_target_project_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("RAILWAY_API_TOKEN", "railway-token")
    monkeypatch.setenv("RAILWAY_SOURCE_SERVICE_ID", "svc_source_123")
    monkeypatch.delenv("RAILWAY_TARGET_PROJECT_ID", raising=False)
    monkeypatch.setenv("BOTFATHER_SVC_URL", "https://botfather.example")
    monkeypatch.setenv("BOTFATHER_SVC_TOKEN", "token")

    store = CloneRunStore()
    orch = RailwayCloneOrchestrator(store=store)
    store.create("clone_4", {"run_id": "clone_4", "status": "queued"})

    import gateway.provisioning.railway_clone as rc

    fake_railway = _FakeRailway()
    monkeypatch.setattr(rc, "RailwayGraphQLClient", lambda *_args, **_kwargs: fake_railway)
    monkeypatch.setattr(rc.BotfatherClient, "from_env", classmethod(lambda _cls: _FakeBotfather()))

    orch._run_sync("clone_4", CloneRequest(target_name="demo-hermes"))
    run = store.get("clone_4")
    assert run["status"] == "healthy"
    assert run["inferred_target_project_id"] == "proj_inferred_999"

