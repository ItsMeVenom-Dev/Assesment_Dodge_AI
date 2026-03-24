
import json, glob, os, sqlite3, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR     = Path(__file__).resolve().parent.parent
DATASET_PATH = Path(os.getenv("DATASET_PATH", str(BASE_DIR / "data" / "sap-o2c-data")))
DB_PATH      = Path(os.getenv("DB_PATH",      str(BASE_DIR / "backend" / "data" / "sap_o2c.db")))

DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def read_jsonl(folder):
    records = []
    for f in sorted(glob.glob(str(folder / "*.jsonl"))):
        with open(f, encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return records


def clean(value):
    if isinstance(value, dict):
        return json.dumps(value)
    if isinstance(value, bool):
        return str(value).lower()
    return value


def load_table(conn, table, records, cols, ddl):
    conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.execute(ddl)
    if not records:
        print(f"  {table}: 0 rows (empty folder)")
        return
    placeholders = ",".join("?" * len(cols))
    rows = [tuple(clean(r.get(c)) for c in cols) for r in records]
    conn.executemany(f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows)
    print(f"  ✓  {table}: {len(rows)} rows")


TABLE_DEFS = [

("business_partners",
 ["businessPartner","customer","businessPartnerCategory","businessPartnerFullName",
  "businessPartnerGrouping","businessPartnerName","correspondenceLanguage",
  "createdByUser","creationDate","creationTime","firstName","formOfAddress",
  "industry","lastChangeDate","lastName","organizationBpName1","organizationBpName2",
  "businessPartnerIsBlocked","isMarkedForArchiving"],
 """CREATE TABLE business_partners (
    businessPartner TEXT PRIMARY KEY, customer TEXT,
    businessPartnerCategory TEXT, businessPartnerFullName TEXT,
    businessPartnerGrouping TEXT, businessPartnerName TEXT,
    correspondenceLanguage TEXT, createdByUser TEXT, creationDate TEXT,
    creationTime TEXT, firstName TEXT, formOfAddress TEXT, industry TEXT,
    lastChangeDate TEXT, lastName TEXT, organizationBpName1 TEXT,
    organizationBpName2 TEXT, businessPartnerIsBlocked TEXT, isMarkedForArchiving TEXT
)"""),

("business_partner_addresses",
 ["businessPartner","addressId","validityStartDate","validityEndDate","addressUuid",
  "addressTimeZone","cityName","country","poBox","poBoxDeviatingCityName",
  "poBoxDeviatingCountry","poBoxDeviatingRegion","poBoxIsWithoutNumber",
  "poBoxLobbyName","poBoxPostalCode","postalCode","region","streetName",
  "taxJurisdiction","transportZone"],
 """CREATE TABLE business_partner_addresses (
    businessPartner TEXT, addressId TEXT, validityStartDate TEXT, validityEndDate TEXT,
    addressUuid TEXT, addressTimeZone TEXT, cityName TEXT, country TEXT,
    poBox TEXT, poBoxDeviatingCityName TEXT, poBoxDeviatingCountry TEXT,
    poBoxDeviatingRegion TEXT, poBoxIsWithoutNumber TEXT, poBoxLobbyName TEXT,
    poBoxPostalCode TEXT, postalCode TEXT, region TEXT, streetName TEXT,
    taxJurisdiction TEXT, transportZone TEXT,
    PRIMARY KEY (businessPartner, addressId)
)"""),

("customer_company_assignments",
 ["customer","companyCode","accountingClerk","accountingClerkFaxNumber",
  "accountingClerkInternetAddress","accountingClerkPhoneNumber",
  "alternativePayerAccount","paymentBlockingReason","paymentMethodsList",
  "paymentTerms","reconciliationAccount","deletionIndicator","customerAccountGroup"],
 """CREATE TABLE customer_company_assignments (
    customer TEXT, companyCode TEXT, accountingClerk TEXT,
    accountingClerkFaxNumber TEXT, accountingClerkInternetAddress TEXT,
    accountingClerkPhoneNumber TEXT, alternativePayerAccount TEXT,
    paymentBlockingReason TEXT, paymentMethodsList TEXT, paymentTerms TEXT,
    reconciliationAccount TEXT, deletionIndicator TEXT, customerAccountGroup TEXT,
    PRIMARY KEY (customer, companyCode)
)"""),

("customer_sales_area_assignments",
 ["customer","salesOrganization","distributionChannel","division",
  "billingIsBlockedForCustomer","completeDeliveryIsDefined","creditControlArea",
  "currency","customerPaymentTerms","deliveryPriority","incotermsClassification",
  "incotermsLocation1","salesGroup","salesOffice","shippingCondition",
  "slsUnlmtdOvrdelivIsAllwd","supplyingPlant","salesDistrict","exchangeRateType"],
 """CREATE TABLE customer_sales_area_assignments (
    customer TEXT, salesOrganization TEXT, distributionChannel TEXT, division TEXT,
    billingIsBlockedForCustomer TEXT, completeDeliveryIsDefined TEXT,
    creditControlArea TEXT, currency TEXT, customerPaymentTerms TEXT,
    deliveryPriority TEXT, incotermsClassification TEXT, incotermsLocation1 TEXT,
    salesGroup TEXT, salesOffice TEXT, shippingCondition TEXT,
    slsUnlmtdOvrdelivIsAllwd TEXT, supplyingPlant TEXT, salesDistrict TEXT,
    exchangeRateType TEXT,
    PRIMARY KEY (customer, salesOrganization, distributionChannel, division)
)"""),

("plants",
 ["plant","plantName","valuationArea","plantCustomer","plantSupplier",
  "factoryCalendar","defaultPurchasingOrganization","salesOrganization",
  "addressId","plantCategory","distributionChannel","division","language",
  "isMarkedForArchiving"],
 """CREATE TABLE plants (
    plant TEXT PRIMARY KEY, plantName TEXT, valuationArea TEXT,
    plantCustomer TEXT, plantSupplier TEXT, factoryCalendar TEXT,
    defaultPurchasingOrganization TEXT, salesOrganization TEXT,
    addressId TEXT, plantCategory TEXT, distributionChannel TEXT,
    division TEXT, language TEXT, isMarkedForArchiving TEXT
)"""),

("products",
 ["product","productType","crossPlantStatus","crossPlantStatusValidityDate",
  "creationDate","createdByUser","lastChangeDate","lastChangeDateTime",
  "isMarkedForDeletion","productOldId","grossWeight","weightUnit","netWeight",
  "productGroup","baseUnit","division","industrySector"],
 """CREATE TABLE products (
    product TEXT PRIMARY KEY, productType TEXT, crossPlantStatus TEXT,
    crossPlantStatusValidityDate TEXT, creationDate TEXT, createdByUser TEXT,
    lastChangeDate TEXT, lastChangeDateTime TEXT, isMarkedForDeletion TEXT,
    productOldId TEXT, grossWeight REAL, weightUnit TEXT, netWeight REAL,
    productGroup TEXT, baseUnit TEXT, division TEXT, industrySector TEXT
)"""),

("product_descriptions",
 ["product","language","productDescription"],
 """CREATE TABLE product_descriptions (
    product TEXT, language TEXT, productDescription TEXT,
    PRIMARY KEY (product, language)
)"""),

("product_plants",
 ["product","plant","countryOfOrigin","regionOfOrigin",
  "productionInvtryManagedLoc","availabilityCheckType",
  "fiscalYearVariant","profitCenter","mrpType"],
 """CREATE TABLE product_plants (
    product TEXT, plant TEXT, countryOfOrigin TEXT, regionOfOrigin TEXT,
    productionInvtryManagedLoc TEXT, availabilityCheckType TEXT,
    fiscalYearVariant TEXT, profitCenter TEXT, mrpType TEXT,
    PRIMARY KEY (product, plant)
)"""),

("product_storage_locations",
 ["product","plant","storageLocation","physicalInventoryBlockInd",
  "dateOfLastPostedCntUnRstrcdStk"],
 """CREATE TABLE product_storage_locations (
    product TEXT, plant TEXT, storageLocation TEXT,
    physicalInventoryBlockInd TEXT, dateOfLastPostedCntUnRstrcdStk TEXT,
    PRIMARY KEY (product, plant, storageLocation)
)"""),

("sales_order_headers",
 ["salesOrder","salesOrderType","salesOrganization","distributionChannel",
  "organizationDivision","salesGroup","salesOffice","soldToParty","creationDate",
  "createdByUser","lastChangeDateTime","totalNetAmount","overallDeliveryStatus",
  "overallOrdReltdBillgStatus","overallSdDocReferenceStatus","transactionCurrency",
  "pricingDate","requestedDeliveryDate","headerBillingBlockReason","deliveryBlockReason",
  "incotermsClassification","incotermsLocation1","customerPaymentTerms","totalCreditCheckStatus"],
 """CREATE TABLE sales_order_headers (
    salesOrder TEXT PRIMARY KEY, salesOrderType TEXT, salesOrganization TEXT,
    distributionChannel TEXT, organizationDivision TEXT, salesGroup TEXT,
    salesOffice TEXT, soldToParty TEXT, creationDate TEXT, createdByUser TEXT,
    lastChangeDateTime TEXT, totalNetAmount REAL, overallDeliveryStatus TEXT,
    overallOrdReltdBillgStatus TEXT, overallSdDocReferenceStatus TEXT,
    transactionCurrency TEXT, pricingDate TEXT, requestedDeliveryDate TEXT,
    headerBillingBlockReason TEXT, deliveryBlockReason TEXT,
    incotermsClassification TEXT, incotermsLocation1 TEXT,
    customerPaymentTerms TEXT, totalCreditCheckStatus TEXT
)"""),

("sales_order_items",
 ["salesOrder","salesOrderItem","salesOrderItemCategory","material",
  "requestedQuantity","requestedQuantityUnit","transactionCurrency","netAmount",
  "materialGroup","productionPlant","storageLocation","salesDocumentRjcnReason",
  "itemBillingBlockReason"],
 """CREATE TABLE sales_order_items (
    salesOrder TEXT, salesOrderItem TEXT, salesOrderItemCategory TEXT,
    material TEXT, requestedQuantity REAL, requestedQuantityUnit TEXT,
    transactionCurrency TEXT, netAmount REAL, materialGroup TEXT,
    productionPlant TEXT, storageLocation TEXT, salesDocumentRjcnReason TEXT,
    itemBillingBlockReason TEXT,
    PRIMARY KEY (salesOrder, salesOrderItem)
)"""),

("sales_order_schedule_lines",
 ["salesOrder","salesOrderItem","scheduleLine","confirmedDeliveryDate",
  "orderQuantityUnit","confdOrderQtyByMatlAvailCheck"],
 """CREATE TABLE sales_order_schedule_lines (
    salesOrder TEXT, salesOrderItem TEXT, scheduleLine TEXT,
    confirmedDeliveryDate TEXT, orderQuantityUnit TEXT,
    confdOrderQtyByMatlAvailCheck REAL,
    PRIMARY KEY (salesOrder, salesOrderItem, scheduleLine)
)"""),

("outbound_delivery_headers",
 ["actualGoodsMovementDate","actualGoodsMovementTime","creationDate","creationTime",
  "deliveryBlockReason","deliveryDocument","hdrGeneralIncompletionStatus",
  "headerBillingBlockReason","lastChangeDate","overallGoodsMovementStatus",
  "overallPickingStatus","overallProofOfDeliveryStatus","shippingPoint"],
 """CREATE TABLE outbound_delivery_headers (
    actualGoodsMovementDate TEXT, actualGoodsMovementTime TEXT,
    creationDate TEXT, creationTime TEXT, deliveryBlockReason TEXT,
    deliveryDocument TEXT PRIMARY KEY, hdrGeneralIncompletionStatus TEXT,
    headerBillingBlockReason TEXT, lastChangeDate TEXT,
    overallGoodsMovementStatus TEXT, overallPickingStatus TEXT,
    overallProofOfDeliveryStatus TEXT, shippingPoint TEXT
)"""),

("outbound_delivery_items",
 ["actualDeliveryQuantity","batch","deliveryDocument","deliveryDocumentItem",
  "deliveryQuantityUnit","itemBillingBlockReason","lastChangeDate","plant",
  "referenceSdDocument","referenceSdDocumentItem","storageLocation"],
 """CREATE TABLE outbound_delivery_items (
    actualDeliveryQuantity REAL, batch TEXT, deliveryDocument TEXT,
    deliveryDocumentItem TEXT, deliveryQuantityUnit TEXT,
    itemBillingBlockReason TEXT, lastChangeDate TEXT, plant TEXT,
    referenceSdDocument TEXT, referenceSdDocumentItem TEXT, storageLocation TEXT,
    PRIMARY KEY (deliveryDocument, deliveryDocumentItem)
)"""),

("billing_document_headers",
 ["billingDocument","billingDocumentType","creationDate","creationTime",
  "lastChangeDateTime","billingDocumentDate","billingDocumentIsCancelled",
  "cancelledBillingDocument","totalNetAmount","transactionCurrency",
  "companyCode","fiscalYear","accountingDocument","soldToParty"],
 """CREATE TABLE billing_document_headers (
    billingDocument TEXT PRIMARY KEY, billingDocumentType TEXT,
    creationDate TEXT, creationTime TEXT, lastChangeDateTime TEXT,
    billingDocumentDate TEXT, billingDocumentIsCancelled TEXT,
    cancelledBillingDocument TEXT, totalNetAmount REAL, transactionCurrency TEXT,
    companyCode TEXT, fiscalYear TEXT, accountingDocument TEXT, soldToParty TEXT
)"""),

("billing_document_items",
 ["billingDocument","billingDocumentItem","material","billingQuantity",
  "billingQuantityUnit","netAmount","transactionCurrency",
  "referenceSdDocument","referenceSdDocumentItem"],
 """CREATE TABLE billing_document_items (
    billingDocument TEXT, billingDocumentItem TEXT, material TEXT,
    billingQuantity REAL, billingQuantityUnit TEXT, netAmount REAL,
    transactionCurrency TEXT, referenceSdDocument TEXT, referenceSdDocumentItem TEXT,
    PRIMARY KEY (billingDocument, billingDocumentItem)
)"""),

("billing_document_cancellations",
 ["billingDocument","billingDocumentType","creationDate","creationTime",
  "lastChangeDateTime","billingDocumentDate","billingDocumentIsCancelled",
  "cancelledBillingDocument","totalNetAmount","transactionCurrency",
  "companyCode","fiscalYear","accountingDocument","soldToParty"],
 """CREATE TABLE billing_document_cancellations (
    billingDocument TEXT PRIMARY KEY, billingDocumentType TEXT,
    creationDate TEXT, creationTime TEXT, lastChangeDateTime TEXT,
    billingDocumentDate TEXT, billingDocumentIsCancelled TEXT,
    cancelledBillingDocument TEXT, totalNetAmount REAL, transactionCurrency TEXT,
    companyCode TEXT, fiscalYear TEXT, accountingDocument TEXT, soldToParty TEXT
)"""),

("payments_accounts_receivable",
 ["companyCode","fiscalYear","accountingDocument","accountingDocumentItem",
  "clearingDate","clearingAccountingDocument","clearingDocFiscalYear",
  "amountInTransactionCurrency","transactionCurrency","amountInCompanyCodeCurrency",
  "companyCodeCurrency","customer","invoiceReference","invoiceReferenceFiscalYear",
  "salesDocument","salesDocumentItem","postingDate","documentDate",
  "assignmentReference","glAccount","financialAccountType","profitCenter","costCenter"],
 """CREATE TABLE payments_accounts_receivable (
    companyCode TEXT, fiscalYear TEXT, accountingDocument TEXT,
    accountingDocumentItem TEXT, clearingDate TEXT, clearingAccountingDocument TEXT,
    clearingDocFiscalYear TEXT, amountInTransactionCurrency REAL,
    transactionCurrency TEXT, amountInCompanyCodeCurrency REAL,
    companyCodeCurrency TEXT, customer TEXT, invoiceReference TEXT,
    invoiceReferenceFiscalYear TEXT, salesDocument TEXT, salesDocumentItem TEXT,
    postingDate TEXT, documentDate TEXT, assignmentReference TEXT,
    glAccount TEXT, financialAccountType TEXT, profitCenter TEXT, costCenter TEXT,
    PRIMARY KEY (accountingDocument, accountingDocumentItem, fiscalYear)
)"""),

("journal_entry_items_accounts_receivable",
 ["companyCode","fiscalYear","accountingDocument","glAccount","referenceDocument",
  "costCenter","profitCenter","transactionCurrency","amountInTransactionCurrency",
  "companyCodeCurrency","amountInCompanyCodeCurrency","postingDate","documentDate",
  "accountingDocumentType","accountingDocumentItem","assignmentReference",
  "lastChangeDateTime","customer","financialAccountType","clearingDate",
  "clearingAccountingDocument","clearingDocFiscalYear"],
 """CREATE TABLE journal_entry_items_accounts_receivable (
    companyCode TEXT, fiscalYear TEXT, accountingDocument TEXT, glAccount TEXT,
    referenceDocument TEXT, costCenter TEXT, profitCenter TEXT,
    transactionCurrency TEXT, amountInTransactionCurrency REAL,
    companyCodeCurrency TEXT, amountInCompanyCodeCurrency REAL,
    postingDate TEXT, documentDate TEXT, accountingDocumentType TEXT,
    accountingDocumentItem TEXT, assignmentReference TEXT, lastChangeDateTime TEXT,
    customer TEXT, financialAccountType TEXT, clearingDate TEXT,
    clearingAccountingDocument TEXT, clearingDocFiscalYear TEXT,
    PRIMARY KEY (accountingDocument, accountingDocumentItem, fiscalYear)
)"""),

]

FOLDER_MAP = {td[0]: td[0] for td in TABLE_DEFS}


def main():
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        print("Extract sap-order-to-cash-dataset.zip to data/sap-o2c-data/ first.")
        sys.exit(1)

    print(f"Loading dataset from : {DATASET_PATH}")
    print(f"Target DB            : {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    table_lookup = {name: (cols, ddl) for name, cols, ddl in TABLE_DEFS}

    for folder_name in FOLDER_MAP:
        folder = DATASET_PATH / folder_name
        if not folder.exists():
            print(f"  ⚠  {folder_name}: folder not found, skipping")
            continue
        records = read_jsonl(folder)
        cols, ddl = table_lookup[folder_name]
        load_table(conn, folder_name, records, cols, ddl)

    conn.commit()

    print("\nRow counts")
    cur = conn.cursor()
    total_rows = 0
    for name, _, _ in TABLE_DEFS:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {name}")
            n = cur.fetchone()[0]
            total_rows += n
            print(f"  {name:<45} {n:>6}")
        except Exception as e:
            print(f"  {name:<45}  ERROR: {e}")

    conn.close()
    print(f"\n  TOTAL ROWS: {total_rows}")
    print(f"\n✅  Database ready: {DB_PATH}")


if __name__ == "__main__":
    main()
