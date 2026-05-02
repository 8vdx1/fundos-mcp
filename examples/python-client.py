"""
FundOS MCP — Python client example
Requires: httpx (pip install httpx)

Get a token: https://kela.com/oauth/authorize?client_id=mcp-generic
Or use an API key from: https://kela.com/admin/api-keys
"""

import httpx

FUNDOS_MCP_URL = "https://kela.com/mcp"
ACCESS_TOKEN = "your-oauth-token-here"  # or vdr_<api-key>

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def call_tool(name: str, arguments: dict = None) -> dict:
    response = httpx.post(
        f"{FUNDOS_MCP_URL}/message",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
            "id": 1,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ── Deal pipeline ─────────────────────────────────────────────────────────────

pipeline = call_tool("fundos_get_pipeline")
print("Pipeline:", pipeline)

diligence_deals = call_tool("fundos_list_deals", {"stage": "diligence"})
print("In diligence:", diligence_deals)


# ── Risk ──────────────────────────────────────────────────────────────────────

alerts = call_tool("fundos_list_risk_alerts", {"open": True})
print("Open risk alerts:", alerts)

covenants = call_tool("fundos_list_covenants")
print("Covenants:", covenants)


# ── LP investors ──────────────────────────────────────────────────────────────

lps = call_tool("fundos_list_lps")
print("LPs:", lps)


# ── Documents (VDR) ───────────────────────────────────────────────────────────

rooms = call_tool("list_deal_rooms")
print("Deal rooms:", rooms)

# Search across all documents in a room
answer = call_tool("search_documents", {
    "query": "what are the transfer restrictions in the LPA?",
})
print("Document search:", answer)


# ── Waterfall modelling ───────────────────────────────────────────────────────

waterfall = call_tool("fundos_compute_waterfall", {
    "distributable": 50_000_000,
    "committed":     20_000_000,
    "hurdle_pct":    0.08,
    "carry_pct":     0.20,
})
print("Waterfall:", waterfall)


# ── DTCC / HF Ops ─────────────────────────────────────────────────────────────

scorecard = call_tool("hf_ops_dtcc_get_affirmation_scorecard")
print("T+0 scorecard:", scorecard)

unaffirmed = call_tool("hf_ops_dtcc_list_unaffirmed")
print("Unaffirmed confirms:", unaffirmed)
