import os, sqlite3, json, re
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "./data/sap_o2c.db")).resolve()

app = FastAPI(title="SAP O2C Graph Query System", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SCHEMA = """
SQLite database: SAP Order-to-Cash (O2C) — 19 tables

business_partners
  businessPartner(PK), customer, businessPartnerCategory, businessPartnerFullName,
  businessPartnerName, industry, createdByUser, creationDate, businessPartnerIsBlocked,
  isMarkedForArchiving

business_partner_addresses
  businessPartner→business_partners, addressId, cityName, country, postalCode,
  region, streetName, transportZone, addressTimeZone

customer_company_assignments
  customer→business_partners, companyCode, paymentTerms, reconciliationAccount,
  paymentBlockingReason, customerAccountGroup, deletionIndicator

customer_sales_area_assignments
  customer→business_partners, salesOrganization, distributionChannel, division,
  currency, customerPaymentTerms, deliveryPriority, incotermsClassification,
  creditControlArea, shippingCondition, supplyingPlant, billingIsBlockedForCustomer

plants
  plant(PK), plantName, valuationArea, salesOrganization, distributionChannel,
  division, factoryCalendar, language, isMarkedForArchiving

products
  product(PK), productType, productGroup, baseUnit, division, industrySector,
  grossWeight, netWeight, weightUnit, creationDate, isMarkedForDeletion

product_descriptions
  product→products, language, productDescription
  (Use this to get human-readable product names)

product_plants
  product→products, plant→plants, profitCenter, mrpType,
  availabilityCheckType, countryOfOrigin

product_storage_locations
  product→products, plant→plants, storageLocation,
  physicalInventoryBlockInd, dateOfLastPostedCntUnRstrcdStk

sales_order_headers
  salesOrder(PK), salesOrderType, salesOrganization, soldToParty→business_partners,
  creationDate, totalNetAmount, transactionCurrency, overallDeliveryStatus,
  overallOrdReltdBillgStatus, requestedDeliveryDate, customerPaymentTerms,
  headerBillingBlockReason, deliveryBlockReason, totalCreditCheckStatus

sales_order_items
  salesOrder→sales_order_headers, salesOrderItem, material→products,
  requestedQuantity, requestedQuantityUnit, netAmount, transactionCurrency,
  materialGroup, productionPlant, storageLocation, itemBillingBlockReason,
  salesDocumentRjcnReason (rejection reason)

sales_order_schedule_lines
  salesOrder→sales_order_headers, salesOrderItem, scheduleLine,
  confirmedDeliveryDate, confdOrderQtyByMatlAvailCheck, orderQuantityUnit

outbound_delivery_headers
  deliveryDocument(PK), creationDate, shippingPoint, deliveryBlockReason,
  overallGoodsMovementStatus, overallPickingStatus, overallProofOfDeliveryStatus,
  actualGoodsMovementDate, hdrGeneralIncompletionStatus

outbound_delivery_items
  deliveryDocument→outbound_delivery_headers, deliveryDocumentItem,
  referenceSdDocument→sales_order_headers.salesOrder,   ← KEY JOIN
  referenceSdDocumentItem, actualDeliveryQuantity, plant, storageLocation

billing_document_headers
  billingDocument(PK), billingDocumentType, billingDocumentDate, creationDate,
  totalNetAmount, transactionCurrency, companyCode, fiscalYear, accountingDocument,
  soldToParty→business_partners, billingDocumentIsCancelled, cancelledBillingDocument

billing_document_items
  billingDocument→billing_document_headers, billingDocumentItem,
  material→products, billingQuantity, billingQuantityUnit, netAmount,
  referenceSdDocument→sales_order_headers.salesOrder   ← KEY JOIN

billing_document_cancellations
  billingDocument(PK), billingDocumentType, billingDocumentDate,
  cancelledBillingDocument→billing_document_headers.billingDocument,
  totalNetAmount, transactionCurrency, soldToParty, companyCode, fiscalYear,
  billingDocumentIsCancelled

payments_accounts_receivable
  accountingDocument, accountingDocumentItem, fiscalYear,
  customer→business_partners, salesDocument→sales_order_headers.salesOrder,
  amountInTransactionCurrency, transactionCurrency, amountInCompanyCodeCurrency,
  clearingDate, postingDate, glAccount, profitCenter, invoiceReference

journal_entry_items_accounts_receivable
  accountingDocument, accountingDocumentItem, fiscalYear,
  customer→business_partners, glAccount, referenceDocument,
  amountInTransactionCurrency, amountInCompanyCodeCurrency,
  postingDate, clearingDate, accountingDocumentType, profitCenter, costCenter


  orders → customer:    sales_order_headers.soldToParty = business_partners.businessPartner
  order → delivery:     outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder
  order → billing:      billing_document_items.referenceSdDocument = sales_order_headers.salesOrder
  order → payment:      payments_accounts_receivable.salesDocument = sales_order_headers.salesOrder
  product names:        JOIN product_descriptions pd ON pd.product = <table>.material AND pd.language = 'EN'
  product → plant:      product_plants.product = products.product AND product_plants.plant = plants.plant
  cancellations:        billing_document_cancellations.cancelledBillingDocument = billing_document_headers.billingDocument
"""

KEYWORDS = [
    "order","sales","customer","partner","delivery","billing","invoice","payment",
    "product","material","shipment","dispatch","amount","revenue","quantity","plant",
    "warehouse","storage","location","document","clearing","journal","account",
    "receivable","credit","fiscal","currency","schedule","status","region","country",
    "city","total","net","gross","overdue","pending","completed","cancelled","blocked",
    "sap","o2c","erp","company","organization","description","profit","center","cost",
    "cancellation","picking","goods","movement","incoterms","payment term",
]


def call_llm(prompt: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        return client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt).text.strip()
    elif provider == "groq":
        from groq import Groq
        resp = Groq(api_key=os.environ["GROQ_API_KEY"]).chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def generate_sql(query: str) -> str:
    prompt = f"""You are a SQLite expert working with a SAP Order-to-Cash database.
Convert the user's natural language question into a valid SQLite SELECT query.

{SCHEMA}

Rules:
- Return ONLY the raw SQL query. No markdown, no backticks, no explanation.
- Only SELECT queries are allowed.
- Use proper JOINs. See KEY JOIN PATTERNS above for correct join paths.
- To get product names, join product_descriptions with language = 'EN'.
- Limit results to 20 rows unless user asks for more.
- Column names are case-sensitive (use exact names from schema).
- Dates are stored as ISO strings e.g. "2025-03-31T00:00:00.000Z".
- billingDocumentIsCancelled is stored as "true" or "false" (strings).
- For cancelled billing docs, use billing_document_cancellations table.

User question: {query}

SQL:"""
    return call_llm(prompt)


def humanize(query: str, sql: str, rows: list, cols: list) -> str:
    if not rows:
        return "No records found in the SAP O2C database matching your query."
    sample = [dict(zip(cols, r)) for r in rows[:10]]
    prompt = f"""You are a concise SAP business analyst. Answer the user's question based on the SQL query results.

User question: {query}
SQL executed: {sql}
Results ({len(rows)} row(s) total, first {len(sample)} shown):
{json.dumps(sample, indent=2, default=str)}

Write a clear, direct 2-4 sentence business answer with specific numbers/values.
Do not mention SQL or technical details. Focus on business meaning."""
    return call_llm(prompt)


def extract_nodes(rows: list, cols: list) -> list:
    id_map = {
        "salesorder": "sales_order",
        "deliverydocument": "delivery",
        "billingdocument": "billing",
        "businesspartner": "customer",
        "customer": "customer",
        "soldtoparty": "customer",
        "product": "product",
        "material": "product",
        "plant": "plant",
        "accountingdocument": "payment",
    }
    seen, result = set(), []
    for row in rows[:20]:
        for i, col in enumerate(cols):
            key = col.lower().replace("_", "")
            if key in id_map and row[i] and str(row[i]) not in seen:
                seen.add(str(row[i]))
                result.append({"id": str(row[i]), "type": id_map[key]})
    return result


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class QueryRequest(BaseModel):
    query: str

@app.get("/health")
def health():
    return {"status": "ok", "db": str(DB_PATH), "db_exists": DB_PATH.exists()}


@app.post("/query")
def run_query(req: QueryRequest):
    q = req.query.strip()
    if not q:
        return {"answer": "Please enter a question.", "sql": None,
                "rows": [], "highlighted_nodes": [], "columns": []}

    if not any(kw in q.lower() for kw in KEYWORDS):
        return {
            "answer": "This system is designed to answer dataset-related queries only.",
            "sql": None, "rows": [], "highlighted_nodes": [], "columns": [],
        }

    sql = ""
    try:
        raw = generate_sql(q)
        sql = re.sub(r"```(?:sql)?|```", "", raw).strip().rstrip(";")

        if not re.match(r"^\s*SELECT", sql, re.IGNORECASE):
            return {"answer": "Only SELECT queries are permitted.",
                    "sql": sql, "rows": [], "highlighted_nodes": [], "columns": []}

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()

        raw_rows = [list(r) for r in rows]
        answer = humanize(q, sql, raw_rows, cols)

        return {
            "answer": answer,
            "sql": sql,
            "rows": [dict(zip(cols, r)) for r in raw_rows[:20]],
            "columns": cols,
            "highlighted_nodes": extract_nodes(raw_rows, cols),
        }

    except sqlite3.OperationalError as e:
        return {"answer": f"Database error: {e}", "sql": sql,
                "rows": [], "highlighted_nodes": [], "columns": []}
    except Exception as e:
        return {"answer": f"Error: {e}", "sql": sql,
                "rows": [], "highlighted_nodes": [], "columns": []}


@app.get("/graph-data")
def graph_data():
    if not DB_PATH.exists():
        return {"nodes": [], "edges": [],
                "error": "DB not found. Run: python scripts/load_dataset.py"}
    conn = get_conn()
    c = conn.cursor()
    nodes, edges, seen = [], [], set()

    def node(nid, label, ntype, data=None):
        nid = str(nid)
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "type": ntype, "data": data or {}})

    c.execute("""
        SELECT bp.businessPartner, bp.businessPartnerFullName, bp.industry,
               bpa.cityName, bpa.country
        FROM business_partners bp
        LEFT JOIN business_partner_addresses bpa ON bpa.businessPartner = bp.businessPartner
        LIMIT 6
    """)
    for r in c.fetchall():
        node(r[0], r[1] or r[0], "customer",
             {"industry": r[2], "city": r[3], "country": r[4]})

    c.execute("SELECT plant, plantName, salesOrganization FROM plants LIMIT 4")
    for r in c.fetchall():
        node(r[0], r[1] or r[0], "plant",
             {"salesOrg": r[2]})

    c.execute("""
        SELECT salesOrder, soldToParty, totalNetAmount, transactionCurrency,
               overallDeliveryStatus, creationDate
        FROM sales_order_headers LIMIT 10
    """)
    for r in c.fetchall():
        node(r[0], f"SO-{r[0]}", "sales_order",
             {"amount": r[2], "currency": r[3], "dlvStatus": r[4], "date": r[5]})
        if str(r[1]) in seen:
            edges.append({"source": str(r[1]), "target": str(r[0]), "label": "placed"})

    c.execute("""
        SELECT p.product, pd.productDescription, p.productGroup, p.industrySector
        FROM products p
        LEFT JOIN product_descriptions pd ON pd.product = p.product AND pd.language = 'EN'
        LIMIT 5
    """)
    for r in c.fetchall():
        node(r[0], (r[1] or r[0])[:18], "product",
             {"group": r[2], "sector": r[3]})

    c.execute("""
        SELECT DISTINCT salesOrder, material FROM sales_order_items
        WHERE material IS NOT NULL LIMIT 10
    """)
    for r in c.fetchall():
        if str(r[0]) in seen and str(r[1]) in seen:
            edges.append({"source": str(r[0]), "target": str(r[1]), "label": "contains"})

    c.execute("""
        SELECT odh.deliveryDocument, odi.referenceSdDocument,
               odh.overallGoodsMovementStatus, odh.shippingPoint
        FROM outbound_delivery_headers odh
        JOIN outbound_delivery_items odi ON odi.deliveryDocument = odh.deliveryDocument
        LIMIT 8
    """)
    for r in c.fetchall():
        node(r[0], f"DEL-{r[0]}", "delivery",
             {"status": r[2], "shippingPoint": r[3]})
        if str(r[1]) in seen:
            edges.append({"source": str(r[1]), "target": str(r[0]), "label": "shipped_via"})

    c.execute("""
        SELECT bdh.billingDocument, bdi.referenceSdDocument,
               bdh.totalNetAmount, bdh.billingDocumentDate, bdh.billingDocumentIsCancelled
        FROM billing_document_headers bdh
        JOIN billing_document_items bdi ON bdi.billingDocument = bdh.billingDocument
        LIMIT 8
    """)
    for r in c.fetchall():
        node(r[0], f"BILL-{r[0]}", "billing",
             {"amount": r[2], "date": r[3], "cancelled": r[4]})
        if str(r[1]) in seen:
            edges.append({"source": str(r[1]), "target": str(r[0]), "label": "billed_as"})

    c.execute("""
        SELECT accountingDocument, salesDocument, customer,
               amountInTransactionCurrency, transactionCurrency, clearingDate
        FROM payments_accounts_receivable LIMIT 6
    """)
    for r in c.fetchall():
        node(r[0], f"PAY-{r[0]}", "payment",
             {"amount": r[3], "currency": r[4], "cleared": r[5]})
        if str(r[1]) in seen:
            edges.append({"source": str(r[1]), "target": str(r[0]), "label": "paid_by"})

    conn.close()
    return {"nodes": nodes[:30], "edges": edges}


