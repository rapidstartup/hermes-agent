# Technology Stack

**Analysis Date:** 2026-03-29

## Languages

**Primary:**
- Python 3.11+ - Core runtime for all agent functionality
- Requirements file: `requirements.txt` lines 1-35, `pyproject.toml` lines 1-104

**Secondary:**
- Shell scripts - Terminal tool backends
- YAML - Configuration files (`~/.hermes/config.yaml`)
- JSON - State storage, API responses

## Runtime

**Environment:**
- Python 3.11+ (specified in `pyproject.toml` line 10)
- Supports Linux, macOS, Windows (platform-specific dependencies in `pyproject.toml` lines 51-54)

**Package Manager:**
- pip with setuptools (build-backend: `setuptools.build_meta`)
- Lockfile: Not committed (relies on version constraints in pyproject.toml)
- Installation: `pip install -e ".[all]"` for full dependencies

## Frameworks

**Core:**
- OpenAI SDK (`openai>=2.21.0,<3`) - Primary LLM client for GPT models and OpenAI-compatible APIs
- Anthropic SDK (`anthropic>=0.39.0,<1`) - Claude model access
- Pydantic (`pydantic>=2.12.5,<3`) - Data validation and settings management

**CLI/Interactive:**
- prompt_toolkit (`>=3.0.52,<4`) - Interactive CLI input with autocomplete (`cli.py` line 12)
- Rich (`>=14.3.3,<15`) - Terminal UI formatting, panels, spinners (`hermes_cli/banner.py`)
- Fire (`>=0.7.1,<1`) - CLI argument parsing

**Data & Config:**
- PyYAML (`>=6.0.2,<7`) - Configuration file parsing
- python-dotenv (`>=1.2.1,<2`) - Environment variable loading from `.env`
- Jinja2 (`>=3.1.5,<4`) - Template rendering

**HTTP & Networking:**
- httpx (`>=0.28.1,<1`) - Async HTTP client for API calls (`tools/web_tools.py` line 45)
- requests (`>=2.33.0,<3`) - Synchronous HTTP client

**Testing:**
- pytest (`>=9.0.2,<10`) - Test framework
- pytest-asyncio (`>=1.3.0,<2`) - Async test support
- pytest-xdist (`>=3.0,<4`) - Parallel test execution

**Authentication:**
- PyJWT (`>=2.12.0,<3`) - JWT token handling for OAuth/device code flows

## Key Dependencies

**LLM/AI Providers:**
- openai - Primary SDK for OpenAI models, OpenRouter, and OpenAI-compatible APIs
- anthropic - Claude model access via official SDK
- exa-py (`>=2.9.0,<3`) - AI-native web search (`hermes_cli/config.py` line 633)
- fal-client (`>=0.13.1,<1`) - Image generation via FAL.ai (`tools/web_tools.py`, `pyproject.toml` line 32)

**Web Tools:**
- firecrawl-py (`>=4.16.0,<5`) - Web scraping, search, content extraction (`tools/web_tools.py` line 46)
- parallel-web (`>=0.4.2,<1`) - Parallel web operations

**Voice/Audio:**
- edge-tts (`>=7.2.7,<8`) - Free Microsoft Edge text-to-speech (no API key required)
- faster-whisper (`>=1.0.0,<2`) - Local Whisper STT
- elevenlabs (`>=1.0,<2`) - Premium TTS voices (optional)
- sounddevice (`>=0.4.6,<1`) - Audio playback for voice mode
- numpy (`>=1.24.0,<3`) - Audio processing

**Browser Automation:**
- agent-browser - CLI tool for headless Chromium (installed separately, not a Python package)
- Browserbase SDK - Cloud browser service (optional, requires `BROWSERBASE_API_KEY`)

**Messaging Platforms:**
- python-telegram-bot (`>=22.6,<23`) - Telegram bot integration (`gateway/platforms/telegram.py` line 19)
- discord.py (`>=2.7.1,<3`) - Discord bot integration (`gateway/platforms/discord.py`)
- slack-bolt (`>=1.18.0,<2`) - Slack bot framework (`gateway/platforms/slack.py`)
- slack-sdk (`>=3.27.0,<4`) - Slack API client
- matrix-nio (`>=0.24.0,<1`) - Matrix protocol client

**Cloud Execution:**
- modal (`>=1.0.0,<2`) - Cloud sandbox execution (`tools/environments/modal.py`)
- daytona (`>=0.148.0,<1`) - Cloud development environments
- docker - Local container execution (`tools/environments/docker.py`)

**RL/Training:**
- Atropos library (git+https) - RL training environments
- Tinker (git+https) - RL training framework
- wandb (`>=0.15.0,<1`) - Weights & Biases experiment tracking

**Other Tools:**
- tenacity (`>=9.1.4,<10`) - Retry logic
- croniter (`>=6.0.0,<7`) - Cron expression parsing (`cron/scheduler.py`)
- mcp (`>=1.2.0,<2`) - Model Context Protocol client (`tools/mcp_tool.py` line 776)
- agent-client-protocol (`>=0.8.1,<0.9`) - VS Code/Zed/JetBrains ACP adapter (`acp_adapter/server.py`)

## Database & Storage

**Primary:**
- SQLite with FTS5 - Session state storage (`hermes_state.py` lines 22, 60-75)
  - Database path: `~/.hermes/state.db` (configurable via `DEFAULT_DB_PATH`)
  - Schema version tracked: `SCHEMA_VERSION = 6` (line 35)
  - Features: WAL mode for concurrent access, FTS5 full-text search

**File Storage:**
- Local filesystem: `~/.hermes/` directory structure
  - `config.yaml` - User configuration
  - `.env` - API keys and secrets
  - `sessions/` - Session history
  - `logs/` - Debug logs
  - `memories/` - Persistent memory storage
  - `skills/` - User-installed skills
  - `cron/` - Scheduled job configs

## Configuration

**Environment:**
- YAML: `~/.hermes/config.yaml` for settings
- .env: `~/.hermes/.env` for API keys and secrets
- Environment variables: Loaded via python-dotenv
- Config loading: `load_cli_config()` in `cli.py`, `load_config()` in `hermes_cli/config.py`

**Key config files:**
- `pyproject.toml` - Project metadata and dependencies
- `hermes_cli/config.py` - Default configuration (`DEFAULT_CONFIG` starting line 136)
- `hermes_cli/auth.py` - Multi-provider authentication system (lines 1-100)

## Platform Requirements

**Development:**
- Python 3.11+
- pip for package management
- Git for version control

**Production:**
- Compatible with Linux servers, macOS, Windows
- Optional: Docker, Modal SDK, Daytona for cloud execution
- Optional: Browserbase account for cloud browser automation

---

*Stack analysis: 2026-03-29*
