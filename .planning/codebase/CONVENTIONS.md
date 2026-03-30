# Coding Conventions

**Analysis Date:** 2026-03-29

## Naming Patterns

### Files

- **Python modules:** `snake_case.py` (e.g., `file_tools.py`, `model_tools.py`, `registry.py`)
- **Test files:** `test_*.py` for unit tests (e.g., `tests/test_model_tools.py`), or `test_*.py` organized by module subdirectory (e.g., `tests/agent/test_prompt_builder.py`)
- **CLI commands:** `*.py` matching command name (e.g., `hermes_cli/config.py`, `hermes_cli/commands.py`)
- **Gateway platforms:** `gateway/platforms/telegram.py`, `gateway/platforms/discord.py`

### Classes

- **PascalCase:** `class AIAgent` in `run_agent.py` (line 139), `class HermesCLI` in `cli.py`
- **Dataclasses:** `@dataclass(frozen=True)` for immutable command definitions in `hermes_cli/commands.py` (line 27)
- **Test classes:** `class TestHandleFunctionCall` in `tests/test_model_tools.py` (line 20), `class TestGuidanceConstants` in `tests/agent/test_prompt_builder.py` (line 34)

### Functions

- **snake_case:** `def handle_function_call()` in `model_tools.py` (line 32), `def _scan_context_content()` in `agent/prompt_builder.py` (line 10)
- **Private functions:** Leading underscore `_private_function()`, e.g., `_get_file_ops()` in `tools/file_tools.py` (line 38)
- **Tool handlers:** Simple snake_case matching tool name, registered via `registry.register()` in tool files

### Variables

- **snake_case:** `tool_names`, `task_id`, `fake_home`
- **Private variables:** Leading underscore `_private_var`
- **Constants:** UPPER_SNAKE_CASE for true constants, but most config uses lowercase keys
- **Module-level logger:** `logger = logging.getLogger(__name__)` (118 occurrences across codebase)

### Types

- **Type hints:** Full typing used throughout (`from typing import List, Dict, Any, Optional`)
- **Pydantic models:** Used for configuration (`GatewayConfig`, `HomeChannel`, `PlatformConfig` in `gateway/config.py`)

## Code Style

### Formatting

- **No automatic formatter configured:** No `.prettierrc`, `.eslintrc`, or `ruff.toml` found
- **PEP 8 compliant:** 4-space indentation, snake_case naming
- **Line length:** Generally under 120 characters, but not strictly enforced

### Linting

- **No explicit linting config:** No `.pylintrc`, `ruff.toml`, or similar
- **Pytest markers defined:** In `pyproject.toml` (lines 101-103):
  ```python
  markers = [
      "integration: marks tests requiring external services (API keys, Modal, etc.)",
  ]
  ```

### Import Organization

**Order in source files:**
1. Standard library imports (`import os`, `import json`, `import logging`)
2. Third-party imports (`from openai import OpenAI`, `import fire`, `import yaml`)
3. Local project imports (`from model_tools import ...`, `from tools.registry import registry`)

**Example from `run_agent.py` (lines 23-52):**
```python
import os
import json
import logging
logger = logging.getLogger(__name__)
from openai import OpenAI
import fire
from hermes_constants import get_hermes_home, display_hermes_home
from hermes_cli.env_loader import load_hermes_dotenv
from model_tools import (...)
```

**Path aliases:** Not used; all imports use relative paths from project root or package.

## Error Handling

### Pattern: JSON Error Responses

Tool handlers must return JSON strings with error format:
```python
# From tools/registry.py (lines 134, 142)
return json.dumps({"error": f"Unknown tool: {name}"})
return json.dumps({"error": f"Tool execution failed: {type(e).__name__}: {e}"})
```

### Pattern: Try/Except with Logging

```python
# From tools/registry.py (lines 136-142)
try:
    if entry.is_async:
        from model_tools import _run_async
        return _run_async(entry.handler(args, **kwargs))
    return entry.handler(args, **kwargs)
except Exception as e:
    logger.exception("Tool %s dispatch error: %s", name, e)
    return json.dumps({"error": f"Tool execution failed: {type(e).__name__}: {e}"})
```

### Pattern: Expected vs Unexpected Errors

```python
# From tools/file_tools.py (lines 17-23)
def _is_expected_write_exception(exc: Exception) -> bool:
    """Return True for expected write denials that should not hit error logs."""
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError) and exc.errno in _EXPECTED_WRITE_ERRNOS:
        return True
    return False
```

### Pattern: Graceful Degradation

Tool registry checks silently skip unavailable tools (lines 106-117 in `tools/registry.py`):
```python
if entry.check_fn:
    if entry.check_fn not in check_results:
        try:
            check_results[entry.check_fn] = bool(entry.check_fn())
        except Exception:
            check_results[entry.check_fn] = False
    if not check_results[entry.check_fn]:
        continue  # Skip tool silently
```

## Logging

### Framework

- **Standard library:** `logging` module used exclusively
- **Module-level logger:** `logger = logging.getLogger(__name__)` in every module
- **118 modules** use this pattern across the codebase

### Patterns

