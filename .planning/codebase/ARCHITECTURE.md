# Architecture

**Analysis Date:** 2026-03-29

## Pattern Overview

**Overall:** Event-driven agent loop with tool calling, supporting multiple entry points (CLI, messaging platforms via gateway, batch processing)

**Key Characteristics:**
- Synchronous agent loop in `run_agent.py` line 5976 (`run_conversation()` method) - iterates until no more tool calls or iteration budget exhausted
- Tool execution via `model_tools.py` which wraps the tool registry system
- Multi-platform support through gateway abstraction (telegram, discord, slack, etc.)
- State persistence via SQLite (`hermes_state.py`) with FTS5 full-text search
- Configuration-driven behavior via `~/.hermes/config.yaml`

## Layers

### Core Agent Layer (`run_agent.py`)

**Purpose:** Main agent implementation with tool-calling loop
**Location:** `run_agent.py` (8283 lines)
**Contains:**
- `AIAgent` class - primary agent implementation
- `run_conversation()` method (line 5976) - core loop
- `_execute_tool_calls()` (line 5203) - tool dispatch
- `_execute_tool_calls_sequential()` (line 5479) - sequential execution
- `_execute_tool_calls_concurrent()` (line 5290) - parallel execution

**Depends on:** `model_tools.py`, `agent/` package, `hermes_state.py`, `tools/` registry

**Used by:** `cli.py`, gateway platforms, `batch_runner.py`, RL environments

### Tool Orchestration Layer (`model_tools.py`)

**Purpose:** Thin orchestration over tool registry, provides public API
**Location:** `model_tools.py` (472 lines)
**Contains:**
- `get_tool_definitions()` - returns tool schemas for enabled toolsets
- `handle_function_call()` - dispatches to tool handlers
- `_run_async()` (line 81) - async/sync bridging for tool handlers
- `_discover_tools()` (line 132) - imports all tool modules to trigger registration

**Depends on:** `tools/registry.py`, `toolsets.py`

**Used by:** `run_agent.py`, `cli.py`, gateway, batch_runner, environments

### Tool Registry Layer (`tools/registry.py`)

**Purpose:** Central registry collecting tool schemas + handlers from tool files
**Location:** `tools/registry.py` (247 lines)
**Contains:**
- `ToolRegistry` class - singleton registry
- `register()` method (line 56) - tool registration at import time
- `get_definitions()` (line 94) - returns OpenAI-format schemas

**Depends on:** None (no imports - circular-import safe design)

**Used by:** All tool files in `tools/` directory

### Tool Implementation Layer (`tools/`)

**Purpose:** Individual tool implementations
**Location:** `tools/*.py` (40+ files)
**Contains:** Each file implements one or more tools, calls `registry.register()` at module level

**Key files:**
- `terminal_tool.py` - terminal command execution
- `file_tools.py` - file read/write/search/patch
- `web_tools.py` - web search and extraction
- `browser_tool.py` - browser automation
- `delegate_tool.py` - subagent delegation
- `mcp_tool.py` - MCP client integration (~1050 lines)

**Depends on:** `tools/registry.py`

**Used by:** `model_tools.py` via tool discovery

### Toolset Definition Layer (`toolsets.py`)

**Purpose:** Tool grouping and toolset resolution
**Location:** `toolsets.py` (629 lines)
**Contains:**
- `_HERMES_CORE_TOOLS` list (line 31) - core tool names
- `TOOLSETS` dict (line 72) - toolset definitions
- `resolve_toolset()` - resolve toolset to tool names

**Depends on:** None

**Used by:** `model_tools.py`, CLI, gateway

### Agent Internals Layer (`agent/`)

**Purpose:** Agent-related components extracted for modularity
**Location:** `agent/*.py` (20+ files)
**Contains:**
- `prompt_builder.py` (816 lines) - system prompt assembly, context file scanning
- `context_compressor.py` - conversation context compression
- `prompt_caching.py` - Anthropic prompt caching support
- `display.py` - KawaiiSpinner, tool preview formatting
- `model_metadata.py` - model context lengths, token estimation
- `auxiliary_client.py` - vision/summarization LLM client
- `trajectory.py` - trajectory saving helpers
- `skill_commands.py` - skill slash commands

**Depends on:** `run_agent.py`

**Used by:** `run_agent.py`

### CLI Layer (`cli.py` + `hermes_cli/`)

**Purpose:** Interactive terminal interface
**Location:** `cli.py` (7602 lines), `hermes_cli/` (20+ modules)
**Contains:**
- `HermesCLI` class in `cli.py` - main CLI orchestrator
- `load_cli_config()` (line 123) - configuration loading
- `commands.py` (737 lines) - slash command definitions
- `config.py` (2081 lines) - config management
- `banner.py` - ASCII art branding
- `skin_engine.py` - theming/skin system

**Depends on:** `run_agent.py`, `hermes_cli/config.py`, `hermes_cli/commands.py`

**Used by:** End users via CLI

### Gateway Layer (`gateway/`)

**Purpose:** Messaging platform integrations
**Location:** `gateway/run.py` (5924 lines), `gateway/platforms/` (multiple adapters)
**Contains:**
- `GatewayRunner` class in `gateway/run.py` - main gateway orchestrator
- Platform adapters in `gateway/platforms/`: telegram.py, discord.py, slack.py, whatsapp.py, signal.py, etc.
- `session.py` - conversation persistence for messaging
- `config.py` - gateway configuration

**Key platform adapter:** `gateway/platforms/base.py` (1476 lines)

**Depends on:** `run_agent.py` (creates AIAgent instances per message)

**Used by:** Messaging platform webhooks

### State Persistence Layer (`hermes_state.py`)

