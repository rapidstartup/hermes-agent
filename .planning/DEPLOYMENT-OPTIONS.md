# Hermes Agent - Deployment Options

## Executive Summary

This document evaluates hosting options for hermes-agent and outlines a phased multi-tenant deployment strategy using Railway.

---

## 1. Hosting Platform Analysis

### Requirements Summary

| Requirement | Details |
|-------------|---------|
| Runtime | Python 3.11+ |
| Node.js | Required (playwright, messaging platforms) |
| Persistence | SQLite with FTS5 (`~/.hermes/`) |
| File System | Config, memory, skills, sessions |
| Terminal Backends | local, docker, ssh, modal, daytona, singularity |

### Platform Comparison

| Platform | Support | Notes |
|----------|---------|-------|
| **Railway** | ✅ Native | Persistent volumes, already common for this project |
| **Modal** | ✅ Native | Built-in sleep/wake, cheapest idle costs |
| **Daytona** | ✅ Native | Same sleep/wake as Modal |
| **VPS/VM** | ✅ Native | $5 VPS (Hetzner, DigitalOcean, Linode) |
| **Vercel** | ⚠️ Hard | Python supported but: no persistent filesystem, 10s timeout, no long-running processes |
| **Netlify** | ⚠️ Hard | Same issues as Vercel |
| **Cloudflare Workers** | ❌ No | Python not supported, no arbitrary execution |
| **Cloudflare Pages** | ❌ No | No Python runtime |

### Selected Platform: Railway

**Rationale:**
- Already has Dockerfile in repo (`Dockerfile`)
- Persistent volumes for SQLite/filestore
- Supports long-running processes (not serverless functions)
- $5/mo Hobby plan covers 6 replicas
- Team familiarity with platform

---

## 2. Railway Deployment Specs

### Resource Allocation

| Plan | RAM | vCPU | Max Replicas | Volume | Monthly Cost |
|------|-----|------|--------------|--------|--------------|
| **Hobby** | 48 GB | 48 | 6 | 5 GB | $5 + overages |
| **Pro** | 1 TB | 1,000 | 42 | 1 TB | $20 + overages |

### Per-Agent Resource Estimates

| State | RAM | CPU |
|-------|-----|-----|
| Idle | 100-200 MB | ~0 |
| Thinking | 500 MB - 1 GB | 0.5-1 vCPU |
| With Browser | +1-2 GB | +0.5 vCPU |

### Capacity Estimates

| Plan | Concurrent Active Agents | Notes |
|------|---------------------------|-------|
| Hobby | ~6 | With browser tool, ~3-4 |
| Pro | ~40+ | With browser tool, ~20+ |

### Deployment Configuration

```dockerfile
# Already exists at ./Dockerfile
FROM debian:13.4
RUN apt-get install -y nodejs npm python3 python3-pip ripgrep ffmpeg gcc python3-dev libffi-dev
COPY . /opt/hermes
WORKDIR /opt/hermes
RUN pip install -e ".[all]" --break-system-packages
RUN npm install && npx playwright install --with-deps chromium
ENV HERMES_HOME=/opt/data
# No Dockerfile VOLUME — Railway forbids it; attach a Railway volume at /opt/data instead.
ENTRYPOINT [ "/opt/hermes/docker/entrypoint.sh" ]
CMD [ "gateway", "run" ]
```

**Railway Environment Variables Required:**
- `HERMES_HOME=/opt/data` (persistent volume mount)
- `ANTHROPIC_API_KEY` (or per-user via config)
- `OPENAI_API_KEY` (or per-user via config)
- `TELEGRAM_BOT_TOKEN` (per instance)
- `DISCORD_BOT_TOKEN` (per instance)
- `SLACK_BOT_TOKEN` (per instance)

---

## 3. Authentication Model

### Current Architecture

```
gateway/session.py:87   - user_id per session
gateway/run.py:1460    - _is_user_authorized() with allowlists
gateway/run.py:406     - DM pairing store for code-based auth
```

### Supported Auth Flows

| Platform | Auth Method | Implementation |
|----------|-------------|----------------|
| Telegram | Bot token + user_id | Platform-native |
| Discord | Bot token + user_id | Platform-native |
| Slack | Bot token + user_id | Platform-native |
| WhatsApp | Phone number | Platform-native |
| Signal | UUID | Platform-native |
| Custom | Allowlist | `security.authorized_users` config |
| Custom | DM pairing | User sends pairing code |

### Auth Gaps for SaaS

