"""Client for external botfather-svc provisioning API."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def sanitize_telegram_username(name: str, suffix: Optional[int] = None) -> str:
    """Convert display name to a valid Telegram bot username."""
    sanitized = re.sub(r"[^a-z0-9_]", "_", name.lower())
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    if len(sanitized) < 2:
        sanitized = f"{sanitized}_agent" if sanitized else "agent"

    if suffix is None:
        username = f"{sanitized}_bot"
        suffix_part = "_bot"
    else:
        suffix_part = f"_{suffix:02d}_bot"
        username = f"{sanitized}{suffix_part}"

    if len(username) > 32:
        max_name_len = 32 - len(suffix_part)
        sanitized = sanitized[:max_name_len].rstrip("_")
        username = f"{sanitized}{suffix_part}"
    return username


class BotfatherClient:
    """Minimal sync HTTP client for botfather-svc."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    @classmethod
    def from_env(cls) -> "BotfatherClient":
        base_url = os.getenv("BOTFATHER_SVC_URL", "").strip()
        token = os.getenv("BOTFATHER_SVC_TOKEN", "").strip()
        if not base_url or not token:
            raise RuntimeError("BOTFATHER_SVC_URL and BOTFATHER_SVC_TOKEN are required")
        return cls(base_url=base_url, token=token)

    def provision(
        self,
        display_name: str,
        explicit_username: Optional[str] = None,
        max_retries: int = 5,
    ) -> Dict[str, Any]:
        """Provision a Telegram bot, retrying username collisions."""
        display_name = (display_name or "").strip()[:64]
        if not display_name:
            raise ValueError("display_name is required")

        for attempt in range(max_retries + 1):
            suffix = None if attempt == 0 else attempt
            username = explicit_username or sanitize_telegram_username(display_name, suffix=suffix)
            payload = {"name": display_name, "username": username}
            result = self._post_json("/provision", payload)
            if result.get("success"):
                return result
            err = str(result.get("error", "")).lower()
            if explicit_username:
                return result
            if "unavailable" in err or "taken" in err or "already" in err:
                continue
            return result
        return {"success": False, "error": f"All {max_retries + 1} username attempts were taken"}

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw)
            except Exception:
                return {"success": False, "error": raw or f"HTTP {exc.code}"}
        except Exception as exc:
            return {"success": False, "error": f"botfather-svc unreachable: {exc}"}

