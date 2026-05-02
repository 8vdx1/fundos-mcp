# Quickstart

Connect an AI agent to FundOS in under 5 minutes.

## Option A — Claude Code (recommended)

```bash
claude mcp add fundos https://kela.com/mcp
```

Claude Code handles OAuth automatically. It opens the browser, you log in
to FundOS and approve access, and the token is stored. Done.

Test it:

```
> list deals in diligence
> show open risk alerts
> what's the T+0 affirmation rate today?
```

## Option B — Cursor

1. Create `.cursor/mcp.json` in your project root:

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

2. Get a token: open `https://kela.com/oauth/authorize?client_id=mcp-generic`
3. Restart Cursor

See [cursor-setup.md](../examples/cursor-setup.md) for the full walkthrough.

## Option C — Python / httpx

```bash
pip install httpx
```

```python
import httpx

headers = {"Authorization": "Bearer YOUR_TOKEN_HERE"}

r = httpx.post("https://kela.com/mcp/message", headers=headers, json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": "fundos_get_pipeline", "arguments": {}},
    "id": 1,
})
print(r.json())
```

See [python-client.py](../examples/python-client.py) for more examples.

## Get a token

| Method | Instructions |
|--------|-------------|
| OAuth (recommended) | Open `https://kela.com/oauth/authorize?client_id=mcp-generic`, log in, approve |
| API key | Go to `https://kela.com/admin/api-keys`, generate a key prefixed `vdr_` |

See [authentication.md](authentication.md) for the full OAuth flow.
