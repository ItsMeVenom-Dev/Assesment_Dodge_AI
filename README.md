# SAP Order-to-Cash Graph Query System

A full-stack MVP that lets you query SAP O2C business data in natural language,
backed by SQLite and an LLM (Gemini 2.0 Flash or Groq), with a live graph visualization.

## 🚀 Live Demo

Frontend: https://assesment-dodge-5xlmc0e3r-itsmevenom-devs-projects.vercel.app/

Backend API: https://assesment-dodge-ai.onrender.com/docs


## Screenshot
<img width="1919" height="879" alt="image" src="https://github.com/user-attachments/assets/ca5942c3-bcc2-43ef-97e8-00be63a8a4c8" />


**All 19 dataset tables are loaded and queryable.**

---

## Architecture

```
graph-query-system/
├── .env                        ← your API keys (fill this in, never commit)
├── .env.example                ← safe template
├── .gitignore
├── README.md
├── backend/
│   ├── main.py                 ← FastAPI: LLM, SQL, all 19 table schema
│   ├── requirements.txt
│   └── data/
│       └── sap_o2c.db          ← pre-built SQLite (21,393 rows across 19 tables)
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── App.jsx / App.module.css
│       ├── index.css / main.jsx
│       └── components/
│           ├── Graph.jsx        ← SVG force-directed graph (8 node types)
│           ├── Chat.jsx         ← Chat + SQL + results table
│           └── StatsBar.jsx     ← 12 live metrics from DB
├── scripts/
│   └── load_dataset.py         ← ETL: all 19 JSONL folders → SQLite
└── data/
    └── sap-o2c-data/           ← extract zip here
```

---

## All 19 Tables
Dataset: (https://drive.google.com/file/d/1UqaLbFaveV-3MEuiUrzKydhKmkeC1iAL/view)

| # | Table | Rows | Description |
|---|-------|------|-------------|
| 1 | `business_partners` | 8 | Customer/partner master data |
| 2 | `business_partner_addresses` | 8 | City, country, region per partner |
| 3 | `customer_company_assignments` | 8 | Payment terms, reconciliation accounts |
| 4 | `customer_sales_area_assignments` | 28 | Currency, delivery priority, credit area |
| 5 | `plants` | 44 | Plant master: name, sales org, location |
| 6 | `products` | 69 | Product master: type, weight, group |
| 7 | `product_descriptions` | 69 | Human-readable product names (EN) |
| 8 | `product_plants` | 3,036 | Product ↔ plant assignments, profit center |
| 9 | `product_storage_locations` | 16,723 | Stock locations per product/plant |
| 10 | `sales_order_headers` | 100 | SO header: customer, amount, status |
| 11 | `sales_order_items` | 167 | Line items: material, quantity, amount |
| 12 | `sales_order_schedule_lines` | 179 | Confirmed delivery dates per item |
| 13 | `outbound_delivery_headers` | 86 | Delivery: picking status, goods movement |
| 14 | `outbound_delivery_items` | 137 | Delivery items linked back to sales orders |
| 15 | `billing_document_headers` | 163 | Invoice header: amount, date, status |
| 16 | `billing_document_items` | 245 | Invoice line items per material |
| 17 | `billing_document_cancellations` | 80 | Cancelled invoices (separate table) |
| 18 | `payments_accounts_receivable` | 120 | AR payments: clearing date, GL account |
| 19 | `journal_entry_items_accounts_receivable` | 123 | Journal entries for AR |
| | **TOTAL** | **21,393** | |

---

## Architecture Decisions

### Database: SQLite
- Zero-config, file-based — ideal for a self-contained demo.
- The pre-built `sap_o2c.db` ships with the project; no setup needed.
- For production, the same DDL and queries work on PostgreSQL with minimal changes.

### LLM Prompting Strategy (Two-Pass)

**Pass 1 — Text → SQL** (`generate_sql`):
- Full 19-table schema fed verbatim to the model, including exact column names, types, and PK/FK relationships.
- Explicit join hints in the prompt for the tricky SAP foreign key patterns (e.g. delivery items → sales orders via `referenceSdDocument`, not a direct FK column named `salesOrder`).
- Model told to return *only* raw SQL — no markdown, no explanation.
- Includes data-type hints (dates stored as ISO strings, booleans stored as `"true"`/`"false"` strings).

**Pass 2 — Results → Human Answer** (`humanize`):
- SQL + first 10 result rows fed back.
- Asked for a 2–4 sentence business answer with specific numbers.
- Technical SQL language explicitly suppressed.

### Guardrails
1. **Keyword whitelist** — 40+ domain terms checked before any LLM call. Off-topic queries (e.g. "capital of France") are rejected immediately.
2. **SELECT-only** — regex gate ensures generated SQL starts with `SELECT`. Any mutation attempt is blocked at the app layer.
3. **Row limit** — LLM prompted to `LIMIT 20` by default to prevent expensive full-table scans on the 16k-row `product_storage_locations` table.

### Graph Visualization
- Pure SVG with a custom JS force-directed simulation (no D3/external lib).
- 8 node types: customer, sales_order, delivery, billing, payment, product, plant, journal.
- Nodes and edges sourced from real DB relationships at startup.
- Query results return entity IDs → matched against graph nodes → highlighted with glow + edge color.
- Zoom/pan via wheel + drag.

---

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gemini API key (free at https://ai.google.dev) **or** Groq API key (free at https://console.groq.com)

### 1 — Configure environment

```bash
# .env is already included, just fill in your key:
# Edit .env → set GEMINI_API_KEY (or GROQ_API_KEY + LLM_PROVIDER=groq)
```

### 2 — (Optional) Re-load the dataset from raw files

The DB is already pre-built. Only do this if you want to reload from JSONL:

```
Extract sap-order-to-cash-dataset.zip → data/sap-o2c-data/ (19 folders)
```
```bash
pip install python-dotenv
python scripts/load_dataset.py
```

### 3 — Start backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### 4 — Start frontend

```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:3000
```

---

## API Reference

| Method | Endpoint      | Description |
|--------|---------------|-------------|
| POST   | `/query`      | NL → SQL → LLM answer + highlighted nodes |
| GET    | `/graph-data` | Nodes and edges for visualization |
| GET    | `/stats`      | 12 live metrics from the DB |
| GET    | `/health`     | Health check |
| GET    | `/docs`       | Swagger UI |

---

## Sample Queries

- `Top 5 customers by total order amount`
- `Show cancelled billing documents`
- `Products with their descriptions and product group`
- `Which plants are linked to sales organization ABCD?`
- `Orders with delivery blocked — show customer and amount`
- `List all payments cleared in April 2025`
- `Product storage locations for plant 1001`
- `Sales orders pending billing`
- `Schedule lines with confirmed delivery dates`
- `Billing documents not yet paid — join with AR`

---

## Environment Variables

| Variable         | Required       | Description |
|------------------|----------------|-------------|
| `LLM_PROVIDER`   | Yes            | `gemini` or `groq` |
| `GEMINI_API_KEY` | If gemini      | https://ai.google.dev |
| `GROQ_API_KEY`   | If groq        | https://console.groq.com |
| `DB_PATH`        | No (has default) | Path to SQLite DB |
| `DATASET_PATH`   | No (for loader)  | Path to extracted zip |
| `VITE_API_URL`   | No             | Frontend API URL (proxied in dev) |
