# Testing Patterns

**Analysis Date:** 2026-03-29

## Test Framework

### Runner

- **Framework:** pytest (version >=9.0.2, <10)
- **Config:** `pyproject.toml` lines 99-104
- **Additional plugins:** pytest-asyncio, pytest-xdist for parallel execution

```toml
# From pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests requiring external services (API keys, Modal, etc.)",
]
addopts = "-m 'not integration' -n auto"
```

### Run Commands

```bash
python -m pytest tests/ -q                    # Full suite (~3000 tests, ~3 min)
python -m pytest tests/test_model_tools.py -q  # Specific test file
python -m pytest tests/gateway/ -q             # Gateway tests
python -m pytest tests/tools/ -q               # Tool-level tests
python -m pytest -m integration tests/        # Include integration tests
```

### Assertion Library

- **Built-in pytest assertions:** `assert`, `assert isinstance()`, `assert in`
- **No external assertion library:** Uses standard pytest

## Test File Organization

### Location

- **Primary:** `tests/` directory at project root
- **Co-located:** Test files often mirror source structure (e.g., `tests/agent/test_prompt_builder.py` matches `agent/prompt_builder.py`)
- **Tool tests:** `tests/tools/test_*.py` for individual tools

### Naming Conventions

- **Unit tests:** `test_*.py` (e.g., `tests/test_model_tools.py`)
- **Integration tests:** `tests/integration/test_*.py`
- **Gateway tests:** `tests/gateway/test_*.py`
- **Test classes:** `class TestHandleFunctionCall` (PascalCase with Test prefix)

### Directory Structure

```
tests/
├── test_*.py              # Core tests (model_tools, run_agent, cli_init)
├── agent/                 # Agent module tests
│   ├── test_prompt_builder.py
│   ├── test_context_compressor.py
│   └── ...
├── tools/                 # Tool implementation tests
│   ├── test_file_tools.py
│   ├── test_terminal_tool.py
│   └── ...
├── gateway/               # Gateway/messaging platform tests
│   ├── test_config.py
│   ├── test_telegram_*.py
│   └── ...
├── integration/           # Tests requiring external services
│   ├── test_web_tools.py
│   └── ...
├── skills/                # Skill-related tests
├── honcho_integration/    # Honcho client tests
├── acp/                   # ACP adapter tests
├── cron/                  # Scheduler tests
├── fakes/                 # Fake/mock implementations
│   └── fake_ha_server.py
└── conftest.py           # Shared fixtures
```

## Test Structure

### Test Class Organization

```python
# From tests/test_model_tools.py (lines 20-40)
class TestHandleFunctionCall:
    def test_agent_loop_tool_returns_error(self):
        for tool_name in _AGENT_LOOP_TOOLS:
            result = json.loads(handle_function_call(tool_name, {}))
            assert "error" in result
            assert "agent loop" in result["error"].lower()

    def test_unknown_tool_returns_error(self):
        result = json.loads(handle_function_call("totally_fake_tool_xyz", {}))
        assert "error" in result
        assert "totally_fake_tool_xyz" in result["error"]
```

### Test Function Organization

- **Single responsibility:** Each test function tests one behavior
- **Descriptive names:** `test_agent_loop_tool_returns_error`, `test_unknown_tool_returns_error`
- **Arrange-Act-Assert pattern:** Implicit in most tests

### Section Markers

Comments used to divide test sections:
```python
# From tests/test_model_tools.py (lines 16-18)
# =========================================================================
# handle_function_call
# =========================================================================
```

## Test Fixtures and Helpers

### Global Fixtures (conftest.py)

**Location:** `tests/conftest.py`

```python
# From tests/conftest.py (lines 19-40)
@pytest.fixture(autouse=True)
def _isolate_hermes_home(tmp_path, monkeypatch):
    """Redirect HERMES_HOME to a temp dir so tests never write to ~/.hermes/."""
    fake_home = tmp_path / "hermes_test"
    fake_home.mkdir()
    (fake_home / "sessions").mkdir()
    (fake_home / "cron").mkdir()
    (fake_home / "memories").mkdir()
    (fake_home / "skills").mkdir()
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    # Reset plugin singleton so tests don't leak plugins
    try:
        import hermes_cli.plugins as _plugins_mod
        monkeypatch.setattr(_plugins_mod, "_plugin_manager", None)
    except Exception:
        pass
    # Clear gateway environment
    monkeypatch.delenv("HERMES_SESSION_PLATFORM", raising=False)
    monkeypatch.delenv("HERMES_SESSION_CHAT_ID", raising=False)
```

**Key fixtures:**
- `_isolate_hermes_home` (autouse): Redirects config to temp directory
- `tmp_dir`: Provides temporary directory
- `mock_config`: Minimal hermes config dict
- `_ensure_current_event_loop`: Provides event loop for sync tests
- `_enforce_test_timeout`: 30-second timeout per test (Unix only)

### Local Test Fixtures

```python
# From tests/test_run_agent.py (lines 45-62)
@pytest.fixture()
def agent():
    """Minimal AIAgent with mocked OpenAI client and tool loading."""
    with (
        patch(
            "run_agent.get_tool_definitions", return_value=_make_tool_defs("web_search")
        ),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        a = AIAgent(
            api_key="test-key-1234567890",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        a.client = MagicMock()
        return a
```

### Helper Functions

```python
# From tests/test_run_agent.py (lines 30-42)
def _make_tool_defs(*names: str) -> list:
    """Build minimal tool definition list accepted by AIAgent.__init__."""
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": f"{n} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for n in names
    ]
```