**Purpose:** SQLite session storage with FTS5 search
**Location:** `hermes_state.py` (1274 lines)
**Contains:**
- `SessionDB` class - SQLite wrapper
- Schema: sessions table, messages table, FTS5 virtual table
- `append_message()` - add messages to session
- `session_search()` - FTS5 search

**Depends on:** `hermes_constants.py`

**Used by:** `run_agent.py`, gateway, CLI

### Configuration Layer (`hermes_cli/config.py`)

**Purpose:** Configuration file management
**Location:** `hermes_cli/config.py` (2081 lines)
**Contains:**
- `DEFAULT_CONFIG` - default configuration values
- `OPTIONAL_ENV_VARS` - env var definitions
- Config loading, saving, migration functions
- Managed mode (NixOS) support

**Depends on:** `hermes_constants.py`, YAML

**Used by:** CLI, gateway, all modules

## Data Flow

### CLI Interaction Flow

```
User Input (cli.py)
  ↓
HermesCLI.process_command() - resolve and dispatch commands
  ↓
AIAgent.run_conversation() - main agent loop (run_agent.py:5976)
  ↓
API Call (OpenAI/Anthropic/OpenRouter/etc.)
  ↓
Response with tool_calls?
  ├─ No → Return final response
  └─ Yes → _execute_tool_calls() (run_agent.py:5203)
      ↓
    handle_function_call() (model_tools.py)
      ↓
    Tool Registry dispatch (tools/registry.py)
      ↓
    Tool implementation (tools/*.py)
      ↓
    Append tool result to messages
      ↓
    Continue loop (next API call)
```

### Gateway Messaging Flow

```
Platform Webhook (Telegram/Discord/etc.)
  ↓
GatewayRunner.dispatch() (gateway/run.py)
  ↓
Platform Adapter (gateway/platforms/telegram.py, etc.)
  ↓
Create new AIAgent instance (or continue session)
  ↓
AIAgent.run_conversation()
  ↓
Response via platform adapter
  ↓
Send to messaging platform
```

### Session Persistence Flow

```
AIAgent.run_conversation() completes
  ↓
_persist_session() (run_agent.py:1685)
  ├─ _save_session_log() - JSON log
  └─ _flush_messages_to_session_db() (run_agent.py:1695)
      ↓
    hermes_state.SessionDB.append_message()
      ↓
    SQLite with FTS5
```

## Key Abstractions

### Tool Registry Pattern

Each tool file calls `registry.register()` at module level:

```python
# tools/file_tools.py (example pattern)
from tools.registry import registry

def check_requirements() -> bool:
    return True

def read_file(path: str, ...) -> str:
    return json.dumps({"success": True, "content": "..."})

registry.register(
    name="read_file",
    toolset="terminal",
    schema={"name": "read_file", "description": "...", "parameters": {...}},
    handler=lambda args, **kw: read_file(...),
    check_fn=check_requirements,
)
```

Import chain: `tools/registry.py` → `tools/*.py` → `model_tools.py` → `run_agent.py`

### Toolset Resolution

Toolsets are defined in `toolsets.py` as dictionaries with tools and includes:

```python
# toolsets.py line 72
TOOLSETS = {
    "web": {
        "description": "Web research and content extraction tools",
        "tools": ["web_search", "web_extract"],
        "includes": []
    },
    "full_stack": {
        "description": "All tools",
        "tools": [],
        "includes": ["web", "terminal", "file", ...]
    },
}
```

### Slash Command Registry

Central registry in `hermes_cli/commands.py` line 46:

```python
COMMAND_REGISTRY: list[CommandDef] = [
    CommandDef("new", "Start a new session", "Session", aliases=("reset",)),
    CommandDef("background", "Run in background", "Session", aliases=("bg",)),
    # ... more commands
]
```

All consumers derive from this: CLI dispatch, gateway dispatch, Telegram BotCommands, Slack subcommands, autocomplete.

## Entry Points

### CLI Entry (`cli.py` line 1)

**Location:** `cli.py`
**Triggers:** `python cli.py` or `hermes` command
**Responsibilities:**
- Load configuration
- Initialize CLI (prompt_toolkit TUI)
- Process user input
- Invoke AIAgent

### Gateway Entry (`gateway/run.py` line 1)

**Location:** `gateway/run.py`
**Triggers:** `python -m gateway.run` or `python cli.py --gateway`
**Responsibilities:**
- Start all configured platform adapters
- Handle incoming webhooks
- Dispatch to AIAgent per message

### Batch Runner Entry (`batch_runner.py`)

**Location:** `batch_runner.py`
**Triggers:** `python batch_runner.py`
**Responsibilities:**
- Process multiple prompts in parallel
- Use same AIAgent infrastructure

## Error Handling

**Strategy:** Graceful degradation with retry logic

**Patterns:**
1. **API Retry** (run_agent.py:6418): Exponential backoff for transient failures
2. **Fallback Providers**: Switch to fallback model on rate limit (run_agent.py:7030)
3. **Context Compression**: Automatic compression on context length errors (run_agent.py:7124)
4. **Tool Validation**: Invalid tool names trigger self-correction (run_agent.py:7494)
5. **JSON Validation**: Invalid JSON args trigger retry or recovery (run_agent.py:7548)

## Cross-Cutting Concerns

**Logging:** Python standard `logging` module, configurable verbosity

**Validation:** Tool schemas validated at registration, tool names validated before execution

**Authentication:** Provider credentials resolved via `hermes_cli/auth.py`, env vars in `~/.hermes/.env`

**Session Management:** SQLite-backed with JSONL fallback, FTS5 search support

---

*Architecture analysis: 2026-03-29*
