# fundos-mcp

MCP server for FundOS — connect Claude Code, Cursor, Codex CLI, and any AI agent to your fund operations.

## What is FundOS?

FundOS is an AI-native operating system for fund managers — private equity, private credit, hedge funds, and venture capital. It replaces disconnected tools (Allvue, Juniper Square, Datasite, Salesforce) with a unified agentic platform across the full fund lifecycle.

## Two ways to integrate

### Option A — MCP server (full FundOS account)

Connect Claude Code, Codex CLI, or any MCP client to your live FundOS data.

**Claude Code (SSE):**
```bash
claude mcp add --transport sse fundos https://www.kela.com/mcp/sse
```

**Codex CLI (Streamable HTTP):**
```bash
# Step 1 — add the MCP server
codex mcp add fundos --url https://www.kela.com/mcp \
  --bearer-token-env-var FUNDOS_API_KEY

# Step 2 — get a vdr_ key at https://kela.com/admin/api-keys
# Add to ~/.zshenv (not ~/.zshrc — Codex uses non-interactive shells)
export FUNDOS_API_KEY=vdr_your_key_here

# Step 3 — run (--sandbox danger-full-access is required for MCP tool calls)
codex exec --skip-git-repo-check \
  --sandbox danger-full-access \
  "Use the fundos MCP server to check my deals"
```

Codex CLI uses Bearer API key auth. Claude Code uses OAuth 2.0 PKCE — it opens a browser window on first use.

47 tools across: deal rooms, deal CRM, LP CRM, risk, pricer, CFO, OMS, syndication, HF Ops (DTCC), compliance, and more.

### Option B — Stateless Document API (no FundOS account required)

Law firms, fund admins, LPs, and placement agents can generate K-1s, ODD/DDQs, and document analyses without creating a FundOS account or loading any fund data.

**Get a `doc_` key at https://kela.com/developers/register** — email + password, key appears immediately. First 30 days free.

```bash
curl -X POST https://kela.com/api/v1/documents/k1 \
  -H "Authorization: Bearer doc_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "fund_name": "Eight Capital Fund II",
    "tax_year": 2025,
    "partner_name": "Aksia LP",
    "lp_share_pct": 0.15,
    "box_1_ordinary_income": 45000,
    "box_9a_lt_gain": 105000
  }'
# → { "html": "<!DOCTYPE html>...", "filename": "k1_2025_aksia_lp.html",
#     "charged_usd": 5.00 }
```

Five endpoints — no account needed:

| Endpoint | Purpose | Price |
|---|---|---|
| `POST /api/v1/documents/k1` | Schedule K-1 (Form 1065) | $5/call |
| `POST /api/v1/documents/odd` | ODD/DDQ completion | $25/call |
| `POST /api/v1/documents/analyze` | Document red-flag + entity-map | $3/call |
| `POST /api/v1/documents/waterfall` | European waterfall | Free |
| `POST /api/v1/documents/pricer` | IRR/MOIC/WAL pricer | Free |

## Quick links

| | |
|---|---|
| 📚 Docs | [docs/quickstart.md](docs/quickstart.md) |
| 🔑 Stateless API | [docs/stateless-api.md](docs/stateless-api.md) |
| 🛠 MCP Tools | [docs/mcp-tools.md](docs/mcp-tools.md) |
| 🔒 Auth | [docs/authentication.md](docs/authentication.md) |
| 🐍 Python example | [examples/python-client.py](examples/python-client.py) |
| 🖥 Cursor setup | [examples/cursor-setup.md](examples/cursor-setup.md) |
| 🌐 API reference | https://kela.com/api/docs |
| 💬 Support | support@kela.com |

## Discovery files

```
https://kela.com/CLAUDE.md                        — canonical agent guide
https://kela.com/llms.txt                         — short FundOS overview for LLMs
https://kela.com/llms-full.txt                    — full developer + integration reference
https://kela.com/.well-known/mcp.json             — MCP server discovery
https://kela.com/.well-known/oauth-authorization-server
https://kela.com/.well-known/oauth-protected-resource
```

## Pricing (MCP / full account)

- $299/paying-seat/month includes 6,000 credits
- 1 credit = $0.01 — same for humans and agents
- Tool tiers: read\_fast 1cr → ai\_heavy 50cr
- Outcome fees (waived during 30-day trial): K-1 $50, ODD $150, CIM $250, audit pack $100

## License

MIT