@app.get("/stats")
def stats():
    if not DB_PATH.exists():
        return {}
    conn = get_conn()
    c = conn.cursor()
    result = {}
    queries = [
        ("customers",       "SELECT COUNT(*) FROM business_partners"),
        ("orders",          "SELECT COUNT(*) FROM sales_order_headers"),
        ("order_items",     "SELECT COUNT(*) FROM sales_order_items"),
        ("deliveries",      "SELECT COUNT(*) FROM outbound_delivery_headers"),
        ("billings",        "SELECT COUNT(*) FROM billing_document_headers WHERE billingDocumentIsCancelled = 'false'"),
        ("cancellations",   "SELECT COUNT(*) FROM billing_document_cancellations"),
        ("payments",        "SELECT COUNT(*) FROM payments_accounts_receivable"),
        ("products",        "SELECT COUNT(*) FROM products"),
        ("plants",          "SELECT COUNT(*) FROM plants"),
        ("storage_locs",    "SELECT COUNT(*) FROM product_storage_locations"),
        ("total_billed",    "SELECT ROUND(SUM(totalNetAmount),2) FROM billing_document_headers WHERE billingDocumentIsCancelled = 'false'"),
        ("total_paid",      "SELECT ROUND(SUM(amountInTransactionCurrency),2) FROM payments_accounts_receivable"),
    ]
    for key, sql in queries:
        try:
            c.execute(sql)
            result[key] = c.fetchone()[0]
        except Exception:
            result[key] = 0
    conn.close()
    return result
