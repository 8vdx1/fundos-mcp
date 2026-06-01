#!/usr/bin/env python3
"""
MyVDR MCP Server — Model Context Protocol server for AI agent integration.

Exposes VDR deal rooms, documents, users, audit logs, and signatures
as MCP tools and resources for Claude, ChatGPT, and other AI agents.

Usage (stdio transport):
    FUNDOS_API_KEY=your-key FUNDOS_BASE_URL=https://my-vdr.vercel.app python server.py

Usage (SSE transport for remote hosting):
    Set MCP_TRANSPORT=sse and MCP_PORT=8080
"""
import json
import os
import logging
from datetime import datetime

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fundos-mcp")

# ── Configuration ────────────────────────────────────────────────────────────

API_KEY = os.environ.get("FUNDOS_API_KEY", "")
BASE_URL = os.environ.get("FUNDOS_BASE_URL", "https://www.kela.com").rstrip("/")
API_BASE = f"{BASE_URL}/api/v1"

# Startup sanity checks — these surface in Claude Desktop's MCP server log pane.
if not API_KEY:
    logger.warning("FUNDOS_API_KEY is not set — every API call will return 401.")
if "my-vdr.vercel.app" in BASE_URL:
    logger.warning(
        "FUNDOS_BASE_URL points to the legacy host my-vdr.vercel.app. "
        "Set FUNDOS_BASE_URL=https://www.kela.com in your Claude Desktop MCP config."
    )


def _api(method: str, path: str, **kwargs) -> dict:
    """Make an authenticated API call to MyVDR.

    On non-2xx, returns a structured ``{"error", "status", "body"}`` dict
    instead of raising. Callers (tools and resources) treat the return as
    a dict and surface errors as MCP content rather than letting the host
    show the opaque "Failed to attach resource. You can try again." dialog.
    """
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    url = f"{API_BASE}{path}"
    try:
        resp = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    except requests.RequestException as e:
        return {"error": f"network: {e}", "url": url}
    if resp.status_code >= 400:
        body = (resp.text or "")[:500]
        return {"error": f"HTTP {resp.status_code}", "status": resp.status_code, "body": body, "url": url}
    try:
        return resp.json()
    except ValueError:
        return {"error": "non-JSON response", "status": resp.status_code, "body": (resp.text or "")[:500], "url": url}


def _get(path: str, params: dict = None) -> dict:
    return _api("GET", path, params=params)


def _post(path: str, data: dict = None) -> dict:
    return _api("POST", path, json=data)


def _put(path: str, data: dict = None) -> dict:
    return _api("PUT", path, json=data)


def _delete(path: str) -> dict:
    return _api("DELETE", path)


# ── MCP Server ───────────────────────────────────────────────────────────────

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource, ToolAnnotations
except ImportError:
    logger.error("MCP SDK not installed. Run: pip install mcp")
    raise SystemExit(1)

FUNDOS_INSTRUCTIONS = (
    "FundOS is an AI-native fund operating system. Use these tools to manage "
    "deals, LP investors, capital calls, reconciliation, risk, and documents "
    "for hedge funds, PE firms, and private credit managers. Always ask for "
    "human approval before posting financial entries or sending notices to "
    "investors."
)

# `instructions` was added in MCP SDK 1.2; pass it conditionally so older
# SDK installs keep working (Server() rejects unknown kwargs).
try:
    server = Server("fundos", instructions=FUNDOS_INSTRUCTIONS)
except TypeError:
    server = Server("fundos")


