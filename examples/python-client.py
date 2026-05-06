"""
FundOS MCP — Python client example
Requires: httpx (pip install httpx)

Get a token: https://kela.com/oauth/authorize?client_id=mcp-generic
Or use an API key from: https://kela.com/admin/api-keys
"""

import hashlib
import hmac
import json

import httpx

FUNDOS_MCP_URL = "https://kela.com/mcp"
FUNDOS_API_URL = "https://kela.com/api/v1"
ACCESS_TOKEN = "your-oauth-token-here"  # or vdr_<api-key>

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


# ── Webhook helpers ────────────────────────────────────────────────────────────

def verify_fundos_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify an inbound X-FundOS-Signature header on your receiving endpoint."""
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected.encode(), signature_header.encode())


def register_webhook(url: str, event_types: list | None = None, name: str = "") -> dict:
    """Register a webhook endpoint.  Returns the endpoint record (including secret)."""
    resp = httpx.post(
        f"{FUNDOS_API_URL}/webhooks/",
        headers=headers,
        json={"url": url, "name": name, "event_types": event_types},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def list_webhooks() -> list:
    resp = httpx.get(f"{FUNDOS_API_URL}/webhooks/", headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def webhook_deliveries(endpoint_id: int, page: int = 1) -> dict:
    resp = httpx.get(
        f"{FUNDOS_API_URL}/webhooks/{endpoint_id}/deliveries",
        headers=headers,
        params={"page": page},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Example: register and handle webhooks ─────────────────────────────────────

# 1. Register an endpoint (run once, save the returned secret securely)
# endpoint = register_webhook(
#     url="https://my-agent.example.com/hooks/fundos",
#     event_types=["credit.low", "action.approval_required", "action.approved"],
#     name="My agent listener",
# )
# MY_WEBHOOK_SECRET = endpoint["secret"]  # SAVE THIS — only shown at creation

# 2. In your Flask/FastAPI receiver:
#
# @app.post("/hooks/fundos")
# def receive(request: Request):
#     raw = request.body()
#     sig = request.headers.get("X-FundOS-Signature", "")
#     if not verify_fundos_signature(raw, sig, MY_WEBHOOK_SECRET):
#         raise HTTPException(401)
#     event = json.loads(raw)
#     delivery_id = event["delivery_id"]   # stable UUID across retries — deduplicate here
#     print(f"Received {event['event']} delivery_id={delivery_id}")
#     return {"ok": True}


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
