# Authentication

FundOS MCP uses OAuth 2.0 Authorization Code flow with PKCE (RFC 7636).
No API keys to manage. No manual token handling.

## How it works

1. Your agent opens: https://kela.com/oauth/authorize
2. You log in to FundOS and approve access in the browser
3. Agent receives an access token automatically
4. Token is used as a Bearer header on all MCP requests
5. Refresh tokens handle expiry silently

## Discovery endpoints

```
https://kela.com/.well-known/oauth-authorization-server
https://kela.com/.well-known/oauth-protected-resource
https://kela.com/.well-known/mcp.json
```

## Pre-registered clients

| Client | client_id | Redirect URI |
|--------|-----------|--------------|
| Claude Code | claude-code | http://localhost:54321/callback |
| Claude.ai | claude-ai | https://claude.ai/oauth/callback |
| Generic MCP | mcp-generic | http://localhost:3000/callback |

## Scopes

| Scope | Access |
|-------|--------|
| read | View deals, LPs, documents, fund data |
| write | Create and update records |
| admin | Full access including user management |

## Token lifetimes

| Token | Lifetime |
|-------|----------|
| Access token | 1 hour |
| Refresh token | 30 days (rotating) |

## Claude Code (CLI)

```bash
claude mcp add fundos https://kela.com/mcp
```

Claude Code handles the full OAuth PKCE flow automatically — opens the browser,
completes the consent screen, stores the token.

## Cursor

Add to `.cursor/mcp.json`:

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

## Claude.ai (web)

1. Go to Claude.ai → Settings → Connectors
2. Search for FundOS or paste: `https://kela.com/mcp`
3. Approve OAuth

## API keys (alternative)

If you prefer a long-lived static credential, generate an API key at
`/admin/api-keys`. Send it as:

```
Authorization: Bearer vdr_<your-key>
```

API keys do not expire by default but can be revoked at any time.
