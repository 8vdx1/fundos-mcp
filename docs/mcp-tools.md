# FundOS MCP Tools Reference

Full reference for all 24 FundOS MCP tools. Tools are grouped by module.

---

## Deal Rooms & Documents (VDR)

### `list_deal_rooms`

List all deal rooms the caller can read.

**Arguments:** none

**Returns:** Array of `{id, name, status, member_count}`

**When to use:** Picking a room to inspect or act on; building a room inventory.

---

### `get_deal_room`

Get full metadata, member list, and document count for a single room.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |

**Returns:** Full room metadata + member list + document count.

---

### `create_deal_room`

Create a new deal room. **Requires human approval.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | yes | Room name (e.g. "Series A") |
| `description` | string | no | Room description |
| `status` | string | no | `active` (default), `draft`, or `closed` |

**Returns:** New room `id` and `slug`.

---

### `list_documents`

List documents in a room, optionally filtered to a folder.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `folder_id` | number | no | Narrow to a specific folder |

**Returns:** Documents with `file_type`, `size`, `uploaded_at`.

---

### `get_document_metadata`

Inspect a single document's metadata.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `doc_id` | number | yes | Document ID |

**Returns:** `filename`, `file_type`, `upload_date`, `view_count`, `ai_classification`, `tags`.

---

### `get_document_download_url`

Get a short-lived download URL for a document.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `doc_id` | number | yes | Document ID |

**Returns:** Short-lived URL pointing at the VDR download endpoint.

---

### `search_documents`

Answer a free-form question over deal-room documents with AI citations.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | yes | Question or search query |
| `folder_id` | number | no | Narrow search to a specific folder |

**Returns:** AI-grounded answer with document citations.

---

### `list_room_members`

List members of a deal room with their roles and per-folder permissions.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |

**Returns:** `user_id`, `email`, `role`, per-folder permissions.

---

### `add_room_member`

Add a user to a deal room. **Requires human approval.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `user_id` | number | yes | User ID to add |
| `role` | string | no | `member` (default) or `manager` |

---

### `list_users`

Enumerate all users in the organisation.

**Arguments:** none

**Returns:** `id`, `email`, `role`, `is_admin`, `is_active` for every user.

---

### `get_audit_log`

Inspect activity history, filterable by action, user, or room.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `action` | string | no | Filter: `VIEW`, `DOWNLOAD`, `UPLOAD`, `LOGIN`, `DELETE` |
| `user_id` | number | no | Filter by user |
| `room_id` | number | no | Filter by deal room |
| `page` | number | no | Pagination (default 1) |

---

### `get_document_activity`

Per-document engagement: who viewed it, when, and for how long.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `doc_id` | number | yes | Document ID |

**Returns:** Per-viewer timestamps, view durations, IPs.

---

### `get_signature_status`

Check DocuSign envelope status for all envelopes in a room.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |

**Returns:** Per-envelope status: `sent`, `signed`, `declined`, or `voided`.

---

### `list_qa_questions`

Read the diligence Q&A queue, optionally filtered by status.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `status` | string | no | `open`, `in_progress`, `answered`, or `closed` |

**Returns:** `title`, `asker`, `priority`, `due_date`.

---

### `answer_qa_question`

Publish an answer to a diligence Q&A question. **Visible to the asking LP — review before posting.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `room_id` | number | yes | Deal room ID |
| `question_id` | number | yes | Question ID |
| `answer` | string | yes | Answer text |

---

## Deal CRM + Transactions + Pricer

### `fundos_list_deals`

Read the deal pipeline.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `stage` | string | no | `sourcing`, `qualification`, `dd`, `ic`, `closing`, `closed`, `lost` |

**Returns:** Array of Deal objects.

---

### `fundos_get_deal`

Load full detail on a single deal.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `deal_id` | number | yes | Deal ID |

**Returns:** Deal record with counterparty, target size, stage, IRR target, notes.

---

### `fundos_create_deal`

Add a deal to the pipeline. Set `ephemeral=true` to dry-run. **Requires human approval for persistence.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | yes | Deal name |
| `counterparty` | string | no | Counterparty name |
| `stage` | string | no | Pipeline stage (default `sourcing`) |
| `target_size` | number | no | Target deal size |
| `asset_class` | string | no | `private_credit`, `private_equity`, `real_estate`, `infra`, `venture`, `secondaries`, `other` |
| `irr_target` | number | no | Target IRR |
| `notes` | string | no | Notes |
| `currency` | string | no | ISO currency (default `USD`) |
| `ephemeral` | boolean | no | Validate without writing (default `false`) |

---

### `fundos_get_pipeline`

Get deals grouped by stage for a kanban view.

**Arguments:** none

**Returns:** Dict keyed by stage, each containing that stage's Deal array.

---

### `fundos_list_transactions`