| Component | Current State | Required for SaaS |
|-----------|--------------|-------------------|
| User registration | ❌ | Signup flow |
| API key management | ❌ | Per-user keys |
| Config isolation | ⚠️ Partial | User-scoped config |
| Billing integration | ❌ | Stripe/usage |
| Usage metering | ❌ | Per-user tracking |
| User dashboard | ❌ | Web UI |

---

## 4. Phased Multi-Tenant Strategy

### Phase 1: Single Instance (MVP)

**Timeline:** Week 1-2

**Architecture:**
```
┌─────────────────────────────────────────┐
│           Railway Service               │
│  ┌─────────────────────────────────┐   │
│  │     Hermes Gateway + Agent      │   │
│  │                                 │   │
│  │  Sessions keyed by:             │   │
│  │  {platform}:{user_id}           │   │
│  │                                 │   │
│  │  Config: shared, per-user opts  │   │
│  └─────────────────────────────────┘   │
│                  │                      │
│                  ▼                      │
│  ┌─────────────────────────────────┐   │
│  │     SQLite + Volume Mount       │   │
│  │     /opt/data                   │   │
│  │     - sessions/                 │   │
│  │     - config.yaml               │   │
│  │     - memory/                   │   │
│  │     - skills/                   │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

**Deployment Steps:**
1. Push to Railway with persistent volume
2. Configure platform bot tokens (Telegram/Discord/Slack)
3. Set allowlist or enable DM pairing
4. Users connect via their preferred platform
5. Each user gets isolated session by platform user_id

**Pros:**
- Simple single deployment
- Lowest cost ($5/mo)
- Fastest to ship
- All users share model/tools (consistent experience)

**Cons:**
- Shared config risk (User A could see User B's settings)
- All users compete for same resources
- No per-user billing/usage tracking
- Single point of failure

**Success Metrics:**
- Active users count
- Concurrent sessions
- Resource utilization

---

### Phase 2: Multi-Project Isolation

**Timeline:** Week 3-4 (or on customer demand)

**Architecture:**
```
┌──────────────────────────────────────────────────────────┐
│                    API Gateway                            │
│              (Your auth, routing, billing)                │
└──────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Railway  │   │ Railway  │   │ Railway  │
   │ Project A│   │ Project B│   │ Project C│
   │          │   │          │   │          │
   │ User A   │   │ User B   │   │ User C   │
   │          │   │          │   │          │
   │ Volume   │   │ Volume   │   │ Volume   │
   └──────────┘   └──────────┘   └──────────┘
```

**Implementation:**

1. **Railway API Integration:**
   - Use Railway API to provision projects programmatically
   - Each customer gets own project
   - Customer pays for their own Railway usage

2. **Routing Layer:**
   - Custom API gateway (FastAPI/Flask)
   - Authenticate user (platform token or API key)
   - Route to correct Railway project based on user_id

3. **Per-User Resources:**
   - Isolated SQLite database
   - Isolated config
   - Isolated session storage
   - Isolated volume mount

**Pros:**
- Complete isolation between users
- Per-user billing easy
- No noisy neighbor problem
- Enterprise customers can request

**Cons:**
- 10x cost ($5/user minimum)
- Complex infrastructure
- More operational overhead

---

## 5. Implementation Checklist

### Phase 1 - Single Instance

- [ ] Deploy Dockerfile to Railway
- [ ] Configure persistent volume mount
- [ ] Set environment variables
- [ ] Configure Telegram bot
- [ ] Configure Discord bot (optional)
- [ ] Configure Slack bot (optional)
- [ ] Set up allowlist or DM pairing
- [ ] Test multi-user session isolation
- [ ] Monitor resource usage
- [ ] Set up logging/monitoring

### Phase 2 - Multi-Project

- [ ] Design API gateway architecture
- [ ] Implement user registration flow
- [ ] Integrate Railway API for project creation
- [ ] Build routing layer
- [ ] Implement per-user billing
- [ ] Add usage metering
- [ ] Build user dashboard
- [ ] Document self-serve signup flow

---

## 6. Cost Projections

### Phase 1 (Single Instance)

| Item | Cost |
|------|------|
| Railway Hobby | $5/mo |
| Domain (optional) | $12/yr |
| Bot tokens | Free |
| **Total** | **$5/mo** |

### Phase 2 (Multi-Project, 10 users)

| Item | Cost |
|------|------|
| Railway Pro (gateway) | $20/mo |
| 10 × Railway Hobby | $50/mo |
| Domain + SSL | $12/yr |
| Bot tokens | Free |
| **Total** | **~$70/mo** ($7/user) |

---

## 7. Alternatives Considered

### Modal/Daytona (Built-in Sleep/Wake)

The README mentions Modal/Daytona as options with "serverless persistence" — the agent hibernates when idle and wakes on demand, costing nearly nothing between sessions.

**Recommendation:** Keep as alternative for cost-sensitive users or add as tier in Phase 2. The integration already exists in the codebase (`hermes-agent[modal]`, `hermes-agent[daytona]`).

### VPS (Hetzner/DigitalOcean)

Traditional $5 VPS works fine but lacks:
- Automatic deploys
- Volume management
- Team features

**Recommendation:** Good fallback, Railway is simpler for team ops.

---

## 8. Railway setup (Phase 1)

Prerequisites: [Railway CLI](https://docs.railway.com/guides/cli) installed and `railway login` done. Repo root contains `railway.toml` and `Dockerfile`; the image **defaults to `hermes gateway run`** (messaging gateway), with data under `/opt/data`.

### 8.1 Create or link the project

```bash
# New project from this directory (optional name)
railway init --name hermes-agent

