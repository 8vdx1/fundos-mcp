# Connecting to FundOS MCP

How to connect your AI client to the FundOS MCP server.

## Claude Code (CLI)

```bash
claude mcp add fundos https://kela.com/mcp
```

Claude Code handles the full OAuth PKCE flow automatically:

1. Opens your browser to the FundOS login page
2. You log in and approve access on the consent screen
3. Claude Code stores the token — no manual handling needed

To verify the connection:

```
> list deals in diligence
> show open risk alerts
> what's the T+0 affirmation rate today?
```

## Claude.ai (web)

1. Go to [Claude.ai](https://claude.ai) → Settings → Connectors
2. Search for **FundOS** or paste: `https://kela.com/mcp`
3. Approve OAuth on the consent screen

The connection will appear as a connected server in your Claude.ai settings.

## Cursor

Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "fundos": {
      "url": "https://kela.com/mcp/sse",
      "transport": "sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Get a token at: `https://kela.com/oauth/authorize?client_id=mcp-generic`

Restart Cursor to pick up the config. See [cursor-setup.md](../examples/cursor-setup.md) for the full walkthrough.

## Any MCP-compatible client (SSE)

Use the SSE endpoint directly:

```
https://kela.com/mcp/sse
```

Pass a Bearer token in the `Authorization` header:

```
Authorization: Bearer vdr_<your-api-key>
```

Or use an OAuth access token obtained from the authorization server.

### Discovery endpoints

| Endpoint | Purpose |
|----------|---------|
| `https://kela.com/.well-known/mcp.json` | MCP server manifest |
| `https://kela.com/.well-known/oauth-authorization-server` | OAuth authorization server metadata (RFC 8414) |
| `https://kela.com/.well-known/oauth-protected-resource` | OAuth protected resource metadata (RFC 9728) |

## Any MCP-compatible client (HTTP/JSON-RPC)

For clients that prefer the JSON-RPC message endpoint:

```
POST https://kela.com/mcp/message
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "fundos_get_pipeline",
    "arguments": {}
  },
  "id": 1
}
```

See [python-client.py](../examples/python-client.py) for a complete working example.

## Getting a token

| Method | Instructions |
|--------|-------------|
| **OAuth (recommended)** | Open `https://kela.com/oauth/authorize?client_id=mcp-generic`, log in, approve |
| **API key** | Go to `https://kela.com/admin/api-keys`, generate a key prefixed `vdr_` |

API keys do not expire by default but can be revoked at any time. OAuth access tokens expire after 1 hour and are refreshed automatically by clients that support refresh tokens.

See [authentication.md](authentication.md) for the complete OAuth flow.

## Pre-registered OAuth clients

| Client | client_id | Redirect URI |
|--------|-----------|--------------|
| Claude Code | `claude-code` | `http://localhost:54321/callback` |
| Claude.ai | `claude-ai` | `https://claude.ai/oauth/callback` |
| Generic MCP | `mcp-generic` | `http://localhost:3000/callback` |

For custom clients, contact support@kela.com to register a new client_id and redirect URI.
