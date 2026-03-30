# External Integrations

**Analysis Date:** 2026-03-29

## LLM Providers

**Direct API Access:**
- **Anthropic** - Claude models via `api.anthropic.com`
  - Env vars: `ANTHROPIC_API_KEY`, `ANTHROPIC_TOKEN` (`hermes_cli/config.py` lines 152-158)
  - SDK: `anthropic` Python package

- **OpenAI** - GPT models via `api.openai.com`
  - Env vars: `OPENAI_API_KEY`, `OPENAI_BASE_URL` (`hermes_cli/config.py` lines 30-31)
  - SDK: `openai` Python package

**AI Gateways & Alternative Providers:**
- **OpenRouter** - Aggregation layer for multiple providers
  - Env vars: `OPENROUTER_API_KEY` (`hermes_cli/config.py` lines 466-474)
  - URL: `https://openrouter.ai/api/v1`
  - Used for: Vision, web scraping helpers, MoA

- **Nous Portal** - Nous Research's inference API
  - Auth: OAuth device code flow (`hermes_cli/auth.py` lines 61-67)
  - Default URL: `https://inference-api.nousresearch.com/v1`

- **OpenAI Codex** - OpenAI's coding model
  - Auth: OAuth external flow (`hermes_cli/auth.py` lines 108-113)
  - URL: `https://chatgpt.com/backend-api/codex`

- **GitHub Copilot** - Via `api.githubcopilot.com`
  - Auth: `COPILOT_GH_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` (`hermes_cli/auth.py` lines 114-127)
  - Alternative: ACP (Agent Client Protocol) via `acp://copilot`

- **Z.AI / GLM** - Chinese AI provider
  - Env vars: `GLM_API_KEY`, `ZAI_API_KEY`, `Z_AI_API_KEY` (`hermes_cli/auth.py` lines 128-135)
  - URL: `https://api.z.ai/api/paas/v4`

- **Kimi / Moonshot** - Chinese LLM provider
  - Env vars: `KIMI_API_KEY` (`hermes_cli/auth.py` lines 136-143)
  - URL: `https://api.moonshot.ai/v1`

- **MiniMax** - Chinese AI company
  - Env vars: `MINIMAX_API_KEY`, `MINIMAX_CN_API_KEY` (`hermes_cli/auth.py` lines 144-174)
  - URLs: `https://api.minimax.io/anthropic` (international), `https://api.minimaxi.com/anthropic` (China)

- **DeepSeek** - DeepSeek's models
  - Env vars: `DEEPSEEK_API_KEY` (`hermes_cli/auth.py` lines 175-182)
  - URL: `https://api.deepseek.com/v1`

- **Alibaba DashScope** - Alibaba's Qwen models
  - Env vars: `DASHSCOPE_API_KEY` (`hermes_cli/auth.py` lines 159-166)
  - URL: `https://coding-intl.dashscope.aliyuncs.com/v1`

- **OpenCode Zen/Go** - OpenCode's curated models
  - Env vars: `OPENCODE_ZEN_API_KEY`, `OPENCODE_GO_API_KEY` (`hermes_cli/auth.py` lines 191-215)
  - URLs: `https://opencode.ai/zen/v1`, `https://opencode.ai/go/v1`

- **Hugging Face** - Inference providers
  - Env vars: `HF_TOKEN` (`hermes_cli/auth.py` lines 216-222)
  - URL: `https://router.huggingface.co`

## Web Search & Scraping

**Search APIs:**
- **Exa** - AI-native web search
  - Env vars: `EXA_API_KEY` (`hermes_cli/config.py` lines 633-640)
  - URL: `https://exa.ai/`
  - Tools: `web_search`, `web_extract`

- **Firecrawl** - Web scraping and search
  - Env vars: `FIRECRAWL_API_KEY`, `FIRECRAWL_API_URL` (`hermes_cli/config.py` lines 649-664)
  - URL: `https://firecrawl.dev/`
  - Tools: `web_search`, `web_extract`, `web_crawl`

- **Parallel** - AI-native web operations
  - Env vars: `PARALLEL_API_KEY` (`hermes_cli/config.py` lines 641-648)
  - URL: `https://parallel.ai/`