# ── Tools ────────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools():
    # Annotation shorthands — used on every tool to satisfy MCP 2025-03 spec.
    # _RO: pure read — safe to retry, never mutates state.
    # _WR: may write — creates / updates DB rows; destructive=False (no deletes).
    _RO = ToolAnnotations(readOnlyHint=True,  destructiveHint=False, idempotentHint=True)
    _WR = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
    return [
        # ── Deal Room Tools ─────────────────────────────────────────────────
        Tool(
            name="list_deal_rooms",
            title="List Deal Rooms",
            description="Use this to enumerate deal rooms when the agent needs to pick a room to inspect or act on. Returns an array of {id, name, status, member_count} for every room the API key can read.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="get_deal_room",
            title="Get Deal Room",
            description="Use this to drill into a single deal room when you have a room_id and need its members or stats. Returns full room metadata plus member list and document count.",
            inputSchema={
                "type": "object",
                "properties": {"room_id": {"type": "integer", "description": "Deal room ID"}},
                "required": ["room_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="create_deal_room",
            title="Create Deal Room",
            description="Use this to create a new deal room when starting a diligence process or onboarding an LP. Requires admin privileges. Returns the new room id and slug. Always confirm the name with a human first.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Room name (e.g. 'Series A')"},
                    "description": {"type": "string", "description": "Room description"},
                    "status": {"type": "string", "enum": ["active", "draft", "closed"], "default": "active"},
                },
                "required": ["name"],
            },
            annotations=_WR,
        ),

        # ── Document Tools ──────────────────────────────────────────────────
        Tool(
            name="list_documents",
            title="List Documents",
            description="Use this to enumerate documents in a deal room when you need an inventory before searching or summarising. Optional folder_id narrows to a single folder. Returns docs with file_type, size, uploaded_at.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer", "description": "Deal room ID"},
                    "folder_id": {"type": "integer", "description": "Optional folder ID to filter"},
                },
                "required": ["room_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="get_document_metadata",
            title="Get Document Metadata",
            description="Use this to inspect a single document's metadata when checking provenance, AI classification, or view stats before deciding to download. Returns filename, file_type, upload_date, view_count, ai_classification, tags.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer"},
                    "doc_id": {"type": "integer", "description": "Document ID"},
                },
                "required": ["room_id", "doc_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="get_document_download_url",
            title="Get Document Download URL",
            description="Use this to obtain a download URL for a document when the agent needs to fetch the raw file (PDF, XLSX, DOCX). Returns a short-lived URL pointing at the VDR download endpoint.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer"},
                    "doc_id": {"type": "integer"},
                },
                "required": ["room_id", "doc_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="search_documents",
            title="Search Documents",
            description="Use this to answer free-form questions over deal-room documents when the user asks something like 'what does the LPA say about transfer rights'. Returns AI-grounded answer with citations. Optional folder_id narrows scope.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or question about documents"},
                    "folder_id": {"type": "integer", "description": "Optional: limit search to a specific folder"},
                },
                "required": ["query"],
            },
            annotations=_RO,
        ),

        # ── User & Access Tools ─────────────────────────────────────────────
        Tool(
            name="list_room_members",
            title="List Room Members",
            description="Use this to list members of a deal room when checking who has access before granting more or before sharing sensitive content. Returns user_id, email, role, and per-folder permissions.",
            inputSchema={
                "type": "object",
                "properties": {"room_id": {"type": "integer"}},
                "required": ["room_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="add_room_member",
            title="Add Room Member",
            description="Use this to add a user to a deal room when onboarding a new collaborator or LP. Role is 'member' or 'manager'. Always confirm the email and role with a human first — this expands access.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer"},
                    "user_id": {"type": "integer", "description": "User ID to add"},
                    "role": {"type": "string", "enum": ["member", "manager"], "default": "member"},
                },
                "required": ["room_id", "user_id"],
            },
            annotations=_WR,
        ),
        Tool(
            name="list_users",
            title="List Users",
            description="Use this to enumerate users in the org when matching a person by email or building a team-wide report. Returns id, email, role, is_admin, is_active for every user.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),

        # ── Audit Tools ─────────────────────────────────────────────────────
        Tool(
            name="get_audit_log",
            title="Get Audit Log",
            description="Use this to inspect activity history when investigating suspicious access, building a compliance report, or showing a user what they did. Filter by action (VIEW|DOWNLOAD|UPLOAD|LOGIN|DELETE), user_id, or date range.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer", "description": "Filter by deal room"},
                    "action": {"type": "string", "description": "Filter by action (VIEW, DOWNLOAD, UPLOAD, LOGIN)"},
                    "user_id": {"type": "integer", "description": "Filter by user"},
                    "page": {"type": "integer", "default": 1},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="get_document_activity",
            title="Get Document Activity",
            description="Use this to surface engagement signals for a single document when the GP wants to know which LPs are actually reading it. Returns per-viewer timestamps, view durations, and IPs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer"},
                    "doc_id": {"type": "integer"},
                },
                "required": ["room_id", "doc_id"],
            },
            annotations=_RO,
        ),

        # ── Signature Tools ─────────────────────────────────────────────────
        Tool(
            name="get_signature_status",
            title="Get Signature Status",
            description="Use this to check signature progress when chasing closing signatures or reporting to the deal team. Returns per-envelope status (sent/signed/declined/voided) for every DocuSign envelope tied to the room.",
            inputSchema={
                "type": "object",
                "properties": {"room_id": {"type": "integer"}},
                "required": ["room_id"],
            },
            annotations=_RO,
        ),

        # ── Q&A Tools ───────────────────────────────────────────────────────
        Tool(
            name="list_qa_questions",
            title="List Q&A Questions",
            description="Use this to read the diligence Q&A queue when prioritising what to answer next or auditing open questions. Optional status filter (open|in_progress|answered|closed). Returns title, asker, priority, due_date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["open", "in_progress", "answered", "closed"]},
                },
                "required": ["room_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="answer_qa_question",
            title="Answer Q&A Question",
            description="Use this to publish an answer to a diligence Q&A question after a human has reviewed the draft. Returns the saved answer record. Do NOT post drafts unreviewed — this is visible to the asking LP.",
            inputSchema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer"},
                    "question_id": {"type": "integer"},
                    "answer": {"type": "string", "description": "The answer text"},
                },
                "required": ["room_id", "question_id", "answer"],
            },
            annotations=_WR,
        ),

        # ── FundOS: CRM & Pipeline ──────────────────────────────────────────
        Tool(
            name="fundos_list_deals",
            title="List Deals",
            description="Use this to read the deal pipeline when ranking opportunities, picking what to work on next, or building a status snapshot. Optional stage filter (sourcing|qualification|dd|ic|closing|closed|lost). Returns Deal objects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stage": {"type": "string",
                              "description": "Optional stage filter (sourcing, qualification, dd, ic, closing, closed, lost)"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_get_deal",
            title="Get Deal",
            description="Use this to load full detail on one deal (counterparty, target size, stage, IRR target, notes) when drafting a memo or answering a question about it. Returns the Deal record by id.",
            inputSchema={
                "type": "object",
                "properties": {"deal_id": {"type": "integer"}},
                "required": ["deal_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_create_deal",
            title="Create Deal",
            description="Use this to add a new deal to the pipeline when an inbound pitch is qualified or a term sheet arrives. Set ephemeral=true to dry-run validate without writing. Always confirm name and target_size with a human before persisting.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "counterparty": {"type": "string"},
                    "asset_class": {"type": "string",
                                    "description": "private_credit, private_equity, real_estate, infra, venture, secondaries, other"},
                    "stage": {"type": "string", "default": "sourcing"},
                    "target_size": {"type": "number"},
                    "currency": {"type": "string", "default": "USD"},
                    "irr_target": {"type": "number"},
                    "notes": {"type": "string"},
                    "ephemeral": {"type": "boolean", "default": False},
                },
                "required": ["name"],
            },
            annotations=_WR,
        ),
        Tool(
            name="fundos_get_pipeline",
            title="Get Deal Pipeline",
            description="Use this to render a pipeline kanban or compute stage counts when summarising deal-flow health. Returns a dict keyed by stage with each stage's Deal array — same shape as /fundos/crm/.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),

        # ── FundOS: Transactions ────────────────────────────────────────────
        Tool(
            name="fundos_list_transactions",
            title="List Transactions",
            description="Use this to view term sheets and closings in flight when reporting on closing pipeline or chasing CPs. Optional status filter (drafting|negotiating|signed|funding|closed|cancelled). Returns Transaction objects.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string",
                               "description": "drafting, negotiating, signed, funding, closed, cancelled"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_draft_transaction",
            title="Draft Transaction",
            description="Use this to start a transaction record (term-sheet to closing) when a deal moves from diligence into negotiation. Seeds the default task pack. Always confirm parties + target_close_date with a human before issuing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "asset_class": {"type": "string"},
                    "deal_id": {"type": "integer"},
                    "linked_room_id": {"type": "integer"},
                    "target_close_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "parties": {"type": "array",
                                "items": {"type": "object",
                                          "properties": {"name": {"type": "string"},
                                                         "role": {"type": "string"},
                                                         "email": {"type": "string"}}}},
                    "seed_default_tasks": {"type": "boolean", "default": True},
                    "ephemeral": {"type": "boolean", "default": False},
                },
                "required": ["name"],
            },
            annotations=_WR,
        ),

        # ── FundOS: Pricer ──────────────────────────────────────────────────
        Tool(
            name="fundos_run_pricer",
            title="Run Asset Pricer",
            description="Use this to score an asset's economics when sizing a deal or comparing tranches. Inputs principal/term/coupon/spread/floor/ceiling/fees. Returns IRR, MOIC, WAL, full cashflow schedule, and waterfall splits.",
            inputSchema={
                "type": "object",
                "properties": {
                    "principal": {"type": "number"},
                    "term_months": {"type": "integer"},
                    "coupon_pct": {"type": "number"},
                    "spread_bps": {"type": "number"},
                    "benchmark_pct": {"type": "number"},
                    "floor_pct": {"type": "number"},
                    "ceiling_pct": {"type": "number"},
                    "amortisation": {"type": "string",
                                     "enum": ["bullet", "linear", "level"],
                                     "default": "bullet"},
                    "fees_upfront_pct": {"type": "number"},
                    "deal_id": {"type": "integer",
                                "description": "Optional — persist DealPricing row against this deal"},
                    "ephemeral": {"type": "boolean", "default": False},
                },
                "required": ["principal", "term_months"],
            },
            annotations=_WR,
        ),

        # ── FundOS: Risk / DSRI ─────────────────────────────────────────────
        Tool(
            name="fundos_list_covenants",
            title="List Covenants",
            description="Use this to enumerate covenants the org is monitoring when building a portfolio risk dashboard or before running covenant checks. Returns each covenant with type, threshold, current_value, and status (ok|breach|alert).",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="fundos_check_covenant",
            title="Check Covenant",
            description=("Use this to test a covenant value when fresh financials arrive or to simulate a what-if. "
                         "Pass covenant_id to update stored row + emit alerts; omit it for ephemeral simulation. "
                         "Returns {status, headroom, breach_severity}."),
            inputSchema={
                "type": "object",
                "properties": {
                    "covenant_id": {"type": "integer"},
                    "name": {"type": "string"},
                    "type": {"type": "string",
                             "description": "dscr, ltv, liquidity, ebitda, debt_ratio, custom"},
                    "direction": {"type": "string", "enum": ["min", "max"]},
                    "threshold": {"type": "number"},
                    "current_value": {"type": "number"},
                    "unit": {"type": "string"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_list_risk_alerts",
            title="List Risk Alerts",
            description="Use this to surface unresolved covenant breaches when triaging the daily risk inbox or driving an action queue. open=true filters to unresolved alerts only. Returns alert rows with covenant_id, severity, raised_at.",
            inputSchema={
                "type": "object",
                "properties": {"open": {"type": "boolean", "default": False}},
                "required": [],
            },
            annotations=_RO,
        ),

        # ── FundOS: Compliance OS ────────────────────────────────────────────
        Tool(
            name="fundos_list_kyc_records",
            title="List KYC Records",
            description=(
                "Use this to enumerate KYC/AML compliance records for all LPs when "
                "building a compliance dashboard or preparing a regulatory report. "
                "Optional status filter: pending | in_progress | approved | rejected | expired. "
                "Returns each record with lp_name, status, aml_status, risk_rating, "
                "expiry_date, pep_check, sanctions_check."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "pending | in_progress | approved | rejected | expired",
                    },
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_list_filings",
            title="List Regulatory Filing Deadlines",
            description=(
                "Use this to enumerate regulatory filing deadlines when tracking "
                "overdue or upcoming filings or preparing a compliance calendar. "
                "Optional status filter: upcoming | submitted | overdue | waived | not_applicable. "
                "Returns title, filing_type, jurisdiction, due_date, status, assigned_to."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "upcoming | submitted | overdue | waived | not_applicable",
                    },
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_check_restricted_list",
            title="Check Restricted Securities List",
            description=(
                "Use this to check whether a security (by ticker or ISIN) is on "
                "the firm's restricted list before approving a trade or pre-clearance request. "
                "Returns matching active restrictions with trade_restriction type and reason."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Security ticker symbol"},
                    "isin":   {"type": "string", "description": "ISIN identifier"},
                    "company_name": {"type": "string", "description": "Company name (partial match)"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_list_obligations",
            title="List Compliance Obligations",
            description=(
                "Use this to enumerate the obligations register when building a "
                "compliance work-plan or checking what is due. "
                "Optional filters: category (sec | cftc | fca | esma | gdpr | aml | other) "
                "and status (current | due_soon | overdue | completed | not_applicable). "
                "Returns title, category, jurisdiction, frequency, next_due_date, status, assigned_to."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "sec | cftc | fca | esma | gdpr | aml | other",
                    },
                    "status": {
                        "type": "string",
                        "description": "current | due_soon | overdue | completed | not_applicable",
                    },
                },
                "required": [],
            },
            annotations=_RO,
        ),

        # ── FundOS: ODD / VDR (BYOD-capable) ────────────────────────────────
        Tool(
            name="fundos_generate_odd",
            title="Generate ODD Answers",
            description=("Use this to draft ODD answers when an LP or consultant sends a DDQ. Source can be "
                         "inline documents (text in request) or an MCP BYOD source (connection_id + path). "
                         "Default ephemeral=true — outputs never persisted."),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "object",
                               "description": "{type: 'inline', documents: [...]} OR {type: 'mcp', connection_id, path}"},
                    "topics": {"type": "array", "items": {"type": "string"},
                               "description": "Optional subset of ODD topics to generate"},
                    "ephemeral": {"type": "boolean", "default": True},
                },
                "required": ["source"],
            },
            annotations=_WR,
        ),
        Tool(
            name="fundos_vdr_analyze",
            title="Analyze VDR Documents",
            description="Use this to surface risky clauses and extract entities (people, companies, valuations) from a doc bundle when speeding through diligence. Accepts inline docs or MCP BYOD source. Returns red_flags[] and entity_map.",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {"type": "object"},
                    "ephemeral": {"type": "boolean", "default": True},
                },
                "required": ["source"],
            },
            annotations=_RO,
        ),

        # ── FundOS: CIM Builder ─────────────────────────────────────────────
        Tool(
            name="fundos_list_cim_reports",
            title="List CIM Reports",
            description="Use this to list previously generated CIMs / teasers / one-pagers when the user asks 'what memos do we have?'. Returns each CIMReport with title, deal_id, status, template_key, updated_at.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="fundos_list_cim_templates",
            title="List CIM Templates",
            description="Use this to discover which CIM templates exist before calling fundos_generate_cim. Returns template keys (standard|teaser|onepager) and their section lists.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="fundos_generate_cim",
            title="Generate CIM",
            description=("Use this to draft a Confidential Information Memorandum from source docs when packaging a deal for IC or LPs. "
                         "Sections depend on template_key."),
            inputSchema={
                "type": "object",
                "properties": {
                    "template_key": {"type": "string",
                                     "enum": ["standard", "teaser", "onepager"],
                                     "default": "standard"},
                    "title": {"type": "string"},
                    "deal_id": {"type": "integer"},
                    "source": {"type": "object"},
                    "ephemeral": {"type": "boolean", "default": False},
                },
                "required": ["source"],
            },
            annotations=_WR,
        ),

        # ── FundOS: Investor Portal ─────────────────────────────────────────
        Tool(
            name="fundos_list_lps",
            title="List LP Investors",
            description="Use this to enumerate LPs when answering 'who has committed' or building per-LP rollups. Returns each LPInvestor with name, entity_type, committed_capital, deployed_capital, kyc_status.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="fundos_get_lp",
            title="Get LP Investor",
            description="Use this to load full LP detail (commitment, KYC, capital-call ledger) when answering an LP query or preparing a portal view. Returns LPInvestor + array of CapitalCall objects.",
            inputSchema={
                "type": "object",
                "properties": {"lp_id": {"type": "integer"}},
                "required": ["lp_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_create_capital_call",
            title="Create Capital Call",
            description="Use this to create a capital call against an LP commitment when funding an investment or paying expenses. **HUMAN APPROVAL REQUIRED** — drafts go to /fundos/investors/<lp_id> for review before LP-facing notice is issued.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lp_id": {"type": "integer"},
                    "amount": {"type": "number"},
                    "notice_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "status": {"type": "string", "default": "issued"},
                    "reference": {"type": "string"},
                    "ephemeral": {"type": "boolean", "default": False},
                },
                "required": ["lp_id", "amount"],
            },
            annotations=_WR,
        ),

        # ── FundOS: CFO Center ──────────────────────────────────────────────
        Tool(
            name="fundos_list_fund_accounts",
            title="List Fund Accounts",
            description="Use this to enumerate fund accounts and SPVs when picking a vehicle to compute P&L against or summarising AUM. Returns each FundAccount with current NAV and currency.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="fundos_compute_pnl",
            title="Compute P&L",
            description=("Use this to compute P&L and NAV over a date range for the books or an LP statement. Pass fund_account_id "
                         "(uses stored JournalEntries) OR inline entries array (headless)."),
            inputSchema={
                "type": "object",
                "properties": {
                    "fund_account_id": {"type": "integer"},
                    "start": {"type": "string", "description": "YYYY-MM-DD"},
                    "end": {"type": "string", "description": "YYYY-MM-DD"},
                    "entries": {"type": "array",
                                "items": {"type": "object"},
                                "description": "Inline headless entries [{date, category, debit, credit, description}]"},
                    "currency": {"type": "string"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_compute_waterfall",
            title="Compute Waterfall",
            description=("Use this to compute LP/GP splits at exit using the European waterfall when modelling a distribution or final payout. ROC → preferred return → "
                         "GP catch-up → carry split. Returns LP/GP totals + tier breakdown."),
            inputSchema={
                "type": "object",
                "properties": {
                    "distributable": {"type": "number"},
                    "committed": {"type": "number"},
                    "hurdle_pct": {"type": "number", "default": 0.08},
                    "carry_pct": {"type": "number", "default": 0.20},
                },
                "required": ["distributable", "committed"],
            },
            annotations=_RO,
        ),

        # ── FundOS: Syndication Engine ──────────────────────────────────────
        Tool(
            name="fundos_list_syndications",
            title="List Syndications",
            description="Use this to view active syndications when reporting raise progress or picking a syndication to allocate against. Returns each Syndication with status, target_amount, raised_to_date.",
            inputSchema={"type": "object", "properties": {}, "required": []},
            annotations=_RO,
        ),
        Tool(
            name="fundos_get_syndication",
            title="Get Syndication",
            description="Use this to inspect a single syndication and its allocation matrix when checking who's committed how much. Returns the Syndication record + array of SyndicationAllocation objects.",
            inputSchema={
                "type": "object",
                "properties": {"synd_id": {"type": "integer"}},
                "required": ["synd_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_allocate",
            title="Allocate to Syndication",
            description=("Use this to record investor allocations on a syndication when committing new LPs or topping up existing ones. Send a single object or "
                         "syndication. Send a single object or {allocations: [...]} for bulk."),
            inputSchema={
                "type": "object",
                "properties": {
                    "synd_id": {"type": "integer"},
                    "investor_name": {"type": "string"},
                    "lp_investor_id": {"type": "integer"},
                    "requested_amount": {"type": "number"},
                    "allocated_amount": {"type": "number"},
                    "kyc_status": {"type": "string", "default": "pending"},
                    "funds_status": {"type": "string", "default": "unsigned"},
                    "allocations": {"type": "array", "items": {"type": "object"},
                                    "description": "Optional bulk list — overrides single-object fields"},
                    "ephemeral": {"type": "boolean", "default": False},
                },
                "required": ["synd_id"],
            },
            annotations=_WR,
        ),

        # ── Tool-registry meta-tools ────────────────────────────────────────
        # Any tool registered via @tool in app.services.tools.* is callable
        # through these two meta-tools — lets MCP clients see new tools
        # without mcp_server.py needing a code change.
        Tool(
            name="fundos_list_tools",
            title="List FundOS Tools",
            description=("Use this to discover the full FundOS tool catalogue when an agent isn't sure which named tool to invoke. "
                         "Returns each tool's name, description, category, and JSON Schema."),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string",
                                 "description": "Optional filter: crm, lp_crm, vdr, cfo, risk, ..."},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="fundos_call_tool",
            title="Call FundOS Tool",
            description=("Use this to invoke any FundOS @tool by name when its inputs are known. The `args` object is "
                         "validated against the tool's JSON Schema. Approval-"
                         "required tools execute immediately over this path "
                         "(the MCP client holds an API key and is trusted)."),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string",
                             "description": "Tool name, e.g. 'cfo.compute_waterfall'"},
                    "args": {"type": "object",
                             "description": "Tool arguments matching its schema"},
                },
                "required": ["name"],
            },
            annotations=_WR,
        ),

        # ── DTCC ITP tools ───────────────────────────────────────────────────
        Tool(
            name="hf_ops_dtcc_get_trade_status",
            title="Get DTCC Trade Status",
            description=(
                "Use this to look up a CTM trade's live status when investigating "
                "a settlement break or reconciling a confirm. Hits the DTCC CTM "
                "upstream by ctm_ref. Returns the full trade record."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ctm_ref": {"type": "string",
                                "description": "DTCC CTM trade reference ID"},
                },
                "required": ["ctm_ref"],
            },
            annotations=_RO,
        ),
        Tool(
            name="hf_ops_dtcc_list_unaffirmed",
            title="List Unaffirmed Confirms",
            description=(
                "Use this to find unaffirmed TradeSuite confirms when chasing "
                "T+0 affirmation or building an ops worklist. Defaults to today "
                "if trade_date is omitted. Returns confirm rows."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "trade_date": {"type": "string",
                                   "description": "ISO date YYYY-MM-DD (optional, defaults to today)"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="hf_ops_dtcc_get_affirmation_scorecard",
            title="Get T+0 Affirmation Scorecard",
            description=(
                "Use this to get the T+0 affirmation scorecard when reporting "
                "ops health to the COO or PM. Derived from webhook events Kela "
                "has received — no live DTCC call. Returns affirmed_count, "
                "dk_count, match/unmatch counts, rate_pct."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "trade_date": {"type": "string",
                                   "description": "ISO date YYYY-MM-DD (optional, defaults to today)"},
                },
                "required": [],
            },
            annotations=_RO,
        ),
        Tool(
            name="hf_ops_dtcc_lookup_ssi",
            title="Lookup SSI",
            description=(
                "Use this to fetch a counterparty's Standing Settlement "
                "Instructions via DTCC ALERT when chasing a missing SSI on a "
                "settlement break. Pass counterparty_bic + optional account. "
                "Returns the SSI record."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "counterparty_bic": {"type": "string",
                                         "description": "BIC of the counterparty (8 or 11 chars)"},
                    "account":          {"type": "string",
                                         "description": "Account identifier (optional)"},
                },
                "required": ["counterparty_bic"],
            },
            annotations=_RO,
        ),

        # ── ChatGPT Deep Research aliases ───────────────────────────────────
        # These two tools have specific names + response shapes required by
        # ChatGPT's Deep Research connector contract. They wrap existing
        # `search_documents` and the new `/text` document endpoint.
        Tool(
            name="search",
            title="Search Documents",
            description=(
                "Use this to find Kela documents by query string when surfacing "
                "candidates for citation in a ChatGPT Deep Research workflow. "
                "Returns array of {id, title, url}. Pair with `fetch` to read "
                "full text."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
            annotations=_RO,
        ),
        Tool(
            name="fetch",
            title="Fetch Document Text",
            description=(
                "Use this to read a Kela document's full text after `search` "
                "returned its id, when grounding an answer or producing a "
                "citation. Returns {id, title, text, url, metadata}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Document id from `search`"},
                },
                "required": ["id"],
            },
            annotations=_RO,
        ),

        # ── OMS — Trading vertical ───────────────────────────────────────────
        Tool(
            name="oms_list_orders",
            title="List OMS Orders",
            description=(
                "Use this to read the order blotter when auditing recent trades, "
                "checking fill status, or building a trade summary. Optional "
                "status filter: NEW | SENT | PARTIAL | FILLED | CANCELLED | REJECTED. "
                "Returns the 50 most recent orders with fill details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Optional status filter"},
                    "fund_account_id": {"type": "integer", "description": "Filter by fund account"},
                    "limit": {"type": "integer", "description": "Max results (default 50, max 200)"},
                },
            },
            annotations=_RO,
        ),
        Tool(
            name="oms_get_order",
            title="Get OMS Order",
            description=(
                "Use this to load full detail on one order including all execution "
                "reports (fills, partial fills, cancels) when investigating a specific "
                "trade. Returns order fields plus executions array."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer", "description": "Order ID"},
                },
                "required": ["order_id"],
            },
            annotations=_RO,
        ),
        Tool(
            name="oms_create_order",
            title="Create OMS Order",
            description=(
                "Use this to submit a new equity order through the OMS when "
                "a human has approved the trade. Pre-trade compliance (restricted "
                "list, short locate, position limits) runs automatically. Returns "
                "the new order record; status BLOCKED means compliance rejected it. "
                "**HUMAN APPROVAL REQUIRED** before calling this tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Ticker symbol (e.g. AAPL)"},
                    "side": {"type": "string", "description": "BUY | SELL | SSHORT"},
                    "quantity": {"type": "number", "description": "Number of shares"},
                    "order_type": {"type": "string", "description": "LIMIT | MARKET"},
                    "limit_price": {"type": "number", "description": "Required for LIMIT orders"},
                    "tif": {"type": "string", "description": "DAY | GTC | IOC | FOK"},
                    "fund_account_id": {"type": "integer", "description": "Fund account to charge"},
                },
                "required": ["ticker", "side", "quantity"],
            },
            annotations=_WR,
        ),
        Tool(
            name="oms_list_positions",
            title="List OMS Positions",
            description=(
                "Use this to read the live position book when computing gross/net "
                "exposure, checking unrealized P&L, or building a portfolio snapshot. "
                "Returns all positions with last_price, unrealized_pnl, gross/net "
                "exposure in USD."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "fund_account_id": {"type": "integer", "description": "Filter by fund account"},
                },
            },
            annotations=_RO,
        ),
        Tool(
            name="oms_check_pretrade",
            title="Run Pre-trade Compliance Check",
            description=(
                "Use this to validate a proposed order against the org's compliance "
                "rules (restricted list, short locate, position limits) WITHOUT "
                "submitting it. Returns passed (bool), blocked (bool), warnings, "
                "errors, and a human-readable notes field. Use before oms_create_order."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "side": {"type": "string", "description": "BUY | SELL | SSHORT"},
                    "quantity": {"type": "number"},
                    "limit_price": {"type": "number"},
                    "fund_account_id": {"type": "integer"},
                },
                "required": ["ticker", "side", "quantity"],
            },
            annotations=_RO,
        ),
        Tool(
            name="oms_get_fix_status",
            title="Get FIX Session Status",
            description=(
                "Use this to check the FIX engine sidecar connectivity when "
                "troubleshooting order routing, reporting session health to the "
                "COO, or before submitting orders. Returns status, last_heartbeat, "
                "sequence numbers, and error_message."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "integer", "description": "Optional specific session ID"},
                },
            },
            annotations=_RO,
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        result = _dispatch_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except requests.HTTPError as e:
        return [TextContent(type="text", text=json.dumps({
            "error": str(e), "status_code": e.response.status_code if e.response else None
        }))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# ── Tool handlers ─────────────────────────────────────────────────────────────
# Each handler takes `args: dict` and returns a `dict | list`. They are registered
# in TOOL_DISPATCH below so _dispatch_tool() is a one-line lookup.

def _h_list_deal_rooms(args): return _get("/rooms")
def _h_get_deal_room(args): return _get(f"/rooms/{args['room_id']}")
def _h_create_deal_room(args):
    return _post("/rooms", {"name": args["name"],
                            "description": args.get("description", ""),
                            "status": args.get("status", "active")})

def _h_list_documents(args): return _get(f"/rooms/{args['room_id']}/documents")
def _h_get_document_metadata(args):
    return _get(f"/rooms/{args['room_id']}/documents/{args['doc_id']}")
def _h_get_document_download_url(args):
    return {"download_url": f"{API_BASE}/rooms/{args['room_id']}/documents/{args['doc_id']}/download",
            "note": "Use Bearer token in Authorization header to download"}
def _h_search_documents(args):
    params = {"q": args["query"]}
    if args.get("folder_id"):
        params["folder_id"] = args["folder_id"]
    return _get("/search", params=params)

def _h_search(args):
    """ChatGPT Deep Research adapter — returns [{id, title, url}, ...]."""
    data = _get("/search", params={"q": args["query"]})
    if isinstance(data, dict) and data.get("error"):
        return data
    out = []
    for r in (data or {}).get("results", []) or []:
        rid = r.get("id")
        room_id = r.get("room_id")
        if rid is None or room_id is None:
            continue
        out.append({
            "id": str(rid),
            "title": r.get("filename") or f"Document {rid}",
            "url": f"{BASE_URL}/api/v1/rooms/{room_id}/documents/{rid}/text",
        })
    return out

def _h_fetch(args):
    """ChatGPT Deep Research adapter — fetches one document's full text."""
    try:
        doc_id = int(args["id"])
    except (ValueError, TypeError):
        return {"error": f"invalid id: {args.get('id')!r}"}
    loc = _get(f"/documents/{doc_id}/locate")
    room_id = None
    if isinstance(loc, dict) and not loc.get("error"):
        room_id = (loc.get("data") or loc).get("room_id")
    if room_id is None:
        return {"error": f"could not resolve room for document {doc_id}",
                "hint": "Document may not be visible to this API key, "
                        "or /documents/<id>/locate is not deployed yet."}
    body = _get(f"/rooms/{room_id}/documents/{doc_id}/text")
    if isinstance(body, dict) and body.get("error"):
        return body
    return (body or {}).get("data", body)

def _h_list_room_members(args):
    data = _get(f"/rooms/{args['room_id']}")
    return {"members": data.get("data", {}).get("members", [])}
def _h_add_room_member(args):
    return _post(f"/rooms/{args['room_id']}", {
        "action": "add_member", "user_id": args["user_id"],
        "role": args.get("role", "member")})
def _h_list_users(args): return _get("/users")

def _h_get_audit_log(args):
    params = {}
    for k in ("action", "user_id", "page"):
        if args.get(k):
            params[k] = args[k]
    room_id = args.get("room_id", 1)
    return _get(f"/rooms/{room_id}/analytics/audit", params=params)
def _h_get_document_activity(args):
    return _get(f"/rooms/{args['room_id']}/analytics/documents")

def _h_get_signature_status(args):
    return {"note": "DocuSign envelopes", "room_id": args["room_id"]}

def _h_list_qa_questions(args):
    params = {}
    if args.get("status"):
        params["status"] = args["status"]
    return _get(f"/rooms/{args['room_id']}/qa", params=params)
def _h_answer_qa_question(args):
    return _post(f"/rooms/{args['room_id']}/qa/{args['question_id']}/answer",
                 {"body": args["answer"]})


# ── Shared helpers for FundOS handlers ────────────────────────────────────────

def _ephemeral_post(path: str, args: dict, *, default: bool = False,
                   strip_keys: tuple = ("ephemeral",)) -> dict:
    """POST helper for routes that accept ?ephemeral=true. Strips ephemeral
    and any caller-specified path-param keys from the body."""
    ephemeral = args.get("ephemeral", default)
    full_path = path + ("?ephemeral=true" if ephemeral else "")
    body = {k: v for k, v in args.items() if k not in strip_keys}
    return _post(full_path, body)


# ── FundOS: CRM ──────────────────────────────────────────────────────────────

def _h_fundos_list_deals(args):
    params = {}
    if args.get("stage"):
        params["stage"] = args["stage"]
    return _get("/fundos/crm/deals", params=params)
def _h_fundos_get_deal(args): return _get(f"/fundos/crm/deals/{args['deal_id']}")
def _h_fundos_create_deal(args):
    return _ephemeral_post("/fundos/crm/deals", args)
def _h_fundos_get_pipeline(args): return _get("/fundos/crm/pipeline")


# ── FundOS: Transactions / Pricer ────────────────────────────────────────────

def _h_fundos_list_transactions(args):
    params = {}
    if args.get("status"):
        params["status"] = args["status"]
    return _get("/fundos/transactions", params=params)
def _h_fundos_draft_transaction(args):
    return _ephemeral_post("/fundos/transactions/draft", args)
def _h_fundos_run_pricer(args):
    return _ephemeral_post("/fundos/pricer/run", args)


# ── FundOS: Risk / DSRI ──────────────────────────────────────────────────────

def _h_fundos_list_covenants(args): return _get("/fundos/risk/covenants")
def _h_fundos_check_covenant(args): return _post("/fundos/risk/check", args)
def _h_fundos_list_risk_alerts(args):
    params = {}
    if args.get("open"):
        params["open"] = "true"
    return _get("/fundos/risk/alerts", params=params)


# ── FundOS: Compliance OS ────────────────────────────────────────────────────

def _h_fundos_list_kyc_records(args):
    params = {"status": args["status"]} if args.get("status") else {}
    return _get("/fundos/compliance/kyc", params=params)
def _h_fundos_list_filings(args):
    params = {"status": args["status"]} if args.get("status") else {}
    return _get("/fundos/compliance/filings", params=params)
def _h_fundos_check_restricted_list(args):
    params = {}
    if args.get("ticker"):       params["ticker"] = args["ticker"]
    if args.get("isin"):         params["isin"] = args["isin"]
    if args.get("company_name"): params["q"] = args["company_name"]
    return _get("/fundos/compliance/trade/check", params=params)
def _h_fundos_list_obligations(args):
    params = {}
    if args.get("category"): params["category"] = args["category"]
    if args.get("status"):   params["status"] = args["status"]
    return _get("/fundos/compliance/obligations", params=params)


# ── FundOS: ODD / VDR (BYOD) / CIM ───────────────────────────────────────────

def _h_fundos_generate_odd(args):
    return _ephemeral_post("/fundos/odd/generate", args, default=True)
def _h_fundos_vdr_analyze(args):
    return _ephemeral_post("/fundos/vdr/analyze", args, default=True)
def _h_fundos_list_cim_reports(args): return _get("/fundos/cim/reports")
def _h_fundos_list_cim_templates(args): return _get("/fundos/cim/templates")
def _h_fundos_generate_cim(args):
    return _ephemeral_post("/fundos/cim/generate", args)


# ── FundOS: Investor Portal ──────────────────────────────────────────────────

def _h_fundos_list_lps(args): return _get("/fundos/investors/lp")
def _h_fundos_get_lp(args): return _get(f"/fundos/investors/lp/{args['lp_id']}")
def _h_fundos_create_capital_call(args):
    return _ephemeral_post(
        f"/fundos/investors/lp/{args['lp_id']}/capital-calls",
        args, strip_keys=("lp_id", "ephemeral"),
    )


# ── FundOS: CFO Center ───────────────────────────────────────────────────────

def _h_fundos_list_fund_accounts(args): return _get("/fundos/cfo/accounts")
def _h_fundos_compute_pnl(args): return _post("/fundos/cfo/report", args)
def _h_fundos_compute_waterfall(args): return _post("/fundos/cfo/waterfall", args)


# ── FundOS: Syndication ──────────────────────────────────────────────────────

def _h_fundos_list_syndications(args): return _get("/fundos/syndication")
def _h_fundos_get_syndication(args): return _get(f"/fundos/syndication/{args['synd_id']}")
def _h_fundos_allocate(args):
    return _ephemeral_post(
        f"/fundos/syndication/{args['synd_id']}/allocate",
        args, strip_keys=("synd_id", "ephemeral"),
    )


# ── Tool-registry meta-tools ─────────────────────────────────────────────────

def _h_fundos_list_tools(args):
    params = {"category": args["category"]} if args.get("category") else {}
    return _get("/api/v1/tools/", params=params)
def _h_fundos_call_tool(args):
    tool_name = args.get("name") or args.get("tool")
    if not tool_name:
        return {"error": "fundos_call_tool requires `name` (the tool to invoke)"}
    return _post(f"/api/v1/tools/{tool_name}/call", args.get("args") or {})


# ── DTCC ITP ─────────────────────────────────────────────────────────────────

def _h_hf_ops_dtcc_get_trade_status(args):
    return _get(f"/api/v1/hf-ops/dtcc/trade-status/{args['ctm_ref']}")
def _h_hf_ops_dtcc_list_unaffirmed(args):
    params = {"trade_date": args["trade_date"]} if args.get("trade_date") else {}
    return _get("/api/v1/hf-ops/dtcc/unaffirmed", params=params)
def _h_hf_ops_dtcc_get_affirmation_scorecard(args):
    params = {"trade_date": args["trade_date"]} if args.get("trade_date") else {}
    return _get("/api/v1/hf-ops/dtcc/scorecard", params=params)
def _h_hf_ops_dtcc_lookup_ssi(args):
    params = {"counterparty_bic": args["counterparty_bic"]}
    if args.get("account"):
        params["account"] = args["account"]
    return _get("/api/v1/hf-ops/dtcc/ssi", params=params)


# ── OMS / Trading tools ──────────────────────────────────────────────────────

def _h_oms_list_orders(args):
    params = {}
    if args.get("status"): params["status"] = args["status"]
    if args.get("fa_id"):  params["fa_id"] = args["fa_id"]
    return _get("/api/v1/fundos/oms/orders", params=params)
def _h_oms_get_order(args):
    return _get(f"/api/v1/fundos/oms/orders/{args['order_id']}")
def _h_oms_create_order(args):
    body = {
        "ticker": args["ticker"], "side": args["side"],
        "order_type": args["order_type"], "quantity": args["quantity"],
        "tif": args.get("tif", "DAY"),
    }
    for opt in ("limit_price", "fa_id", "broker", "account"):
        if args.get(opt) is not None:
            body[opt] = args[opt]
    return _post("/api/v1/fundos/oms/orders", body)
def _h_oms_list_positions(args):
    params = {"fa_id": args["fa_id"]} if args.get("fa_id") else {}
    return _get("/api/v1/fundos/oms/positions", params=params)
def _h_oms_check_pretrade(args):
    body = {"ticker": args["ticker"], "side": args["side"], "quantity": args["quantity"]}
    for opt in ("limit_price", "fa_id"):
        if args.get(opt) is not None:
            body[opt] = args[opt]
    return _post("/api/v1/fundos/oms/pretrade", body)
def _h_oms_get_fix_status(args): return _get("/api/v1/fundos/oms/fix-status")


# ── Dispatch table ───────────────────────────────────────────────────────────
# Tool name → handler function. Lookup is O(1). To add a tool: write _h_xxx
# above, then add one line here. Keep this grouped by domain for readability.

TOOL_DISPATCH = {
    # Deal Rooms / VDR core
    "list_deal_rooms":           _h_list_deal_rooms,
    "get_deal_room":             _h_get_deal_room,
    "create_deal_room":          _h_create_deal_room,
    # Documents
    "list_documents":            _h_list_documents,
    "get_document_metadata":     _h_get_document_metadata,
    "get_document_download_url": _h_get_document_download_url,
    "search_documents":          _h_search_documents,
    # ChatGPT Deep Research adapters
    "search":                    _h_search,
    "fetch":                     _h_fetch,
    # Users & access / audit / signatures / Q&A
    "list_room_members":         _h_list_room_members,
    "add_room_member":           _h_add_room_member,
    "list_users":                _h_list_users,
    "get_audit_log":             _h_get_audit_log,
    "get_document_activity":     _h_get_document_activity,
    "get_signature_status":      _h_get_signature_status,
    "list_qa_questions":         _h_list_qa_questions,
    "answer_qa_question":        _h_answer_qa_question,
    # FundOS — CRM
    "fundos_list_deals":         _h_fundos_list_deals,
    "fundos_get_deal":           _h_fundos_get_deal,
    "fundos_create_deal":        _h_fundos_create_deal,
    "fundos_get_pipeline":       _h_fundos_get_pipeline,
    # FundOS — Transactions / Pricer
    "fundos_list_transactions":  _h_fundos_list_transactions,
    "fundos_draft_transaction":  _h_fundos_draft_transaction,
    "fundos_run_pricer":         _h_fundos_run_pricer,
    # FundOS — Risk / DSRI
    "fundos_list_covenants":     _h_fundos_list_covenants,
    "fundos_check_covenant":     _h_fundos_check_covenant,
    "fundos_list_risk_alerts":   _h_fundos_list_risk_alerts,
    # FundOS — Compliance OS
    "fundos_list_kyc_records":   _h_fundos_list_kyc_records,
    "fundos_list_filings":       _h_fundos_list_filings,
    "fundos_check_restricted_list": _h_fundos_check_restricted_list,
    "fundos_list_obligations":   _h_fundos_list_obligations,
    # FundOS — ODD / VDR / CIM
    "fundos_generate_odd":       _h_fundos_generate_odd,
    "fundos_vdr_analyze":        _h_fundos_vdr_analyze,
    "fundos_list_cim_reports":   _h_fundos_list_cim_reports,
    "fundos_list_cim_templates": _h_fundos_list_cim_templates,
    "fundos_generate_cim":       _h_fundos_generate_cim,
    # FundOS — Investor Portal
    "fundos_list_lps":           _h_fundos_list_lps,
    "fundos_get_lp":              _h_fundos_get_lp,
    "fundos_create_capital_call": _h_fundos_create_capital_call,
    # FundOS — CFO
    "fundos_list_fund_accounts": _h_fundos_list_fund_accounts,
    "fundos_compute_pnl":        _h_fundos_compute_pnl,
    "fundos_compute_waterfall":  _h_fundos_compute_waterfall,
    # FundOS — Syndication
    "fundos_list_syndications":  _h_fundos_list_syndications,
    "fundos_get_syndication":    _h_fundos_get_syndication,
    "fundos_allocate":           _h_fundos_allocate,
    # Tool registry
    "fundos_list_tools":         _h_fundos_list_tools,
    "fundos_call_tool":          _h_fundos_call_tool,
    # DTCC ITP
    "hf_ops_dtcc_get_trade_status":           _h_hf_ops_dtcc_get_trade_status,
    "hf_ops_dtcc_list_unaffirmed":            _h_hf_ops_dtcc_list_unaffirmed,
    "hf_ops_dtcc_get_affirmation_scorecard":  _h_hf_ops_dtcc_get_affirmation_scorecard,
    "hf_ops_dtcc_lookup_ssi":                 _h_hf_ops_dtcc_lookup_ssi,
    # OMS / Trading
    "oms_list_orders":           _h_oms_list_orders,
    "oms_get_order":             _h_oms_get_order,
    "oms_create_order":          _h_oms_create_order,
    "oms_list_positions":        _h_oms_list_positions,
    "oms_check_pretrade":        _h_oms_check_pretrade,
    "oms_get_fix_status":        _h_oms_get_fix_status,
}


def _dispatch_tool(name: str, args: dict) -> dict:
    """Route tool calls to the appropriate handler. O(1) dict lookup."""
    handler = TOOL_DISPATCH.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name}"}
    return handler(args)


