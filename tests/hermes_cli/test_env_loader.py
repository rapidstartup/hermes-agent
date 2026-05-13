import importlib
import os
import sys
from pathlib import Path

from hermes_cli.env_loader import load_hermes_dotenv


def test_empty_user_env_does_not_wipe_injected_secret(tmp_path, monkeypatch):
    """Railway/k8s sets OPENROUTER_API_KEY; bootstrapped HERMES_HOME/.env has KEY=."""
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text("OPENROUTER_API_KEY=\nOTHER=set\n", encoding="utf-8")

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-platform")
    monkeypatch.delenv("OTHER", raising=False)

    loaded = load_hermes_dotenv(hermes_home=home)

    assert loaded == [env_file]
    assert os.getenv("OPENROUTER_API_KEY") == "sk-from-platform"
    assert os.getenv("OTHER") == "set"


def test_user_env_overrides_stale_shell_values(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text("OPENAI_BASE_URL=https://new.example/v1\n", encoding="utf-8")

    monkeypatch.setenv("OPENAI_BASE_URL", "https://old.example/v1")

    loaded = load_hermes_dotenv(hermes_home=home)

    assert loaded == [env_file]
    assert os.getenv("OPENAI_BASE_URL") == "https://new.example/v1"


def test_project_env_overrides_stale_shell_values_when_user_env_missing(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    project_env = tmp_path / ".env"
    project_env.write_text("OPENAI_BASE_URL=https://project.example/v1\n", encoding="utf-8")

    monkeypatch.setenv("OPENAI_BASE_URL", "https://old.example/v1")

    loaded = load_hermes_dotenv(hermes_home=home, project_env=project_env)

    assert loaded == [project_env]
    assert os.getenv("OPENAI_BASE_URL") == "https://project.example/v1"


def test_project_env_is_sanitized_before_loading(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    project_env = tmp_path / ".env"
    project_env.write_text(
        "TELEGRAM_BOT_TOKEN=8356550917:AAGGEkzg06Hrc3Hjb3Sa1jkGVDOdU_lYy2Q"
        "ANTHROPIC_API_KEY=sk-ant-test123\n",
        encoding="utf-8",
    )

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    loaded = load_hermes_dotenv(hermes_home=home, project_env=project_env)

    assert loaded == [project_env]
    assert os.getenv("TELEGRAM_BOT_TOKEN") == "8356550917:AAGGEkzg06Hrc3Hjb3Sa1jkGVDOdU_lYy2Q"
    assert os.getenv("ANTHROPIC_API_KEY") == "sk-ant-test123"


def test_user_env_takes_precedence_over_project_env(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    user_env = home / ".env"
    project_env = tmp_path / ".env"
    user_env.write_text("OPENAI_BASE_URL=https://user.example/v1\n", encoding="utf-8")
    project_env.write_text("OPENAI_BASE_URL=https://project.example/v1\nOPENAI_API_KEY=project-key\n", encoding="utf-8")

    monkeypatch.setenv("OPENAI_BASE_URL", "https://old.example/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    loaded = load_hermes_dotenv(hermes_home=home, project_env=project_env)

    assert loaded == [user_env, project_env]
    assert os.getenv("OPENAI_BASE_URL") == "https://user.example/v1"
    assert os.getenv("OPENAI_API_KEY") == "project-key"


def test_main_import_applies_user_env_over_shell_values(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    (home / ".env").write_text(
        "OPENAI_BASE_URL=https://new.example/v1\nHERMES_INFERENCE_PROVIDER=custom\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("OPENAI_BASE_URL", "https://old.example/v1")
    monkeypatch.setenv("HERMES_INFERENCE_PROVIDER", "openrouter")

    sys.modules.pop("hermes_cli.main", None)
    importlib.import_module("hermes_cli.main")

    assert os.getenv("OPENAI_BASE_URL") == "https://new.example/v1"
    assert os.getenv("HERMES_INFERENCE_PROVIDER") == "custom"


# ── Platform-injection priority (Railway / Fly / k8s / etc.) ──────────────
#
# On a PaaS the platform's variables UI is the source of truth for
# credentials and config — they are injected into os.environ at boot.
# A stale ~/.hermes/.env on a persistent volume (typically bootstrapped
# from .env.example, or written by an earlier `hermes setup` run) must
# not silently clobber those platform-injected values.

def test_platform_indicator_preserves_injected_credentials(tmp_path, monkeypatch):
    """Railway-style: platform indicator + .env with stale value → injected wins."""
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text(
        "FIRECRAWL_API_KEY=fc-stale-from-old-setup\n"
        "EXA_API_KEY=exa-stale\n"
        "ONLY_IN_FILE=file-value\n",
        encoding="utf-8",
    )

    # Simulate Railway runtime: indicator set + Hermes credentials injected.
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-from-platform")
    monkeypatch.setenv("EXA_API_KEY", "exa-from-platform")
    monkeypatch.delenv("ONLY_IN_FILE", raising=False)

    loaded = load_hermes_dotenv(hermes_home=home)

    assert loaded == [env_file]
    # Platform values survive — file did not override.
    assert os.getenv("FIRECRAWL_API_KEY") == "fc-from-platform"
    assert os.getenv("EXA_API_KEY") == "exa-from-platform"
    # File-only keys still get loaded.
    assert os.getenv("ONLY_IN_FILE") == "file-value"


def test_explicit_priority_os_preserves_injected_credentials(tmp_path, monkeypatch):
    """HERMES_ENV_PRIORITY=os explicitly opts into platform-priority mode."""
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-from-file\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_ENV_PRIORITY", "os")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-platform")

    load_hermes_dotenv(hermes_home=home)

    assert os.getenv("OPENROUTER_API_KEY") == "sk-from-platform"


def test_explicit_priority_file_overrides_platform_indicator(tmp_path, monkeypatch):
    """HERMES_ENV_PRIORITY=file forces legacy "file wins" behavior even on Railway."""
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text("OPENROUTER_API_KEY=sk-from-file\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_ENV_PRIORITY", "file")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-platform")

    load_hermes_dotenv(hermes_home=home)

    # Explicit override beats the auto-detect.
    assert os.getenv("OPENROUTER_API_KEY") == "sk-from-file"


def test_platform_priority_loads_keys_only_in_file(tmp_path, monkeypatch):
    """In platform mode, .env still populates keys that aren't on the platform."""
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text(
        "EXA_API_KEY=exa-from-file\n"
        "FIRECRAWL_API_KEY=fc-from-file\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)

    load_hermes_dotenv(hermes_home=home)

    assert os.getenv("EXA_API_KEY") == "exa-from-file"
    assert os.getenv("FIRECRAWL_API_KEY") == "fc-from-file"


def test_default_mode_still_lets_file_override_shell(tmp_path, monkeypatch):
    """Without a platform indicator, legacy "file wins" behavior is preserved.

    Pinned regression: dev/CLI users who edit ~/.hermes/.env to update a base
    URL, model name, or credential must still see the change after restart
    even if their shell still has the old value exported.
    """
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"
    env_file.write_text(
        "OPENAI_BASE_URL=https://new.example/v1\n"
        "OPENROUTER_API_KEY=sk-from-file\n",
        encoding="utf-8",
    )

    # Hermetic conftest already deletes RAILWAY_*/FLY_*/etc., but be explicit.
    monkeypatch.delenv("HERMES_ENV_PRIORITY", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://stale-shell.example/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-stale-shell")

    load_hermes_dotenv(hermes_home=home)

    assert os.getenv("OPENAI_BASE_URL") == "https://new.example/v1"
    assert os.getenv("OPENROUTER_API_KEY") == "sk-from-file"


def test_platform_priority_via_each_indicator(tmp_path, monkeypatch):
    """Every supported platform indicator should trigger os-priority mode."""
    home = tmp_path / "hermes"
    home.mkdir()
    env_file = home / ".env"

    indicators = (
        "RAILWAY_ENVIRONMENT_NAME",
        "RAILWAY_PROJECT_ID",
        "RAILWAY_SERVICE_ID",
        "FLY_APP_NAME",
        "FLY_REGION",
        "KUBERNETES_SERVICE_HOST",
        "RENDER",
        "DYNO",
        "VERCEL",
        "NETLIFY",
        "HERMES_PLATFORM_INJECTED",
    )

    for indicator in indicators:
        env_file.write_text("FIRECRAWL_API_KEY=fc-stale\n", encoding="utf-8")
        # Reset state for each iteration.
        for name in indicators:
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv(indicator, "1")
        monkeypatch.setenv("FIRECRAWL_API_KEY", "fc-platform")

        load_hermes_dotenv(hermes_home=home)

        assert os.getenv("FIRECRAWL_API_KEY") == "fc-platform", (
            f"Platform indicator {indicator!r} did not trigger os-priority mode"
        )