- **Tavily** - AI search engine
  - Env vars: `TAVILY_API_KEY` (`hermes_cli/config.py` lines 665-672)
  - URL: `https://app.tavily.com/home`

## Browser Automation

**Cloud Browser:**
- **Browserbase** - Cloud headless browser service
  - Env vars: `BROWSERBASE_API_KEY`, `BROWSERBASE_PROJECT_ID`, `BROWSERBASE_PROXIES` (`tools/browser_tool.py` lines 28-37)
  - URL: `https://browserbase.com/`
  - Features: Stealth mode, residential proxies, session management

- **Browser Use** - Alternative cloud browser
  - Env vars: `BROWSER_USE_API_KEY` (`hermes_cli/config.py` lines 689-696)
  - URL: `https://browser-use.com/`

**Local Browser:**
- **agent-browser** CLI - Self-hosted headless Chromium
  - Installation: `agent-browser install` or `agent-browser install --with-deps`
  - No API key required

## Messaging Platforms

**Telegram:**
- Library: `python-telegram-bot` (`gateway/platforms/telegram.py` lines 18-29)
- Env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS` (`hermes_cli/config.py` lines 760-773)
- Setup: Via @BotFather

**Discord:**
- Library: `discord.py` (`gateway/platforms/discord.py`)
- Env vars: `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USERS` (`hermes_cli/config.py` lines 774-787)
- Setup: Discord Developer Portal

**Slack:**
- Libraries: `slack-bolt`, `slack-sdk` (`gateway/platforms/slack.py`)
- Env vars: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN` (`hermes_cli/config.py` lines 788-805)
- Scopes required: `chat:write`, `app_mentions:read`, `channels:history`, etc.

**Mattermost:**
- Env vars: `MATTERMOST_URL`, `MATTERMOST_TOKEN`, `MATTERMOST_ALLOWED_USERS` (`hermes_cli/config.py` lines 806-840)
- URL: `https://mattermost.com/deploy/`

**Matrix:**
- Library: `matrix-nio` (`gateway/platforms/matrix.py`)
- Env vars: `MATRIX_HOMESERVER`, `MATRIX_ACCESS_TOKEN`, `MATRIX_USER_ID` (`hermes_cli/config.py` lines 841-868)
- Protocol: `https://matrix.org/ecosystem/servers/`

**Signal:**
- Env vars: `SIGNAL_ACCOUNT`, `SIGNAL_HTTP_URL`, `SIGNAL_ALLOWED_USERS`, `SIGNAL_GROUP_ALLOWED_USERS` (`hermes_cli/config.py` lines 34-35)
- Implementation: `gateway/platforms/signal.py`

**WhatsApp:**
- Env vars: `WHATSAPP_MODE`, `WHATSAPP_ENABLED` (`hermes_cli/config.py` line 38)
- Implementation: `gateway/platforms/whatsapp.py`

**SMS:**
- Implementation: `gateway/platforms/sms.py`

**Email:**
- Implementation: `gateway/platforms/email.py`

**Home Assistant:**
- Implementation: `gateway/platforms/homeassistant.py`
- Optional deps: `aiohttp>=3.9.0,<4`

**DingTalk:**
- Library: `dingtalk-stream` (optional dependency)
- Env vars: `DINGTALK_CLIENT_ID`, `DINGTALK_CLIENT_SECRET` (`hermes_cli/config.py` line 36)
- Implementation: `gateway/platforms/dingtalk.py`

## MCP (Model Context Protocol)

**MCP Servers:**
- Configuration: `~/.hermes/config.yaml` under `mcp_servers` key (`tools/mcp_tool.py` lines 14-43)
- Transport: Stdio (command + args) or HTTP/StreamableHTTP (url)
- Package: `mcp>=1.2.0,<2` (optional dependency)

**Popular MCP Servers:**
- `@modelcontextprotocol/server-filesystem` - File system access
- `@modelcontextprotocol/server-github` - GitHub API access
- Custom servers via `url` + `headers` configuration

## Cloud Execution Environments

