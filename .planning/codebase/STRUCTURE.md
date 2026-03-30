# Codebase Structure

**Analysis Date:** 2026-03-29

## Directory Layout

```
hermes-agent/
├── run_agent.py              # Core AIAgent class (~8300 lines)
├── model_tools.py            # Tool orchestration (~470 lines)
├── toolsets.py               # Toolset definitions (~630 lines)
├── cli.py                    # CLI entry point (~7600 lines)
├── batch_runner.py           # Batch processing
├── hermes_state.py           # SQLite session store (~1270 lines)
├── hermes_constants.py       # Shared constants (no deps)
│
├── agent/                    # Agent internals
│   ├── prompt_builder.py     # System prompt assembly (~820 lines)
│   ├── context_compressor.py # Context compression
│   ├── prompt_caching.py    # Anthropic prompt caching
│   ├── display.py           # KawaiiSpinner, tool formatting
│   ├── model_metadata.py    # Model context lengths
│   ├── auxiliary_client.py  # Vision/summarization LLM
│   ├── trajectory.py        # Trajectory saving
│   ├── skill_commands.py    # Skill slash commands
│   └── ...                  # Other agent modules
│
├── hermes_cli/               # CLI subcommands and setup (~30 modules)
│   ├── main.py              # Entry point - all `hermes` subcommands
│   ├── config.py            # DEFAULT_CONFIG, env var definitions (~2080 lines)
│   ├── commands.py          # Slash command definitions (~740 lines)
│   ├── callbacks.py         # Terminal callbacks (clarify, sudo)
│   ├── setup.py             # Interactive setup wizard
│   ├── skin_engine.py       # Skin/theme engine
│   ├── skills_config.py     # Skill enable/disable per platform
│   ├── tools_config.py      # Tool enable/disable per platform
│   ├── auth.py              # Provider credential resolution
│   └── ...                  # Other CLI modules
│
├── tools/                    # Tool implementations (~40 files)
│   ├── registry.py           # Central tool registry (~250 lines)
│   ├── terminal_tool.py      # Terminal orchestration
│   ├── file_tools.py         # File read/write/search/patch
│   ├── web_tools.py          # Web search/extract
│   ├── browser_tool.py       # Browser automation
│   ├── code_execution_tool.py # execute_code sandbox
│   ├── delegate_tool.py      # Subagent delegation
│   ├── mcp_tool.py           # MCP client (~1050 lines)
│   ├── memory_tool.py       # Memory persistence
│   ├── todo_tool.py          # Todo list management
│   ├── skills_tool.py        # Skill management
│   └── environments/        # Terminal backends (local, docker, ssh, etc.)
│
├── gateway/                  # Messaging platform gateway
│   ├── run.py               # Main gateway loop (~5920 lines)
│   ├── session.py           # SessionStore for messaging
│   ├── config.py            # Gateway config
│   └── platforms/           # Platform adapters
│       ├── base.py          # Base adapter class (~1480 lines)
│       ├── telegram.py     # Telegram adapter
│       ├── discord.py       # Discord adapter
│       ├── slack.py         # Slack adapter
│       ├── whatsapp.py      # WhatsApp adapter
│       ├── signal.py        # Signal adapter
│       └── ...              # Other platforms
│
├── environments/             # RL training environments
├── cron/                     # Scheduler
├── acp_adapter/              # ACP server (VS Code/Zed integration)
├── honcho_integration/       # Honcho memory integration
└── tests/                    # Pytest suite (~3000 tests)
```

## Directory Purposes

### Root Level (`hermes-agent/`)

**Purpose:** Primary entry points and core agent logic
**Contains:**
- `run_agent.py` - Main AIAgent class
- `model_tools.py` - Tool orchestration
- `toolsets.py` - Toolset definitions
- `cli.py` - CLI entry point
- `hermes_state.py` - Session persistence
- `hermes_constants.py` - Shared constants

**Key files:**
- `run_agent.py:5976` - `run_conversation()` method
- `model_tools.py:132` - `_discover_tools()` function
- `toolsets.py:31` - `_HERMES_CORE_TOOLS` list
- `hermes_state.py:33` - `DEFAULT_DB_PATH`

### `agent/` Directory

**Purpose:** Agent internals extracted for modularity
**Contains:** Prompt building, context compression, display, metadata

**Key files:**
- `agent/prompt_builder.py:1` - System prompt assembly
- `agent/context_compressor.py:1` - Context compression logic
- `agent/display.py:1` - KawaiiSpinner, tool formatting

### `hermes_cli/` Directory

**Purpose:** CLI implementation, configuration, commands
**Contains:** 30+ modules for CLI functionality

**Key files:**
- `hermes_cli/main.py:1` - CLI entry point (hermes subcommands)
- `hermes_cli/config.py:1` - Configuration management
- `hermes_cli/commands.py:46` - COMMAND_REGISTRY

### `tools/` Directory

**Purpose:** Tool implementations
**Contains:** 40+ tool files, each implements one or more tools

**Key files:**
- `tools/registry.py:45` - ToolRegistry class
- `tools/terminal_tool.py` - Terminal execution
- `tools/file_tools.py` - File operations
- `tools/web_tools.py` - Web search/extract

### `gateway/` Directory

**Purpose:** Messaging platform integrations
**Contains:** Gateway runner, session management, platform adapters

**Key files:**
- `gateway/run.py:1` - Gateway runner
- `gateway/platforms/base.py:1` - Base platform adapter

### `gateway/platforms/` Directory

**Purpose:** Individual platform adapters
**Contains:** Telegram, Discord, Slack, WhatsApp, Signal, etc.

## Key File Locations

### Entry Points

