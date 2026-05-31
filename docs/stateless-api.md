# Stateless Document API

Generate fund documents via REST — no FundOS account, no fund data to configure. Send your data inline, get back a completed document.

## Get a key

Register at **https://kela.com/developers/register** — email + password, no card required. Your `doc_` key appears immediately on the dashboard. First 30 days free (all document types, unlimited calls).

Dashboard: **https://kela.com/developers/dashboard** — manage keys, see usage by document type, review monthly charges.

## Authentication

All five endpoints use Bearer auth with your `doc_` key:

```
Authorization: Bearer doc_your_key_here
Content-Type: application/json
```

## Endpoints

### POST /api/v1/documents/k1 — Schedule K-1 — $5/call

Complete IRS Form 1065 Schedule K-1 for any LP. Send partner data inline, get back HTML.

**Required fields:**
| Field | Type | Description |
|---|---|---|
| `fund_name` | string | Legal name of the fund |
| `tax_year` | integer | Tax year (e.g. 2025) |
| `partner_name` | string | LP / partner legal name |

**Optional fields (all default to 0 or empty):**
| Field | Type | Description |
|---|---|---|
| `fund_account_name` | string | Series or account name |
| `fund_ein` | string | Fund EIN (e.g. "82-1234567") |
| `partner_tin` | string | LP TIN |
| `partner_jurisdiction` | string | e.g. "Delaware" |
| `partner_entity_type` | string | e.g. "LLC" |
| `partner_committed_capital` | number | Total commitment |
| `partner_deployed_capital` | number | Amount deployed |
| `lp_share_pct` | number | Ownership fraction (0–1) |
| `capital_account_start` | number | Beginning capital |
| `contributions_year` | number | Capital contributed this year |
| `box_1_ordinary_income` | number | Box 1 — Ordinary income |
| `box_5_interest` | number | Box 5 — Interest income |
| `box_8_st_gain` | number | Box 8 — Short-term capital gain |
| `box_9a_lt_gain` | number | Box 9a — Long-term capital gain |
| `box_11_other_income` | number | Box 11 — Other income |
| `box_13_deductions` | number | Box 13 — Deductions |
| `box_20_notes` | string | Box 20 — Other notes |
| `distributions` | number | Total distributions (or use per-type breakdown below) |
| `dist_roc` | number | Return of capital distribution |
| `dist_income` | number | Income distribution |
| `dist_lt` | number | Long-term gain distribution |
| `dist_st` | number | Short-term gain distribution |
| `dist_recallable` | number | Recallable distribution |
| `format` | string | Output format — only `"html"` supported today |