# ── Resources ────────────────────────────────────────────────────────────────

@server.list_resources()
async def list_resources():
    resources = [
        Resource(
            uri="fundos://rooms",
            name="Deal Rooms Index",
            description="Index of all deal rooms with IDs and status",
            mimeType="application/json",
        ),
        # FundOS top-level indexes
        Resource(
            uri="fundos://fundos/deals",
            name="FundOS — CRM Deals",
            description="Pipeline of all deals across the organisation",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/transactions",
            name="FundOS — Transactions",
            description="Active term-sheet drafts and closings",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/covenants",
            name="FundOS — Covenants",
            description="All tracked covenants with current status",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/alerts",
            name="FundOS — Risk Alerts",
            description="Open risk alerts from covenant breaches",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/lps",
            name="FundOS — LP Investors",
            description="Registered LP investors with commitments",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/capital-calls",
            name="FundOS — Capital Calls",
            description="Issued and outstanding capital calls",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/fund-accounts",
            name="FundOS — Fund Accounts",
            description="CFO Center — fund accounts and SPVs with NAV",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/syndications",
            name="FundOS — Syndications",
            description="Active and closed syndications",
            mimeType="application/json",
        ),
        Resource(
            uri="fundos://fundos/cim-reports",
            name="FundOS — CIM Reports",
            description="Generated CIM reports",
            mimeType="application/json",
        ),
    ]
    # Dynamically add room-specific resources
    try:
        data = _get("/rooms")
        rooms = data.get("data", [])
        for room in rooms[:20]:
            rid = room.get("id")
            rname = room.get("name", f"Room {rid}")
            resources.append(Resource(
                uri=f"fundos://rooms/{rid}",
                name=rname,
                description=f"Deal room '{rname}' — summary, members, doc count",
                mimeType="application/json",
            ))
            resources.append(Resource(
                uri=f"fundos://rooms/{rid}/documents",
                name=f"{rname} — Documents",
                description=f"Document index for deal room '{rname}'",
                mimeType="application/json",
            ))
            resources.append(Resource(
                uri=f"fundos://rooms/{rid}/members",
                name=f"{rname} — Members",
                description=f"Member list for deal room '{rname}'",
                mimeType="application/json",
            ))
    except Exception:
        pass
    return resources


