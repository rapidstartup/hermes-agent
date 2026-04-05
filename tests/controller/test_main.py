"""Tests for standalone controller app."""

from unittest.mock import patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from controller.main import create_app


class TestControllerApp:
    @pytest.mark.asyncio
    async def test_health(self):
        app = create_app()
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_control_ui(self):
        app = create_app()
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.get("/control")
            assert resp.status == 200
            body = await resp.text()
            assert "Hermes Clone Controller" in body

    @pytest.mark.asyncio
    async def test_clone_requires_auth(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        app = create_app()
        async with TestClient(TestServer(app)) as cli:
            resp = await cli.post("/api/control/clone", json={"target_name": "demo"})
            assert resp.status == 401

    @pytest.mark.asyncio
    async def test_clone_queues(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        app = create_app()
        async with TestClient(TestServer(app)) as cli:
            with patch("controller.main.RailwayCloneOrchestrator.start", return_value="clone_123"):
                resp = await cli.post(
                    "/api/control/clone",
                    json={"target_name": "demo"},
                    headers={"Authorization": "Bearer secret"},
                )
            assert resp.status == 202
            data = await resp.json()
            assert data["run_id"] == "clone_123"

    @pytest.mark.asyncio
    async def test_clone_list_and_status(self, monkeypatch):
        monkeypatch.setenv("CONTROL_API_ENABLED", "true")
        monkeypatch.setenv("CONTROL_API_TOKEN", "secret")
        app = create_app()
        async with TestClient(TestServer(app)) as cli:
            with patch("controller.main.CloneRunStore.list_runs", return_value=[{"run_id": "clone_1", "status": "queued"}]):
                resp = await cli.get("/api/control/clone", headers={"Authorization": "Bearer secret"})
            assert resp.status == 200
            data = await resp.json()
            assert data["runs"][0]["run_id"] == "clone_1"

            with patch("controller.main.CloneRunStore.get", return_value={"run_id": "clone_1", "status": "healthy"}):
                resp2 = await cli.get("/api/control/clone/clone_1", headers={"Authorization": "Bearer secret"})
            assert resp2.status == 200
            data2 = await resp2.json()
            assert data2["status"] == "healthy"