## Mocking Strategies

### unittest.mock Usage

- **MagicMock:** For mock objects that need to handle any attribute/method
- **AsyncMock:** For async functions
- **patch:** Context manager or decorator for mocking

```python
# From tests/test_run_agent.py (lines 48-54)
with (
    patch(
        "run_agent.get_tool_definitions", return_value=_make_tool_defs("web_search")
    ),
    patch("run_agent.check_toolset_requirements", return_value={}),
    patch("run_agent.OpenAI"),
):
```

### What to Mock

1. **External API clients:** OpenAI, Anthropic clients
2. **Tool loading:** `get_tool_definitions`
3. **File system:** HERMES_HOME redirected via fixture
4. **Environment variables:** Using `monkeypatch.setenv()` or `patch.dict()`
5. **Prompt_toolkit:** In CLI tests to avoid terminal dependency

```python
# From tests/test_cli_init.py (lines 30-48)
prompt_toolkit_stubs = {
    "prompt_toolkit": MagicMock(),
    "prompt_toolkit.history": MagicMock(),
    "prompt_toolkit.styles": MagicMock(),
    # ... more stubs
}
with patch.dict(sys.modules, prompt_toolkit_stubs), \
     patch.dict("os.environ", clean_env, clear=False):
```

### What NOT to Mock

- **Internal logic:** Test actual behavior when possible
- **Tool registry:** Tests verify actual tool registration
- **Config loading:** Tests verify config parsing works correctly

```python
# From tests/gateway/test_config.py (lines 13-21)
def test_to_dict_from_dict(self):
    hc = HomeChannel(platform=Platform.DISCORD, chat_id="999", name="general")
    d = hc.to_dict()
    restored = HomeChannel.from_dict(d)

    assert restored.platform == Platform.DISCORD
    assert restored.chat_id == "999"
    assert restored.name == "general"
```

## Fixtures and Test Data

### Mock Config

```python
# From tests/conftest.py (lines 50-64)
@pytest.fixture()
def mock_config():
    """Return a minimal hermes config dict suitable for unit tests."""
    return {
        "model": "test/mock-model",
        "toolsets": ["terminal", "file"],
        "max_turns": 10,
        "terminal": {
            "backend": "local",
            "cwd": "/tmp",
            "timeout": 30,
        },
        "compression": {"enabled": False},
        "memory": {"memory_enabled": False, "user_profile_enabled": False},
        "command_allowlist": [],
    }
```

### Test Data Creation

- **Inline data:** Simple dicts/lists in test functions
- **Factory functions:** `_make_tool_defs()` for creating tool definitions
- **Fixtures:** Reusable test data via `@pytest.fixture()`

## Coverage

### No Enforced Coverage Target

- No coverage requirement configured
- Manual coverage checks via `--cov` flag if needed

### Viewing Coverage

```bash
python -m pytest --cov=. --cov-report=html tests/
```

## Test Types

### Unit Tests

- **Scope:** Individual functions, classes, modules
- **Location:** `tests/test_*.py`, `tests/agent/`, `tests/tools/`
- **Example:** `tests/test_model_tools.py` tests tool dispatch

```python
# From tests/test_model_tools.py (lines 27-30)
def test_unknown_tool_returns_error(self):
    result = json.loads(handle_function_call("totally_fake_tool_xyz", {}))
    assert "error" in result
    assert "totally_fake_tool_xyz" in result["error"]
```

### Integration Tests

- **Marker:** `@pytest.mark.integration`
- **Location:** `tests/integration/`
- **Requirement:** External services (API keys, Modal, etc.)

```python
# From tests/integration/test_web_tools.py (marker required)
@pytest.mark.integration
def test_web_search_with_api_key(self):
    # Requires EXA_API_KEY
```

**Running integration tests:**
```bash
python -m pytest -m integration tests/
```

### Gateway Tests

- **Scope:** Messaging platform adapters
- **Location:** `tests/gateway/`
- **Pattern:** Test platform config, message handling, session management

### End-to-End Tests

- **Not extensively used:** Most "E2E" tests are integration tests
- **ACP tests:** `tests/acp/` for Agent Client Protocol

## Common Patterns

### Async Testing

```python
# From tests/conftest.py (lines 76-105)
@pytest.fixture(autouse=True)
def _ensure_current_event_loop(request):
    """Provide a default event loop for sync tests that call get_event_loop()."""
    if request.node.get_closest_marker("asyncio") is not None:
        yield
        return
    # ... event loop setup
```

### Error Testing

```python
# From tests/test_model_tools.py (lines 32-39)
def test_exception_returns_json_error(self):
    # Even if something goes wrong, should return valid JSON
    result = handle_function_call("web_search", None)  # None args may cause issues
    parsed = json.loads(result)
    assert isinstance(parsed, dict)
    assert "error" in parsed
```

### Fixture Isolation

Critical pattern: Every test gets isolated HERMES_HOME:
```python
# CRITICAL: Tests must not write to ~/.hermes/
# The _isolate_hermes_home fixture ensures this
```

### Test Timeout

30-second timeout prevents hanging tests:
```python
# From tests/conftest.py (lines 108-119)
@pytest.fixture(autouse=True)
def _enforce_test_timeout():
    if sys.platform == "win32":
        yield
        return
    # SIGALRM setup
```

## Test Isolation Principles

1. **HERMES_HOME isolation:** All tests use temp directory
2. **Environment variable cleanup:** Gateway env vars cleared
3. **Plugin singleton reset:** Prevents test leakage
4. **Test timeout:** 30-second max per test

---

*Testing analysis: 2026-03-29*
