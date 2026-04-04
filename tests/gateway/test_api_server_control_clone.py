"""Tests for /api/control/clone endpoints on API server adapter."""

from unittest.mock import patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from gateway.config import PlatformConfig
from gateway.platforms.api_server import APIServerAdapter, cors_middleware, security_headers_middleware


def _create_control_app(adapter: APIServerAdapter) -> web.Application:
    mws = [mw for mw in (cors_middleware, security_headers_middleware) if mw is not None]
    app = web.Application(middlewares=mws)
    app["api_server_adapter"] = adapter
    app.router.add_get("/control", adapter._handle_control_ui)
    app.router.add_get("/api/control/clone", adapter._handle_control_clone_runs)
    app.router.add_post("/api/control/clone", adapter._handle_control_clone)
    app.router.add_get("/api/control/clone/{run_id}", adapter._handle_control_clone_status)
    return app


class TestControlCloneAPI:
    @pytest.mark.asyncio
    async def test_control_ui_renders(self):
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get("/control")
            assert resp.status == 200
            text = await resp.text()
            assert "Hermes Clone Control" in text

    @pytest.mark.asyncio
    async def test_control_api_disabled_returns_404(self):
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post("/api/control/clone", json={"target_name": "demo"})
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_control_api_requires_token(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.delenv("CONTROL_API_TOKEN", raising=False)
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post("/api/control/clone", json={"target_name": "demo"})
            assert resp.status == 500

    @pytest.mark.asyncio
    async def test_control_api_unauthorized(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post(
                "/api/control/clone",
                json={"target_name": "demo"},
                headers={"Authorization": "Bearer wrong"},
            )
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_control_api_rejects_non_allowlisted_ip(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        monkeypatch.setenv("CONTROL_API_ALLOWED_IPS", "203.0.113.10")
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post(
                "/api/control/clone",
                json={"target_name": "demo"},
                headers={"Authorization": "Bearer secret"},
            )
            assert resp.status == 403

    @pytest.mark.asyncio
    async def test_control_clone_queues_run(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch("gateway.provisioning.railway_clone.RailwayCloneOrchestrator.start", return_value="clone_abc123"):
                resp = await cli.post(
                    "/api/control/clone",
                    json={"target_name": "demo-hermes"},
                    headers={"Authorization": "Bearer secret"},
                )
            assert resp.status == 202
            data = await resp.json()
            assert data["run_id"] == "clone_abc123"
            assert data["status"] == "queued"

    @pytest.mark.asyncio
    async def test_control_clone_requires_target_name(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post(
                "/api/control/clone",
                json={},
                headers={"Authorization": "Bearer secret"},
            )
            assert resp.status == 400

    @pytest.mark.asyncio
    async def test_control_clone_status_not_found(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get(
                "/api/control/clone/clone_missing",
                headers={"Authorization": "Bearer secret"},
            )
            assert resp.status == 404

    @pytest.mark.asyncio
    async def test_control_clone_runs_list(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        adapter = APIServerAdapter(PlatformConfig(enabled=True))
        app = _create_control_app(adapter)
        async with TestClient(TestServer(app)) as cli:
            with patch(
                "gateway.provisioning.railway_clone.CloneRunStore._load",
                return_value={"runs": {"clone_x": {"run_id": "clone_x", "status": "queued", "updated_at": "2026-04-04T00:00:00Z"}}},
            ):
                resp = await cli.get(
                    "/api/control/clone",
                    headers={"Authorization": "Bearer secret"},
                )
            assert resp.status == 200
            data = await resp.json()
            assert len(data["runs"]) == 1
            assert data["runs"][0]["run_id"] == "clone_x"