**Minimal example:**
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
```

**Response:**
```json
{
  "html": "<!DOCTYPE html>...",
  "filename": "k1_2025_aksia_lp.html",
  "charged_usd": 5.00,
  "charge_reason": "charged"
}
```

> `charge_reason` will be `"trial_waived"` during the free trial period.

---

### POST /api/v1/documents/odd — ODD/DDQ Completion — $25/call

Kela's AI fills in DDQ answers from your fund information and the LP's questions.

**Simplified body (recommended):**
```json
{
  "fund_info": {
    "fund_name": "Eight Capital Fund II",
    "strategy": "Private credit — senior secured",
    "aum": 85000000,
    "team": ["Jane Smith (GP, 18yr PE)", "Mark Lee (CFO, 12yr)"],
    "vintage": 2021,
    "domicile": "Delaware"
  },
  "questions": [
    "Describe your investment process.",
    "What is your risk management framework?",
    "How do you manage conflicts of interest?"
  ]
}
```

**Full source passthrough (advanced):**
```json
{
  "source": {
    "type": "inline",
    "documents": [
      {"name": "fund_profile.txt", "text": "...full text of your fund documents..."}
    ]
  }
}
```

**Response:**
```json
{
  "answers": {
    "Describe your investment process.": "Eight Capital employs a three-stage process...",
    "What is your risk management framework?": "..."
  },
  "charged_usd": 25.00,
  "charge_reason": "charged",
  "token_usage": {"input_tokens": 1200, "output_tokens": 850}
}
```

---

### POST /api/v1/documents/analyze — Document Analysis — $3/call

Submit any document text — CIM, term sheet, subscription agreement — and get back red flags, an entity map, and a risk summary.

**Body:**
```json
{
  "documents": [
    {"name": "cim.pdf", "text": "...full extracted text of the document..."},
    {"name": "term_sheet.pdf", "text": "..."}
  ]
}
```

**Response:**
```json
{
  "summary": "This CIM describes a mid-market buyout strategy...",
  "red_flags": [
    "Unusual management fee structure (3% on committed capital)",
    "No key-man clause identified",
    "Conflicts of interest with affiliated entities not fully disclosed"
  ],
  "entity_map": {
    "fund": "Eight Capital Fund II",
    "gp": "Eight Capital Management LLC",
    "auditor": "Deloitte & Touche LLP",
    "lpa_law_firm": "Proskauer Rose LLP"
  },
  "charged_usd": 3.00
}
```

---

### POST /api/v1/documents/waterfall — European Waterfall — Free

European waterfall with hurdle, carry, and catchup. Returns LP/GP split by tier.

**Body:**
```json
{
  "distributable": 1000000,
  "committed": 1000000,
  "hurdle_pct": 8,
  "carry_pct": 20
}
```

> `hurdle_pct` and `carry_pct` accept either whole percentages (8 = 8%) or decimals (0.08 = 8%).

**Response:**
```json
{
  "total_distributed": 1000000,
  "lp_total": 916000,
  "gp_total": 84000,
  "charged_usd": 0.0,
  "tiers": [
    {"label": "Return of Capital", "distributed": 1000000, "lp_amount": 1000000, "gp_amount": 0, "lp_share": 1.0, "gp_share": 0.0},
    {"label": "Preferred Return (8%)", "distributed": 80000, "lp_amount": 80000, "gp_amount": 0, "lp_share": 1.0, "gp_share": 0.0},
    {"label": "GP Catch-Up", "distributed": 0, "lp_amount": 0, "gp_amount": 0, "lp_share": 0.0, "gp_share": 0.0},
    {"label": "Carried Interest (20%)", "distributed": 0, "lp_amount": 0, "gp_amount": 0, "lp_share": 0.0, "gp_share": 0.0}
  ]
}
```

---

### POST /api/v1/documents/pricer — IRR/MOIC/WAL Pricer — Free

Price a private credit or equity deal. Returns IRR, MOIC, WAL, and a full cashflow schedule.

**Body:**
```json
{
  "principal": 10000000,
  "term_months": 60,
  "coupon_pct": 0.08,
  "amortisation": "bullet",
  "fees_upfront_pct": 0.02
}
```

`amortisation` options: `"bullet"` (default), `"linear"`, `"level"`.

**Response:**
```json
{
  "irr": 0.0921,
  "moic": 1.45,
  "wal": 5.0,
  "cashflows": [
    {"period": 0, "cashflow": -10000000},
    {"period": 1, "cashflow": 66667},
    ...
  ],
  "charged_usd": 0.0
}
```

---

## Error responses

All errors follow the same shape:

```json
{"error": "description of what went wrong"}
```

| Status | Meaning |
|---|---|
| `400` | Missing required fields or invalid input |
| `401` | Missing or invalid API key |
| `403` | Key not associated with an account (register at kela.com/developers) |
| `429` | Rate limit — retry after a moment |
| `500` | Server error — retry with backoff |

---

## Pricing and trial

| Document | Price | Trial |
|---|---|---|
| Schedule K-1 | $5/call | Free (first 30 days) |
| ODD/DDQ | $25/call | Free (first 30 days) |
| Document analysis | $3/call | Free (first 30 days) |
| Waterfall | Free | Always free |
| Pricer | Free | Always free |

Charges are invoiced at end of month. If output fails, no charge. View monthly totals at https://kela.com/developers/dashboard.

---

## Developer dashboard

**https://kela.com/developers/dashboard**

- Create additional `doc_` keys (e.g. one per environment)
- Revoke compromised keys instantly
- View per-document-type usage counts this month
- Review charges — or confirm they're $0.00 during trial
- Copy your key once (shown in full on creation only)