- `cli.py:1` - CLI mode: `python cli.py` or `hermes`
- `gateway/run.py:1` - Gateway mode: `python -m gateway.run`
- `run_agent.py:5976` - Agent loop: `AIAgent.run_conversation()`

### Configuration

- `hermes_cli/config.py:43` - `DEFAULT_CONFIG` dict
- `hermes_cli/config.py:26` - `OPTIONAL_ENV_VARS` dict
- `~/.hermes/config.yaml` - User configuration file
- `~/.hermes/.env` - API keys and secrets

### Tool System

- `tools/registry.py:56` - `registry.register()` method
- `model_tools.py:132` - Tool discovery function
- `toolsets.py:31` - Core tool definitions

### State

- `hermes_state.py:33` - SQLite database path
- `hermes_state.py:37` - Database schema SQL

## Naming Conventions

### Files

- **Modules:** `snake_case.py` (e.g., `model_tools.py`, `prompt_builder.py`)
- **CLI modules:** `snake_case.py` (e.g., `tools_config.py`, `skills_config.py`)
- **Platform adapters:** `platform_name.py` (e.g., `telegram.py`, `discord.py`)

### Functions/Methods

- **Public API:** `snake_case` (e.g., `get_tool_definitions()`, `run_conversation()`)
- **Internal:** `_leading_underscore` (e.g., `_discover_tools()`, `_execute_tool_calls()`)
- **Classes:** `PascalCase` (e.g., `AIAgent`, `ToolRegistry`, `SessionDB`)

### Constants

- **Module-level:** `UPPER_SNAKE_CASE` (e.g., `_HERMES_CORE_TOOLS`, `OPENROUTER_BASE_URL`)
- **Configuration:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONFIG`)

## Where to Add New Code

### New Tool

1. Create `tools/new_tool.py`
2. Call `registry.register()` at module level
3. Add import to `model_tools.py:_discover_tools()` list (line 138)
4. Add to `toolsets.py` in `_HERMES_CORE_TOOLS` or new toolset

Example structure:
```python
# tools/new_tool.py
from tools.registry import registry
import json

def check_requirements() -> bool:
    return True  # or check for env var

def new_tool(param: str, task_id: str = None) -> str:
    return json.dumps({"success": True, "data": "..."})

registry.register(
    name="new_tool",
    toolset="my_toolset",
    schema={"name": "new_tool", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: new_tool(param=args.get("param", ""), task_id=kw.get("task_id")),
    check_fn=check_requirements,
    requires_env=["MY_API_KEY"],
)
```

### New Slash Command

1. Add `CommandDef` entry to `hermes_cli/commands.py:COMMAND_REGISTRY` (line 46)
2. Add handler in `cli.py:HermesCLI.process_command()`
3. If gateway-only, add handler in `gateway/run.py`

### New Messaging Platform

1. Create `gateway/platforms/new_platform.py`
2. Inherit from `gateway/platforms/base.py:PlatformAdapter`
3. Implement required methods
4. Register in `gateway/config.py:PLATFORMS` dict

### New Configuration Option

1. Add to `DEFAULT_CONFIG` in `hermes_cli/config.py:43`
2. Bump `_config_version` (currently 5) to trigger migration
3. Add to `OPTIONAL_ENV_VARS` in `hermes_cli/config.py:26` if env var

## File Dependency Chain

```
hermes_constants.py          # No deps - import-safe
       ↑
tools/registry.py            # No deps
       ↑
tools/*.py                  # Import registry
       ↑
model_tools.py              # Import registry + tools
       ↑
run_agent.py                # Import model_tools + agent/*
       ↑
cli.py / gateway/run.py    # Import run_agent + hermes_cli/*
```

### Detailed Import Chain

```python
# hermes_constants.py - No imports (base module)

# tools/registry.py - No imports

# tools/web_tools.py
from tools.registry import registry

# model_tools.py (line 29-30)
from tools.registry import registry
from toolsets import resolve_toolset, validate_toolset

# run_agent.py (line 65-103)
from model_tools import get_tool_definitions, handle_function_call
from agent.prompt_builder import ...
from agent.context_compressor import ContextCompressor

# cli.py (line 60-75)
from agent.usage_pricing import ...
from hermes_cli.banner import ...
from hermes_constants import get_hermes_home, OPENROUTER_BASE_URL
from hermes_cli.env_loader import load_hermes_dotenv

# hermes_cli/commands.py - No imports from other hermes modules

# hermes_cli/config.py (line 43)
import yaml
from hermes_cli.colors import Colors
from hermes_cli.default_soul import DEFAULT_SOUL_MD

# gateway/run.py (line 84-100)
from dotenv import load_dotenv
from hermes_cli.env_loader import load_hermes_dotenv
from hermes_cli.config import _expand_env_vars
```

## CLI vs Gateway vs Tool Separation

### CLI Mode (`cli.py`)

- Interactive TUI with prompt_toolkit
- Single-user, single-session
- Direct stdin/stdout
- Rich display (KawaiiSpinner, banners)
- Commands via `/slash` syntax

### Gateway Mode (`gateway/run.py`)

- Long-running server process
- Multi-user, multi-session (one AIAgent per message)
- Webhook-based (HTTP)
- Platform adapters for each messaging service
- Session continuation via session_id

### Tool System (standalone)

- Can be used by CLI, gateway, batch_runner, RL environments
- No direct dependency on CLI or gateway
- Tools return JSON strings
- Parallel or sequential execution based on tool safety

### Shared Components

- `hermes_cli/config.py` - Configuration loading (used by CLI and gateway)
- `hermes_state.py` - Session persistence (used by CLI and gateway)
- `model_tools.py` - Tool API (used by all)
- `toolsets.py` - Toolset definitions (used by all)

---

*Structure analysis: 2026-03-29*
