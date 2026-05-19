"""Helpers for loading Hermes .env files consistently across entrypoints."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from utils import atomic_replace


# Env var name suffixes that indicate credential values.  These are the
# only env vars whose values we sanitize on load — we must not silently
# alter arbitrary user env vars, but credentials are known to require
# pure ASCII (they become HTTP header values).
_CREDENTIAL_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_KEY")

# Names we've already warned about during this process, so repeated
# load_hermes_dotenv() calls (user env + project env, gateway hot-reload,
# tests) don't spam the same warning multiple times.
_WARNED_KEYS: set[str] = set()


# Platform-as-a-Service / orchestrator indicators.  When any of these is
# present in os.environ, the platform is presumed to be the authoritative
# source of env vars (vs. a stale ``~/.hermes/.env`` left over from an
# earlier ``hermes setup`` run or bootstrapped from ``.env.example``).
#
# These names are reserved by the platform itself and never written by
# users, so their presence is a reliable signal.  See ``_detect_env_priority()``.
_PLATFORM_INDICATORS: tuple[str, ...] = (
    # Railway
    "RAILWAY_ENVIRONMENT_NAME",
    "RAILWAY_PROJECT_ID",
    "RAILWAY_SERVICE_ID",
    # Fly.io
    "FLY_APP_NAME",
    "FLY_REGION",
    # Kubernetes (auto-injected into every pod)
    "KUBERNETES_SERVICE_HOST",
    # Render.com
    "RENDER",
    # Heroku (also set by Render for web dynos)
    "DYNO",
    # Vercel
    "VERCEL",
    # Netlify
    "NETLIFY",
    # Generic explicit opt-in for any other platform / custom container.
    "HERMES_PLATFORM_INJECTED",
)

# Recognized values for the explicit ``HERMES_ENV_PRIORITY`` override.
_PRIORITY_OS_ALIASES = frozenset({"os", "env", "platform", "shell"})
_PRIORITY_FILE_ALIASES = frozenset({"file", "dotenv"})

# Literal values that mean "not configured" when found in ``.env`` or
# ``os.environ``.  Agents often misread output-redacted ``***`` (from
# ``agent.redact``) or stale setup placeholders as real credentials.
_PLACEHOLDER_VALUES = frozenset({
    "***",
    "****",
    "*****",
    "[redacted]",
    "(not set)",
    "(redacted)",
    "changeme",
    "change-me",
    "change_me",
    "your_key_here",
    "your-api-key",
    "your_api_key",
    "insert_key_here",
    "replace_me",
})

_TRUNCATED_DOC_KEY_RE = re.compile(
    r"^(?:sk|sk-or|sk-ant|xoxb|ghp_?|fc-?)-\.{2,}$",
    re.IGNORECASE,
)


def is_placeholder_env_value(value: str | None) -> bool:
    """Return True when *value* is empty or a known non-credential placeholder."""
    if value is None:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    lower = stripped.lower()
    if lower in _PLACEHOLDER_VALUES:
        return True
    if lower.startswith("your_") and lower.endswith("_here"):
        return True
    if set(stripped) == {"*"}:
        return True
    if _TRUNCATED_DOC_KEY_RE.match(stripped):
        return True
    return False


def is_effective_env_value(key: str, value: str | None) -> bool:
    """True when *value* is a non-empty, non-placeholder env assignment."""
    if is_placeholder_env_value(value):
        return False
    return bool(str(value).strip())


def get_effective_env(key: str, default: str | None = None) -> str | None:
    """Like ``os.getenv`` but treats placeholder values as unset."""
    value = os.getenv(key, default)
    if is_placeholder_env_value(value):
        return None
    return value


def _detect_env_priority() -> str:
    """Return the active env priority mode: ``"os"`` or ``"file"``.

    Resolution order:
      1. Explicit ``HERMES_ENV_PRIORITY`` env var.
         ``os`` / ``env`` / ``platform`` / ``shell`` → os.environ wins.
         ``file`` / ``dotenv`` → ``.env`` file wins.
      2. Auto-detect: if any platform indicator (Railway, Fly, k8s, …) is
         present, default to ``"os"``.  Container/PaaS deployments treat the
         platform as the source of truth for credentials and config.
      3. Default: ``"file"``.  Preserves the legacy "stale shell exports"
         override behavior for interactive CLI users who edit
         ``~/.hermes/.env`` and expect it to take effect on next launch.
    """
    explicit = os.environ.get("HERMES_ENV_PRIORITY", "").strip().lower()
    if explicit in _PRIORITY_OS_ALIASES:
        return "os"
    if explicit in _PRIORITY_FILE_ALIASES:
        return "file"
    if any(os.environ.get(name) for name in _PLATFORM_INDICATORS):
        return "os"
    return "file"


def _format_offending_chars(value: str, limit: int = 3) -> str:
    """Return a compact 'U+XXXX ('c'), ...' summary of non-ASCII codepoints."""
    seen: list[str] = []
    for ch in value:
        if ord(ch) > 127:
            label = f"U+{ord(ch):04X}"
            if ch.isprintable():
                label += f" ({ch!r})"
            if label not in seen:
                seen.append(label)
            if len(seen) >= limit:
                break
    return ", ".join(seen)


def _sanitize_loaded_credentials() -> None:
    """Strip non-ASCII characters from credential env vars in os.environ.

    Called after dotenv loads so the rest of the codebase never sees
    non-ASCII API keys.  Only touches env vars whose names end with
    known credential suffixes (``_API_KEY``, ``_TOKEN``, etc.).

    Emits a one-line warning to stderr when characters are stripped.
    Silent stripping would mask copy-paste corruption (Unicode lookalike
    glyphs from PDFs / rich-text editors, ZWSP from web pages) as opaque
    provider-side "invalid API key" errors (see #6843).
    """
    for key, value in list(os.environ.items()):
        if not any(key.endswith(suffix) for suffix in _CREDENTIAL_SUFFIXES):
            continue
        try:
            value.encode("ascii")
            continue
        except UnicodeEncodeError:
            pass
        cleaned = value.encode("ascii", errors="ignore").decode("ascii")
        os.environ[key] = cleaned
        if key in _WARNED_KEYS:
            continue
        _WARNED_KEYS.add(key)
        stripped = len(value) - len(cleaned)
        detail = _format_offending_chars(value) or "non-printable"
        print(
            f"  Warning: {key} contained {stripped} non-ASCII character"
            f"{'s' if stripped != 1 else ''} ({detail}) — stripped so the "
            f"key can be sent as an HTTP header.",
            file=sys.stderr,
        )
        print(
            "  This usually means the key was copy-pasted from a PDF, "
            "rich-text editor, or web page that substituted lookalike\n"
            "  Unicode glyphs for ASCII letters. If authentication fails "
            '(e.g. "API key not valid"), re-copy the key from the\n'
            "  provider's dashboard and run `hermes setup` (or edit the "
            ".env file in a plain-text editor).",
            file=sys.stderr,
        )


def _dotenv_keys_with_empty_value(path: Path) -> set[str]:
    """Keys in a .env file whose value is empty or a known placeholder.

    Used so ``KEY=`` / ``KEY=***`` lines do not wipe a non-empty value
    already in ``os.environ`` (e.g. Railway / k8s injects OPENROUTER_API_KEY
    while HERMES_HOME/.env was bootstrapped from ``.env.example``).
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
        if (
            len(val_stripped) >= 2
            and val_stripped[0] == val_stripped[-1]
            and val_stripped[0] in "\"'"
        ):
            val_stripped = val_stripped[1:-1]
        if is_placeholder_env_value(val_stripped):
            keys.add(key)
    return keys


def _strip_placeholder_credentials_from_environ() -> None:
    """Remove placeholder credential values from ``os.environ`` after load."""
    for key, value in list(os.environ.items()):
        if not any(key.endswith(suffix) for suffix in _CREDENTIAL_SUFFIXES):
            continue
        if is_placeholder_env_value(value):
            os.environ.pop(key, None)


def _load_dotenv_with_fallback(path: Path, *, override: bool) -> None:
    try:
        load_dotenv(dotenv_path=path, override=override, encoding="utf-8")
    except UnicodeDecodeError:
        load_dotenv(dotenv_path=path, override=override, encoding="latin-1")
    # Strip non-ASCII characters from credential env vars that were just
    # loaded.  API keys must be pure ASCII since they're sent as HTTP
    # header values (httpx encodes headers as ASCII).  Non-ASCII chars
    # typically come from copy-pasting keys from PDFs or rich-text editors
    # that substitute Unicode lookalike glyphs (e.g. ʋ U+028B for v).
    _sanitize_loaded_credentials()


def _sanitize_env_file_if_needed(path: Path) -> None:
    """Pre-sanitize a .env file before python-dotenv reads it.

    python-dotenv does not handle corrupted lines where multiple
    KEY=VALUE pairs are concatenated on a single line (missing newline).
    This produces mangled values — e.g. a bot token duplicated 8×
    (see #8908).

    We delegate to ``hermes_cli.config._sanitize_env_lines`` which
    already knows all valid Hermes env-var names and can split
    concatenated lines correctly.
    """
    if not path.exists():
        return
    try:
        from hermes_cli.config import _sanitize_env_lines
    except ImportError:
        return  # early bootstrap — config module not available yet

    read_kw = {"encoding": "utf-8-sig", "errors": "replace"}
    try:
        with open(path, **read_kw) as f:
            original = f.readlines()
        sanitized = _sanitize_env_lines(original)
        if sanitized != original:
            import tempfile
            fd, tmp = tempfile.mkstemp(
                dir=str(path.parent), suffix=".tmp", prefix=".env_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.writelines(sanitized)
                    f.flush()
                    os.fsync(f.fileno())
                atomic_replace(tmp, path)
            except BaseException:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
    except Exception:
        pass  # best-effort — don't block gateway startup


def load_hermes_dotenv(
    *,
    hermes_home: str | os.PathLike | None = None,
    project_env: str | os.PathLike | None = None,
) -> list[Path]:
    """Load Hermes environment files with priority-aware merging.

    Two priority modes (see ``_detect_env_priority()``):

    ``"file"`` (default on dev/CLI machines):
    - ``~/.hermes/.env`` overrides stale shell-exported values when present.
    - A key in that file with an empty value (``KEY=``) does not clear the same
      variable if the process environment already had a non-empty value.
    - project ``.env`` acts as a dev fallback and only fills missing values when
      the user env exists.
    - if no user env exists, the project ``.env`` also overrides stale shell vars.

    ``"os"`` (auto-selected on Railway / Fly / k8s / Render / Heroku / Vercel /
    Netlify, or when ``HERMES_ENV_PRIORITY=os`` is set explicitly):
    - Any value already present in ``os.environ`` with a non-empty string
      WINS over the same key in ``.env``.  This prevents stale or
      placeholder values in ``$HERMES_HOME/.env`` (typically bootstrapped
      from ``.env.example`` on a persistent volume) from silently shadowing
      credentials and config injected by the hosting platform.
    - ``.env`` can still POPULATE keys that are not set in ``os.environ``,
      so file-only configuration continues to work as before.
    """
    loaded: list[Path] = []

    home_path = Path(hermes_home or os.getenv("HERMES_HOME", Path.home() / ".hermes"))
    user_env = home_path / ".env"
    project_env_path = Path(project_env) if project_env else None

    # Fix corrupted .env files before python-dotenv parses them (#8908).
    if user_env.exists():
        _sanitize_env_file_if_needed(user_env)
    if project_env_path and project_env_path.exists():
        _sanitize_env_file_if_needed(project_env_path)

    priority = _detect_env_priority()

    # Snapshot the platform-injected environment BEFORE any dotenv loading
    # happens.  In "os" priority mode, these values are restored after the
    # file loaders have run so the file cannot override them.  Only
    # non-empty strings are snapshotted — empty/whitespace values are not
    # considered authoritative.
    pre_load_env: dict[str, str] = {}
    if priority == "os":
        pre_load_env = {
            k: v for k, v in os.environ.items() if isinstance(v, str) and v.strip()
        }

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

    # In "os" priority mode, restore any value that .env clobbered.  Note
    # we only restore keys whose os.environ value actually changed — this
    # keeps "file" loads of brand-new keys (those not in pre_load_env) intact.
    if pre_load_env:
        for key, value in pre_load_env.items():
            if os.environ.get(key) != value:
                os.environ[key] = value

    _strip_placeholder_credentials_from_environ()

    return loaded