```python
# Standard module logger setup (from tools/file_tools.py, line 11)
logger = logging.getLogger(__name__)

# Info logging
logger.info("%s environment ready for task %s", env_type, task_id[:8])

# Debug logging
logger.debug("Tool %s unavailable (check failed)", name)

# Exception logging with traceback
logger.exception("Tool %s dispatch error: %s", name, e)
```

### Log File Location

Error logs written to `~/.hermes/logs/errors.log` (see `run_agent.py` around line 687).

## Configuration Formats

### YAML Configuration

- **Primary config:** `~/.hermes/config.yaml`
- **Secrets:** `~/.hermes/.env` (never committed)

**Example from test fixtures (`tests/test_cli_init.py`, lines 15-24):**
```python
_clean_config = {
    "model": {
        "default": "anthropic/claude-opus-4.6",
        "base_url": "https://openrouter.ai/api/v1",
        "provider": "auto",
    },
    "display": {"compact": False, "tool_progress": "all"},
    "agent": {},
    "terminal": {"env_type": "local"},
}
```

### Environment Variables

- **Prefix:** `HERMES_` for Hermes-specific vars (e.g., `HERMES_MAX_ITERATIONS`)
- **Provider vars:** `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.
- **Tool vars:** Provider-specific (e.g., `BROWSERBASE_API_KEY`, `FIRECRAWL_API_KEY`)

### Config Loading

Two separate systems:
- `load_cli_config()` in `cli.py` - CLI mode
- `load_config()` in `hermes_cli/config.py` - `hermes tools`, `hermes setup`
- Direct YAML load in `gateway/run.py` - Gateway mode

## Documentation Patterns

### Module Docstrings

**Purpose:** First line describes module purpose, followed by details.

```python
# From tools/registry.py (lines 1-15)
"""Central registry for all hermes-agent tools.

Each tool file calls ``registry.register()`` at module level to declare its
schema, handler, toolset membership, and availability check.  ``model_tools.py``
queries the registry instead of maintaining its own parallel data structures.

Import chain (circular-import safe):
    tools/registry.py  (no imports from model_tools or tool files)
           ^
    tools/*.py  (import from tools.registry at module level)
           ^
    model_tools.py  (imports tools.registry + all tool modules)
           ^
    run_agent.py, cli.py, batch_runner.py, etc.
"""
```

### Function Docstrings

**Google-style or simple descriptive:**
```python
# From tools/file_tools.py (lines 38-47)
def _get_file_ops(task_id: str = "default") -> ShellFileOperations:
    """Get or create ShellFileOperations for a terminal environment.

    Respects the TERMINAL_ENV setting -- if the task_id doesn't have an
    environment yet, creates one using the configured backend (local, docker,
    modal, etc.) rather than always defaulting to local.

    Thread-safe: uses the same per-task creation locks as terminal_tool to
    prevent duplicate sandbox creation from concurrent tool calls.
    """
```

### Inline Comments

Used for:
- **Security notes:** `# Security: block direct reads of internal Hermes cache/files` (`tools/file_tools.py`, line 171)
- **Section markers:** `# ── Global test timeout ─────────────────────────────────────────────────────` (`tests/conftest.py`, line 67)
- **Explanation of magic:** `# Fast path: check cache` (`tools/file_tools.py`, line 56)

### Test Documentation

```python
# From tests/test_model_tools.py (lines 1-2)
"""Tests for model_tools.py — function call dispatch, agent-loop interception, legacy toolsets."""
```

## Function Design

### Size Guidelines

- Large files exist (e.g., `run_agent.py` is 8000+ lines), but most modules are reasonably sized
- Complex functions broken into private helpers (`_get_file_ops`, `_scan_context_content`)

### Parameter Patterns

- **task_id:** Used for tracking tool invocations across conversation turns
- **Optional params with defaults:** `def read_file_tool(path: str, offset: int = 1, limit: int = 500, task_id: str = "default")`
- **kwargs for extensibility:** `def dispatch(self, name: str, args: dict, **kwargs)`

### Return Values

- **Tools:** Always return JSON string (required for LLM consumption)
- **Internal functions:** Type-hinted returns

## Module Design

### Tool Registration Pattern

Each tool file calls `registry.register()` at module level:
```python
# From tools/registry.py usage pattern
registry.register(
    name="example_tool",
    toolset="example",
    schema={"name": "example_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: example_tool(param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["EXAMPLE_API_KEY"],
)
```

### Singleton Pattern

- **Tool registry:** `registry = ToolRegistry()` at module level in `tools/registry.py` (line 247)
- **Config loading:** Multiple config loaders for different contexts

### Package Structure

```
hermes-agent/
├── run_agent.py          # AIAgent class — core conversation loop
├── model_tools.py        # Tool orchestration
├── toolsets.py           # Toolset definitions
├── cli.py                # HermesCLI class
├── tools/                # Tool implementations
│   └── registry.py       # Central registry (imported by all tools)
├── agent/                # Agent internals
│   ├── prompt_builder.py
│   ├── context_compressor.py
│   └── display.py
├── hermes_cli/           # CLI subcommands
└── gateway/              # Messaging platform gateway
```

---

*Convention analysis: 2026-03-29*