**Modal:**
- Package: `modal>=1.0.0,<2` (`tools/environments/modal.py`)
- Purpose: Cloud sandbox for code execution
- Features: Persistent filesystem snapshots, native SDK integration

**Daytona:**
- Package: `daytona>=0.148.0,<1` (`tools/environments/daytona.py`)
- Purpose: Cloud development environments

**Docker:**
- Local execution: `tools/environments/docker.py`
- Requires: Docker daemon running

**SSH:**
- Remote execution: `tools/environments/ssh.py`
- Env vars: `TERMINAL_SSH_KEY`, `TERMINAL_SSH_PORT` (`hermes_cli/config.py` line 37)

## Voice & Audio

**Text-to-Speech:**
- **Edge TTS** (default, free) - Microsoft Edge's TTS engine
- **ElevenLabs** (premium) - `ELEVENLABS_API_KEY` (`hermes_cli/config.py` lines 729-735)
- **OpenAI TTS** - `VOICE_TOOLS_OPENAI_KEY` (`hermes_cli/config.py` lines 721-728)

**Speech-to-Text:**
- **Faster Whisper** (local, free) - `faster-whisper>=1.0.0,<2`
- **Groq** (free API) - Auto-detected fallback
- **OpenAI Whisper** (paid API) - Requires `VOICE_TOOLS_OPENAI_KEY`

**Audio Playback:**
- Package: `sounddevice>=0.4.6,<1`
- Used by: `tools/voice_mode.py`

## Image Generation

**FAL.ai:**
- Package: `fal-client` (`pyproject.toml` line 32)
- Env vars: `FAL_KEY` (`hermes_cli/config.py` lines 697-704)
- URL: `https://fal.ai/`
- Tool: `image_generate`

## RL/Training

**Tinker:**
- Env vars: `TINKER_API_KEY` (`hermes_cli/config.py` lines 705-712)
- URL: `https://tinker-console.thinkingmachines.ai/keys`
- Tool: `rl_start_training`, `rl_check_status`, `rl_stop_training`

**Weights & Biases:**
- Env vars: `WANDB_API_KEY` (`hermes_cli/config.py` lines 713-720)
- URL: `https://wandb.ai/authorize`
- Tools: `rl_get_results`, `rl_check_status`

**Atropos:**
- Source: `git+https://github.com/NousResearch/atropos.git`
- Purpose: RL training environments

## Memory & Persistence

**Honcho:**
- Env vars: `HONCHO_API_KEY`, `HONCHO_BASE_URL` (`hermes_cli/config.py` lines 744-757)
- URL: `https://app.honcho.dev`
- Purpose: AI-native persistent memory

## Monitoring & Observability

**Logging:**
- Built-in Python logging (`logging` module)
- Debug output: `~/.hermes/logs/` directory

**Error Tracking:**
- Not integrated (relies on provider error responses)

## CI/CD & Deployment

**Development:**
- Local execution via `hermes` CLI command
- Config: `~/.hermes/config.yaml`

**Gateway Mode:**
- Messaging platform bots (Telegram, Discord, Slack, etc.)
- API server mode: `API_SERVER_ENABLED`, `API_SERVER_PORT`, `API_SERVER_KEY` (`hermes_cli/config.py` lines 877-908)
- Webhook server: `WEBHOOK_ENABLED`, `WEBHOOK_PORT`, `WEBHOOK_SECRET` (`hermes_cli/config.py` lines 909-929)

## Environment Configuration

**Required env vars:**
- `ANTHROPIC_API_KEY` or other LLM provider API key

**Common optional env vars:**
- Provider keys: `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, etc.
- Tool keys: `FIRECRAWL_API_KEY`, `EXA_API_KEY`, `BROWSERBASE_API_KEY`, `FAL_KEY`
- Messaging: `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, `SLACK_BOT_TOKEN`
- Voice: `ELEVENLABS_API_KEY`, `VOICE_TOOLS_OPENAI_KEY`

**Config locations:**
- Main config: `~/.hermes/config.yaml`
- Secrets: `~/.hermes/.env`
- Session DB: `~/.hermes/state.db`

---

*Integration audit: 2026-03-29*