View term sheets and closings in flight.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `status` | string | no | `drafting`, `negotiating`, `signed`, `funding`, `closed`, `cancelled` |

---

### `fundos_draft_transaction`

Start a transaction record with default task pack. **Requires human approval.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | yes | Transaction name |
| `deal_id` | number | no | Link to a deal |
| `parties` | array | no | `[{name, email, role}]` |
| `target_close_date` | string | no | `YYYY-MM-DD` |
| `linked_room_id` | number | no | Link to a VDR room |
| `asset_class` | string | no | Asset class |
| `seed_default_tasks` | boolean | no | Seed default task list (default `true`) |
| `ephemeral` | boolean | no | Validate without writing |

---

### `fundos_run_pricer`

Score an asset: IRR, MOIC, WAL, cashflow schedule, waterfall splits.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `principal` | number | yes | Principal amount |
| `term_months` | number | yes | Term in months |
| `coupon_pct` | number | no | Coupon rate % |
| `spread_bps` | number | no | Spread over benchmark in bps |
| `benchmark_pct` | number | no | Benchmark rate % |
| `floor_pct` | number | no | Rate floor % |
| `ceiling_pct` | number | no | Rate ceiling % |
| `fees_upfront_pct` | number | no | Upfront fee % |
| `amortisation` | string | no | `bullet` (default), `linear`, or `level` |
| `deal_id` | number | no | Persist DealPricing row against this deal |
| `ephemeral` | boolean | no | Don't persist (default `false`) |

**Returns:** IRR, MOIC, WAL, full cashflow schedule, waterfall splits.

---

## Risk

### `fundos_list_covenants`

List all covenants being monitored.

**Arguments:** none

**Returns:** Each covenant with `type`, `threshold`, `current_value`, `status` (`ok`, `breach`, or `alert`).

---

### `fundos_check_covenant`

Test a covenant value — update stored state or run an ephemeral simulation.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `current_value` | number | yes | Value to test |
| `threshold` | number | yes | Threshold to test against |
| `direction` | string | yes | `min` or `max` |
| `name` | string | yes | Covenant name |
| `type` | string | yes | `dscr`, `ltv`, `liquidity`, `ebitda`, `debt_ratio`, `custom` |
| `unit` | string | no | Unit label |
| `covenant_id` | number | no | Update stored row (omit for ephemeral simulation) |

**Returns:** `{status, headroom, breach_severity}`

---

### `fundos_list_risk_alerts`

Surface unresolved covenant breaches.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `open` | boolean | no | Filter to unresolved alerts only (default `false`) |

**Returns:** Alert rows with `covenant_id`, `severity`, `raised_at`.

---

## ODD / Diligence / CIM

### `fundos_generate_odd`

Draft ODD answers from a DDQ. Always ephemeral by default — outputs are never persisted.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `source` | object | yes | `{type: "inline", documents: [...]}` or `{type: "mcp", connection_id, path}` |
| `topics` | array | no | Subset of ODD topics to generate |
| `ephemeral` | boolean | no | Default `true` |

---

### `fundos_vdr_analyze`

Surface risky clauses and extract entities from a document bundle.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `source` | object | yes | `{type: "inline", documents: [...]}` or `{type: "mcp", connection_id, path}` |
| `ephemeral` | boolean | no | Default `true` |

**Returns:** `red_flags[]` and `entity_map`.

---

### `fundos_list_cim_reports`

List previously generated CIMs, teasers, and one-pagers.

**Arguments:** none

**Returns:** Each CIMReport with `title`, `deal_id`, `status`, `template_key`, `updated_at`.

---

### `fundos_list_cim_templates`

Discover available CIM templates before generating.

**Arguments:** none

**Returns:** Template keys (`standard`, `teaser`, `onepager`) and their section lists.

---

### `fundos_generate_cim`

Draft a CIM from source documents.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `source` | object | yes | Inline docs or MCP BYOD source |
| `template_key` | string | no | `standard` (default), `teaser`, or `onepager` |
| `title` | string | no | CIM title |
| `deal_id` | number | no | Link to a deal |
| `ephemeral` | boolean | no | Default `false` |

---

## Investor Portal (LP CRM)

### `fundos_list_lps`

Enumerate LP investors.

**Arguments:** none

**Returns:** Each LPInvestor with `name`, `entity_type`, `committed_capital`, `deployed_capital`, `kyc_status`.

---

### `fundos_get_lp`

