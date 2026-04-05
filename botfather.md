I’ll quickly trace where BOTFATHER_SVC_URL and BOTFATHER_SVC_TOKEN are used so I can tell you the exact API call shape you can reproduce outside the app.

I found the architecture doc, now I’m locating the concrete route implementation for BotFather provisioning so I can give you the exact request payload and auth header.

Use your BotFather service directly:

BOTFATHER_SVC_URL = base URL of botfather-svc (no trailing slash), e.g. https://botfather-svc-production.up.railway.app
BOTFATHER_SVC_TOKEN = the service AUTH_TOKEN (sent as Authorization: Bearer ...)
Create a bot (direct API call)
curl -X POST "$BOTFATHER_SVC_URL/provision" \
  -H "Authorization: Bearer $BOTFATHER_SVC_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Agent Name",
    "username": "my_agent_name_bot"
  }'
Notes:

username must end with bot.
If username is taken, this endpoint returns failure; your app code retries with suffixed names (_01_bot, etc), but direct calls must handle that yourself.
Other useful botfather-svc endpoints
POST $BOTFATHER_SVC_URL/revoke with { "username": "my_agent_name_bot" } (get fresh token for existing bot)
POST $BOTFATHER_SVC_URL/deprovision with { "username": "my_agent_name_bot" } (delete bot)