_FUNDOS_RESOURCE_MAP = {
    "fundos://fundos/deals":          "/fundos/crm/deals",
    "fundos://fundos/transactions":   "/fundos/transactions",
    "fundos://fundos/covenants":      "/fundos/risk/covenants",
    "fundos://fundos/alerts":         "/fundos/risk/alerts?open=true",
    "fundos://fundos/lps":            "/fundos/investors/lp",
    "fundos://fundos/capital-calls":  "/fundos/investors/capital-calls",
    "fundos://fundos/fund-accounts":  "/fundos/cfo/accounts",
    "fundos://fundos/syndications":   "/fundos/syndication",
    "fundos://fundos/cim-reports":    "/fundos/cim/reports",
}


@server.read_resource()
async def read_resource(uri: str):
    uri = str(uri)
    try:
        if uri == "fundos://rooms":
            data = _get("/rooms")
            return json.dumps(data, indent=2, default=str)

        # FundOS resources
        if uri in _FUNDOS_RESOURCE_MAP:
            path = _FUNDOS_RESOURCE_MAP[uri]
            # Split path + query string for _get's params argument
            if "?" in path:
                base, qs = path.split("?", 1)
                params = {}
                for pair in qs.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
                data = _get(base, params=params)
            else:
                data = _get(path)
            return json.dumps(data, indent=2, default=str)

        if uri.startswith("fundos://rooms/"):
            parts = [p for p in uri.replace("fundos://rooms/", "").split("/") if p != ""]
            if not parts:
                return json.dumps({"error": f"Unknown resource: {uri}"})
            room_id = int(parts[0])
            if len(parts) == 1:
                # Room summary — the deal room itself.
                data = _get(f"/rooms/{room_id}")
                return json.dumps(data, indent=2, default=str)
            if parts[1] == "documents":
                data = _get(f"/rooms/{room_id}/documents")
                return json.dumps(data, indent=2, default=str)
            if parts[1] == "members":
                data = _get(f"/rooms/{room_id}")
                members = data.get("data", {}).get("members", [])
                return json.dumps({"room_id": room_id, "members": members}, indent=2, default=str)

        return json.dumps({"error": f"Unknown resource: {uri}"})
    except Exception as e:
        # Surface as a readable JSON resource body instead of letting the MCP
        # framework propagate, which causes Claude Desktop's opaque
        # "Failed to attach resource. You can try again." dialog.
        return json.dumps({
            "error": str(e),
            "uri": uri,
            "hint": "Check FUNDOS_API_KEY and FUNDOS_BASE_URL in your Claude Desktop MCP config.",
        })


# ── Main ─────────────────────────────────────────────────────────────────────

async def _main_stdio():
    logger.info("Starting FundOS MCP Server (stdio)")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def _main_sse():
    """Run the SSE transport. Synchronous on purpose — uvicorn.run manages
    its own event loop, so we must NOT call this from within asyncio.run.
    """
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route
    import uvicorn

    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    app = Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=sse.handle_post_message, methods=["POST"]),
    ])

    port = int(os.environ.get("MCP_PORT", "8080"))
    logger.info(f"Starting FundOS MCP Server (SSE) on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        _main_sse()
    else:
        import asyncio
        asyncio.run(_main_stdio())