Load full LP detail: commitment, KYC status, capital-call ledger.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lp_id` | number | yes | LP investor ID |

**Returns:** LPInvestor record + array of CapitalCall objects.

---

### `fundos_create_capital_call`

Issue a capital call against an LP commitment. **Requires human approval — affects LP cash.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `lp_id` | number | yes | LP investor ID |
| `amount` | number | yes | Call amount |
| `due_date` | string | no | `YYYY-MM-DD` |
| `notice_date` | string | no | `YYYY-MM-DD` |
| `reference` | string | no | Reference string |
| `status` | string | no | Default `issued` |
| `ephemeral` | boolean | no | Validate without writing |

---

## CFO Center

### `fundos_list_fund_accounts`

Enumerate fund accounts and SPVs.

**Arguments:** none

**Returns:** Each FundAccount with current NAV and currency.

---

### `fundos_compute_pnl`

Compute P&L and NAV over a date range.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `fund_account_id` | number | no | Use stored journal entries for this account |
| `entries` | array | no | Inline entries `[{date, category, debit, credit, description}]` |
| `start` | string | no | `YYYY-MM-DD` |
| `end` | string | no | `YYYY-MM-DD` |
| `currency` | string | no | ISO currency |

---

### `fundos_compute_waterfall`

Compute LP/GP splits using the European waterfall model.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `distributable` | number | yes | Total distributable proceeds |
| `committed` | number | yes | Total committed capital |
| `hurdle_pct` | number | no | Preferred return hurdle (default `0.08`) |
| `carry_pct` | number | no | GP carry percentage (default `0.20`) |

**Returns:** LP/GP totals + tier breakdown (ROC → pref return → GP catch-up → carry split).

---

## Syndication

### `fundos_list_syndications`

List active syndications and their raise progress.

**Arguments:** none

**Returns:** Each Syndication with `status`, `target_amount`, `raised_to_date`.

---

### `fundos_get_syndication`

Inspect a single syndication and its full allocation matrix.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `synd_id` | number | yes | Syndication ID |

**Returns:** Syndication record + array of SyndicationAllocation objects.

---

### `fundos_allocate`

Record investor allocations on a syndication. **Requires human approval.**

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `synd_id` | number | yes | Syndication ID |
| `lp_investor_id` | number | no | LP investor ID |
| `investor_name` | string | no | Investor name |
| `requested_amount` | number | no | Amount requested |
| `allocated_amount` | number | no | Amount allocated |
| `kyc_status` | string | no | Default `pending` |
| `funds_status` | string | no | Default `unsigned` |
| `allocations` | array | no | Bulk list — overrides single-object fields |
| `ephemeral` | boolean | no | Validate without writing |

---

## HF Ops (DTCC ITP)

### `hf_ops_dtcc_get_trade_status`

Look up a CTM trade's live status by `ctm_ref`.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `ctm_ref` | string | yes | DTCC CTM trade reference ID |

**Returns:** Full trade record from DTCC CTM upstream.

---

### `hf_ops_dtcc_list_unaffirmed`

Find unaffirmed TradeSuite confirms, defaulting to today.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `trade_date` | string | no | `YYYY-MM-DD` (defaults to today) |

**Returns:** Confirm rows still pending affirmation.

---

### `hf_ops_dtcc_get_affirmation_scorecard`

Get the T+0 affirmation scorecard for a given trade date.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `trade_date` | string | no | `YYYY-MM-DD` (defaults to today) |

**Returns:** `affirmed_count`, `dk_count`, match/unmatch counts, `rate_pct`.

---

### `hf_ops_dtcc_lookup_ssi`

Fetch a counterparty's Standing Settlement Instructions via DTCC ALERT.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `counterparty_bic` | string | yes | BIC of the counterparty (8 or 11 chars) |
| `account` | string | no | Account identifier |

**Returns:** SSI record.

---

## Generic / Catalogue / Search

### `fundos_list_tools`

Discover the full FundOS tool catalogue.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `category` | string | no | Filter by category: `crm`, `lp_crm`, `vdr`, `cfo`, `risk`, ... |

**Returns:** Each tool's name, description, category, and JSON Schema.

---

### `fundos_call_tool`

Invoke any FundOS tool by name with validated arguments.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | yes | Tool name, e.g. `cfo.compute_waterfall` |
| `args` | object | no | Tool arguments matching its schema |

---

### `search`

ChatGPT Deep Research search adapter — find Kela documents by query.

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | yes | Search query |

**Returns:** Array of `{id, title, url}`.

---

### `fetch`

Read a Kela document's full text by ID (pair with `search`).

**Arguments:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `id` | string | yes | Document ID from `search` |

**Returns:** `{id, title, text, url, metadata}`

---

## Actions requiring human approval

The following tools are dual-use. Never execute these without an explicit human confirmation:

| Tool | Reason |
|------|--------|
| `create_deal_room` | Expands access to sensitive data |
| `add_room_member` | Expands access to sensitive data |
| `answer_qa_question` | Visible to LP — review before posting |
| `fundos_create_deal` | Creates pipeline records |
| `fundos_draft_transaction` | Starts a transaction + task pack |
| `fundos_create_capital_call` | Affects LP cash |
| `fundos_allocate` | Commits investor allocations |

For all write operations, passing `ephemeral: true` (where supported) validates the input and returns the expected output shape without persisting anything to the database.
