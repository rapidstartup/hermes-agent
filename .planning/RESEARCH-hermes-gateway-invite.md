# Research: Hermes Gateway Invite Functionality for Paperclip

## Problem Statement

Research how to create an "invite" functionality for Hermes agents to bring them into Paperclip, similar to how Paperclip has an invite for OpenClaw agents via the `openclaw_gateway` adapter.

## Current State

### Existing Hermes Integration

Paperclip already has a `hermes_local` adapter (registered in `server/src/adapters/registry.ts:188-199`) that uses the `hermes-paperclip-adapter` npm package. This adapter is for **local** Hermes agents (running on the same machine as Paperclip).

### OpenClaw Gateway Reference

Paperclip has a complete gateway-based invite system for OpenClaw:

1. **Adapter**: `packages/adapters/openclaw-gateway/` - WebSocket gateway adapter
2. **Invite endpoints**: `server/src/routes/access.ts:1991-2034` - `/companies/:companyId/openclaw/invite-prompt`
3. **Onboarding flow**: 
   - Creates invite with `allowedJoinTypes: "agent"`
   - Agent fetches onboarding manifest from `/invites/:token/onboarding`
   - Agent submits join request via POST
   - Agent claims API key
4. **Skill**: `paperclip` skill installed in OpenClaw at `~/.openclaw/skills/paperclip/SKILL.md`

## Required Components

### 1. Hermes Gateway Adapter (`hermes_gateway`)

Create a new adapter package at `packages/adapters/hermes-gateway/` with:

**Core files:**
- `src/index.ts` - Type definition, label, agent config doc
- `src/server/index.ts` - Export execute and testEnvironment
- `src/server/execute.ts` - WebSocket gateway execution (~1400 lines like openclaw-gateway)
- `src/server/test.ts` - Environment testing
- `src/ui/index.ts` - UI components
- `src/ui/build-config.ts` - Config builder for UI
- `src/cli/index.ts` - CLI integration

**Adapter interface (similar to openclaw_gateway):**
```typescript
// Core config fields
url: string                    // Hermes gateway WebSocket URL (ws:// or wss://)
headers: object               // Authentication headers
authToken: string             // Gateway token
password: string              // Gateway password (optional)

// Request behavior
timeoutSec: number            // Adapter timeout (default 120)
waitTimeoutMs: number         // agent.wait timeout override
sessionKeyStrategy: string    // "issue", "fixed", or "run"
sessionKey: string            // Fixed session key when strategy=fixed

// Paperclip integration
paperclipApiUrl: string       // Paperclip API base URL advertised in wake text
```

**Key implementation differences from OpenClaw:**
- Different WebSocket message format/frames
- Different auth mechanism (Hermes uses its own auth)
- Different wake text format (Hermes-specific context)
- Hermes-specific session management

### 2. Server Registration

Add to `server/src/adapters/registry.ts`:
```typescript
import {
  execute as hermesGatewayExecute,
  testEnvironment as hermesGatewayTestEnvironment,
} from "@paperclipai/adapter-hermes-gateway/server";

const hermesGatewayAdapter: ServerAdapterModule = {
  type: "hermes_gateway",
  execute: hermesGatewayExecute,
  testEnvironment: hermesGatewayTestEnvironment,
  // models: [...],
  supportsLocalAgentJwt: false,
  agentConfigurationDoc: hermesGatewayAgentConfigurationDoc,
};

// Add to adaptersByType map
```

### 3. Invite Endpoint

Add to `server/src/routes/access.ts`:
```typescript
router.post(
  "/companies/:companyId/hermes/invite-prompt",
  validate(createHermesInvitePromptSchema),
  async (req, res) => {
    // Similar to openclaw/invite-prompt but:
    // - adapterType: "hermes_gateway"
    // - Different skill name (hermes instead of paperclip)
    // - Hermes-specific onboarding text
  }
);
```

### 4. Onboarding Manifest

The onboarding manifest should include:
- Hermes-specific wake text with Paperclip context
- Registration endpoint for join requests
- Skill: "hermes" skill that Hermes installs
- Connectivity diagnostics

### 5. Hermes Skill

Create a skill that Hermes uses to bootstrap into Paperclip:
- Name: `paperclip` (or `hermes-paperclip`)
- Location: `/api/skills/hermes-paperclip` or similar
- Install path in Hermes: `~/.hermes/skills/paperclip/SKILL.md`

The skill provides:
- Instructions for connecting to Paperclip
- API endpoints to use
- How to claim API key
- How to handle Paperclip tasks

### 6. UI Updates

Update UI files to include `hermes_gateway`:
- `ui/src/pages/NewAgent.tsx` - Add to adapter type dropdown
- `ui/src/pages/OrgChart.tsx` - Display name mapping
- `ui/src/pages/AgentDetail.tsx` - Agent detail view
- `ui/src/components/agent-config-primitives.tsx` - Config fields

## Architecture Pattern

The gateway adapter pattern works as follows:

```
Paperclip Server                    Hermes Gateway                 Hermes Agent
     |                                   |                            |
     |  1. Create invite                 |                            |
     |---------------------------------->|                            |
     |                                   |                            |
     |  2. Return invite URL             |                            |
     |<-----------------------------------|                            |
     |                                   |                            |
     |                                   |  3. Fetch /invites/:token/
     |                                   |     onboarding             |
     |                                   |<---------------------------|
     |                                   |                            |
     |  4. Return onboarding manifest    |                            |
     |   (registration endpoint, skill)   |                            |
     |---------------------------------->|                            |
     |                                   |                            |
     |                                   |  5. POST /join-requests
     |                                   |     (claim API key)         |
     |  6. Create join request           |                            |
     |<----------------------------------|                            |
     |                                   |                            |
     |  7. Return join request + secret  |                            |
     |---------------------------------->|                            |
     |                                   |                            |
     |                                   |  8. Claim API key
     |                                   |     POST /join-requests/:id/
     |                                   |     claim-api-key          |
     |<----------------------------------|                            |
     |                                   |                            |
     |                                   |  9. WebSocket connection
     |  10. Agent runs tasks             |--------------------------->|
     |<----------------------------------|                            |
```

## Hermes Gateway Protocol

Based on the OpenClaw gateway implementation, Hermes gateway would use:

1. **WebSocket connection** to `ws://<hermes-gateway-url>`
2. **Protocol frames**:
   - `req`: Request frame with method and params
   - `res`: Response frame with ok/payload/error
   - `event`: Event frame (agent output, shutdown, etc.)
3. **Authentication**: Token-based via headers
4. **Device pairing**: Optional for auto-approval

## Don't Hand-Roll

- WebSocket client implementation (use ws library like OpenClaw does)
- Token hashing for invites (reuse existing `hashToken` utilities)
- Invite expiration logic (reuse existing patterns)
- Join request flow (reuse existing `join_requests` table and endpoints)

## Common Pitfalls

1. **Protocol mismatch**: Hermes gateway must match the protocol Hermes gateway expects
2. **Auth header naming**: Match exactly what Hermes gateway expects (e.g., `x-hermes-token` vs `x-openclaw-token`)
3. **Wake text format**: Must be parseable by Hermes agent
4. **Connectivity**: Ensure Paperclip can reach Hermes gateway URL (hostname resolution)
5. **Session key strategy**: Different strategies have different implications for state

## Standard Stack

- **WebSocket**: `ws` npm package (used by openclaw-gateway)
- **Crypto**: Node.js `crypto` module for token handling
- **Adapter utils**: `@paperclipai/adapter-utils` for common adapter functionality
- **Testing**: vitest (like other adapters)

## Code Examples

### Adapter Type Definition
```typescript
// packages/adapters/hermes-gateway/src/index.ts
export const type = "hermes_gateway";
export const label = "Hermes Gateway";

export const models: { id: string; label: string }[] = [];

export const agentConfigurationDoc = `# hermes_gateway agent configuration

Adapter: hermes_gateway

Use when:
- You want Paperclip to invoke Hermes over the Gateway WebSocket protocol.

Core fields:
- url (string, required): Hermes gateway WebSocket URL
- headers (object, optional): authentication headers
- authToken (string, optional): gateway token override
`;
```

### Server Registration
```typescript
// server/src/adapters/registry.ts (existing pattern)
const hermesGatewayAdapter: ServerAdapterModule = {
  type: "hermes_gateway",
  execute: hermesGatewayExecute,
  testEnvironment: hermesGatewayTestEnvironment,
  models: hermesGatewayModels,
  supportsLocalAgentJwt: false,
  agentConfigurationDoc: hermesGatewayAgentConfigurationDoc,
};
```

### Invite Endpoint
```typescript
// server/src/routes/access.ts (similar to openclaw)
router.post(
  "/companies/:companyId/hermes/invite-prompt",
  validate(createHermesInvitePromptSchema),
  async (req, res) => {
    const companyId = req.params.companyId;
    await assertCanGenerateHermesInvitePrompt(req, companyId);
    
    const { token, created } = await createCompanyInviteForCompany({
      req,
      companyId,
      allowedJoinTypes: "agent",  // Agents only
      defaultsPayload: null,
      agentMessage: req.body.agentMessage ?? null
    });
    
    // Return with hermes_gateway specific fields
    res.status(201).json({
      ...created,
      token,
      inviteUrl: `/invite/${token}`,
      // ...
    });
  }
);
```

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Adapter architecture | High | OpenClaw provides complete reference |
| Server registration | High | Standard pattern already exists |
| Invite endpoints | High | Can copy from OpenClaw |
| Onboarding flow | High | Reuse existing patterns |
| UI integration | Medium | Need to verify Hermes-specific config fields |
| Hermes gateway protocol | Medium | Need to confirm with Hermes implementation |

## Next Steps

1. **Confirm Hermes gateway protocol**: Work with Hermes team to understand the exact WebSocket protocol, message formats, and auth mechanism
2. **Create adapter package**: Build `packages/adapters/hermes-gateway/` following openclaw-gateway pattern
3. **Add invite endpoint**: Copy from OpenClaw and adapt for Hermes
4. **Create skill**: Design skill that Hermes uses to bootstrap into Paperclip
5. **Test end-to-end**: Full flow from invite creation to agent running tasks