# Or attach to an existing project (e.g. created in the dashboard)
railway link
```

### 8.2 Connect GitHub (push-to-deploy)

In the [Railway dashboard](https://railway.com/dashboard): open the project → **Settings** → **Git** → connect the GitHub repository and enable deploys on push. Alternatively, from the CLI:

```bash
railway add -r YOUR_GITHUB_USER/hermes-agent
```

(Use your real org/user and repo name.)

### 8.3 Add a service (if the project is empty)

If you still need a service that builds from this repo: **New** → **GitHub Repo** → select `hermes-agent`, or use `railway add` and choose **GitHub Repo** in the interactive menu. Railway will detect `Dockerfile` / `railway.toml`.

If `railway status` shows **Service: None**, create or select a service in the dashboard, then run `railway service <service-name-or-id>` so CLI commands (`variables`, `volume`, `up`) target the Hermes service.

### 8.4 Persistent volume (required)

Hermes stores SQLite and config under `HERMES_HOME` (`/opt/data` in the image). **`railway.toml` sets `requiredMountPath = "/opt/data"`** — you must attach a volume at that path or deploys will not succeed.

**Dashboard:** Project → your Hermes service → **Storage** → **Add volume** → mount path **`/opt/data`**.

**CLI:**

```bash
railway volume add --mount-path /opt/data
# If needed: railway volume attach …  (see railway volume --help)
```

### 8.5 Environment variables

Set secrets in the service **Variables** tab or via CLI. Values are injected into the process environment; Hermes also reads `$HERMES_HOME/.env` after first boot (entrypoint copies `.env.example` once). Prefer Railway variables for secrets so they are not baked into the image.

Minimum for a typical OpenRouter setup (adjust to your providers):

```bash
railway variables --set "OPENROUTER_API_KEY=sk-or-v1-..." --set "LLM_MODEL=anthropic/claude-opus-4.6"
```

Add tool keys as needed (see repo root `.env.example`): e.g. `EXA_API_KEY`, `FIRECRAWL_API_KEY`, and platform tokens such as `TELEGRAM_BOT_TOKEN`, `DISCORD_BOT_TOKEN`, `SLACK_BOT_TOKEN`. Configure allowlists or DM pairing per `gateway/run.py` / docs.

**Do not commit real keys.** Use the dashboard or `railway variables --set` only.

### 8.6 Deploy

- **From Git:** push to the connected branch; Railway builds the Dockerfile and runs the start command implied by the image (`hermes gateway run`).
- **From local copy:**

```bash
railway up
```

### 8.7 Operational notes

- **Start command:** The Docker `CMD` is `gateway run` (see `Dockerfile`). You normally do not set a custom start command in Railway unless you override (e.g. `hermes chat` for a one-off — not typical on Railway).
- **Healthchecks:** The gateway is long-lived and may not expose an HTTP `/health` path; leave Railway healthcheck unset unless you add an HTTP probe.
- **Costs / resources:** See tables in sections 2 and 6 above.

### Next steps after deploy

1. **Test with 2–3 users** — Verify session isolation (`platform:user_id`).
2. **Add basic metrics** — Track active users.
3. **Iterate on Phase 1** — Fix issues before scaling.
4. **Plan Phase 2** — If demand materializes.

---

*Document generated: 2026-03-30*
*Target: Railway deployment with phased multi-tenant*
