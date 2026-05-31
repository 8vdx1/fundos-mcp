# Quickstart

Connect an AI agent to FundOS in under 5 minutes.

## Option A — Claude Code (SSE transport)

```bash
claude mcp add --transport sse fundos https://www.kela.com/mcp/sse
```

Claude Code handles OAuth automatically. It opens a browser window on first use — log in to FundOS and approve access. Token is stored for future sessions.

Test it:

```
> list deals in diligence
> show open risk alerts
> what's the T+0 affirmation rate today?
```

## Option B — OpenAI Codex CLI (Streamable HTTP)

Codex CLI connects via Streamable HTTP (`POST /mcp`) with a Bearer API key.

**Step 1 — Register the MCP server:**
```bash
codex mcp add fundos --url https://www.kela.com/mcp \
  --bearer-token-env-var FUNDOS_API_KEY
```

**Step 2 — Get an API key and export it:**

Get a `vdr_` key at `https://kela.com/admin/api-keys`, then add to `~/.zshenv`
(not `~/.zshrc` — Codex uses non-interactive shells):

```bash
export FUNDOS_API_KEY=vdr_your_key_here
```

**Step 3 — Run with required sandbox flag:**
```bash
codex exec --skip-git-repo-check \
  --sandbox danger-full-access \
  "Use the fundos MCP server to list my deals"
```

> **Important:** `--sandbox danger-full-access` is required. Without it, Codex runs in `workspace-write` mode which silently cancels MCP tool calls in non-interactive exec sessions. This is a Codex limitation, not a FundOS issue.

**Tip — add a shell wrapper to `~/.zshenv` so you never forget:**
```bash
codex() {
  if [[ "$1" == "exec" && "$*" != *"--sandbox"* ]]; then
    shift
    command codex exec --sandbox danger-full-access "$@"
    return $?
  fi
  command codex "$@"
}
```

## Option C — Cursor

Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "fundos": {
      "url": "https://kela.com/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer vdr_YOUR_KEY_HERE"
      }
    }
  }
}
```

Get a `vdr_` key at `https://kela.com/admin/api-keys`. Restart Cursor.

See [cursor-setup.md](../examples/cursor-setup.md) for the full walkthrough.

## Option D — Python / httpx

```bash
pip install httpx
```

```python
import httpx

headers = {"Authorization": "Bearer vdr_YOUR_KEY_HERE"}

r = httpx.post("https://kela.com/mcp/message", headers=headers, json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": "fundos_get_pipeline", "arguments": {}},
    "id": 1,
})
print(r.json())
```

See [python-client.py](../examples/python-client.py) for more examples.

## Option E — Stateless Document API (no FundOS account required)

For law firms, fund admins, and LPs who just need to generate documents — no account needed.

```bash
curl -X POST https://kela.com/api/v1/documents/k1 \
  -H "Authorization: Bearer doc_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "fund_name": "My Fund I",
    "tax_year": 2025,
    "partner_name": "LP Name",
    "lp_share_pct": 0.10,
    "box_1_ordinary_income": 50000
  }'
```

Get a `doc_` key at https://kela.com/developers/register. First 30 days free.

See [stateless-api.md](stateless-api.md) for all five endpoints.

---

## Authentication summary

| Key type | Prefix | Auth method | Use for |
|---|---|---|---|
| API key (full account) | `vdr_` | Bearer token | MCP, REST API |
| Developer key (stateless) | `doc_` | Bearer token | `/api/v1/documents/*` only |
| OAuth token | `eyJ…` | Bearer token | Browser sessions, Claude Code |

### Dynamic Client Registration (RFC 7591)

MCP clients like Codex CLI and Claude Code can self-register without a pre-configured `client_id`:

```
POST https://kela.com/oauth/register
Content-Type: application/json

{
  "client_name": "My Agent",
  "redirect_uris": ["http://localhost:9999/cb"],
  "grant_types": ["authorization_code"],
  "token_endpoint_auth_method": "none"
}
→ 201 { "client_id": "dyn_...", ... }
```

Discovery: `GET /.well-known/oauth-authorization-server` → `registration_endpoint`.

See [authentication.md](authentication.md) for the full OAuth PKCE flow.
