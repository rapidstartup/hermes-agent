"""Helpers for loading Hermes .env files consistently across entrypoints."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _dotenv_keys_with_empty_value(path: Path) -> set[str]:
    """Keys assigned to an empty value in a .env file (template placeholders).

    Used so `KEY=` lines do not wipe a non-empty value already in os.environ
    (e.g. Railway / k8s injects OPENROUTER_API_KEY while HERMES_HOME/.env was
    bootstrapped from .env.example).
    """
    keys: set[str] = set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return keys
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val_stripped = val.strip()
        if (len(val_stripped) >= 2 and val_stripped[0] == val_stripped[-1] and val_stripped[0] in "\"'"):
            val_stripped = val_stripped[1:-1]
        if val_stripped == "":
            keys.add(key)
    return keys


def _load_dotenv_with_fallback(path: Path, *, override: bool) -> None:
    try:
        load_dotenv(dotenv_path=path, override=override, encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(dotenv_path=path, override=override, encoding="latin-1")


def load_hermes_dotenv(
    *,
    hermes_home: str | os.PathLike | None = None,
    project_env: str | os.PathLike | None = None,
) -> list[Path]:
    """Load Hermes environment files with user config taking precedence.

    Behavior:
    - `~/.hermes/.env` overrides stale shell-exported values when present.
    - A key in that file with an empty value (``KEY=``) does not clear the same
      variable if the process environment already had a non-empty value.
    - project `.env` acts as a dev fallback and only fills missing values when
      the user env exists.
    - if no user env exists, the project `.env` also overrides stale shell vars.
    """
    loaded: list[Path] = []

    home_path = Path(hermes_home or os.getenv("HERMES_HOME", Path.home() / ".hermes"))
    user_env = home_path / ".env"
    project_env_path = Path(project_env) if project_env else None

    if user_env.exists():
        empty_keys = _dotenv_keys_with_empty_value(user_env)
        preserved = {
            k: os.environ[k]
            for k in empty_keys
            if k in os.environ and os.environ[k].strip()
        }
        _load_dotenv_with_fallback(user_env, override=True)
        for key, value in preserved.items():
            if not os.environ.get(key, "").strip():
                os.environ[key] = value
        loaded.append(user_env)

    if project_env_path and project_env_path.exists():
        _load_dotenv_with_fallback(project_env_path, override=not loaded)
        loaded.append(project_env_path)

    return loaded
