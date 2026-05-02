# Cursor Setup

Connect Cursor to FundOS so you can query deals, LPs, documents, and risk
directly from the editor.

## 1. Create the config file

In your project root, create `.cursor/mcp.json`:

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

## 2. Get your token

Open this URL in your browser and log in to FundOS:

```
https://kela.com/oauth/authorize?client_id=mcp-generic&response_type=code&scope=read+write
```

Approve access on the consent screen. Copy the access token from the callback.

Alternatively, generate a long-lived API key at `https://kela.com/admin/api-keys`
and use that as `vdr_<your-key>` — no expiry, revocable at any time.

## 3. Restart Cursor

Cursor picks up MCP config changes on restart. Open the MCP panel to confirm
FundOS is listed as a connected server.

## 4. Test it

In Cursor chat:

```
@fundos list open risk alerts
```

```
@fundos what deals are in diligence?
```

```
@fundos search documents for transfer restrictions in the LPA
```

## Available tools

| Category | Example prompt |
|----------|---------------|
| Deal pipeline | "What's in the diligence stage?" |
| LP investors | "List all LPs and their committed capital" |
| Documents | "Search room 12 for redemption terms" |
| Risk | "Show all open covenant breaches" |
| Waterfall | "Model a $50M exit on $20M committed at 8% hurdle" |
| HF Ops | "What's today's T+0 affirmation rate?" |
| Pricer | "Price a $10M 3-year note at SOFR+350" |

Full tool reference: https://kela.com/api/docs
