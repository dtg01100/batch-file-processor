"""Customer query SQL templates and field constants for EDI converters.

This module contains only data (SQL templates and field lists).
Business logic for executing queries and building header dicts is in
CustomerLookupService.
"""

CUSTOMER_QUERY_SQL_TEMPLATE = """
    SELECT TRIM(dsadrep.adbbtx) AS "Salesperson Name",
        ohhst.btcfdt AS "Invoice Date",
        TRIM(ohhst.btfdtx) AS "Terms Code",
        dsagrep.agrrnb AS "Terms Duration",
        dsabrep.abbvst AS "Customer Status",
        dsabrep.ababnb AS "Customer Number",
        TRIM(dsabrep.abaatx) AS "Customer Name",
        {customer_store_number_field}
        TRIM(dsabrep.ababtx) AS "Customer Address",
        TRIM(dsabrep.abaetx) AS "Customer Town",
        TRIM(dsabrep.abaftx) AS "Customer State",
        TRIM(dsabrep.abagtx) AS "Customer Zip",
        CONCAT(dsabrep.abadnb, dsabrep.abaenb) AS "Customer Phone",
        TRIM(cvgrrep.grm9xt) AS "Customer Email",
        TRIM(cvgrrep.grnaxt) AS "Customer Email 2",
        dsabrep_corp.abbvst AS "Corporate Customer Status",
        dsabrep_corp.ababnb AS "Corporate Customer Number",
        TRIM(dsabrep_corp.abaatx) AS "Corporate Customer Name",
        TRIM(dsabrep_corp.ababtx) AS "Corporate Customer Address",
        TRIM(dsabrep_corp.abaetx) AS "Corporate Customer Town",
        TRIM(dsabrep_corp.abaftx) AS "Corporate Customer State",
        TRIM(dsabrep_corp.abagtx) AS "Corporate Customer Zip",
        CONCAT(dsabrep_corp.abadnb, dsabrep_corp.abaenb) AS "Corporate Customer Phone",
        TRIM(cvgrrep_corp.grm9xt) AS "Corporate Customer Email",
        TRIM(cvgrrep_corp.grnaxt) AS "Corporate Customer Email 2"
    FROM dacdata.ohhst ohhst
        INNER JOIN dacdata.dsabrep dsabrep
            ON ohhst.btabnb = dsabrep.ababnb
        LEFT OUTER JOIN dacdata.cvgrrep cvgrrep
            ON dsabrep.ababnb = cvgrrep.grabnb
        INNER JOIN dacdata.dsadrep dsadrep
            ON dsabrep.abajcd = dsadrep.adaecd
        INNER JOIN dacdata.dsagrep dsagrep
            ON ohhst.bta0cd = dsagrep.aga0cd
        LEFT OUTER JOIN dacdata.dsabrep dsabrep_corp
            ON dsabrep.abalnb = dsabrep_corp.ababnb
        LEFT OUTER JOIN dacdata.cvgrrep cvgrrep_corp
            ON dsabrep_corp.ababnb = cvgrrep_corp.grabnb
        LEFT OUTER JOIN dacdata.dsadrep dsadrep_corp
            ON dsabrep_corp.abajcd = dsadrep_corp.adaecd
    WHERE ohhst.bthhnb = ?
"""

CUSTOMER_FIELDS_LIST_BASE = [
    "Salesperson_Name",
    "Invoice_Date",
    "Terms_Code",
    "Terms_Duration",
    "Customer_Status",
    "Customer_Number",
    "Customer_Name",
    "Customer_Address",
    "Customer_Town",
    "Customer_State",
    "Customer_Zip",
    "Customer_Phone",
    "Customer_Email",
    "Customer_Email_2",
    "Corporate_Customer_Status",
    "Corporate_Customer_Number",
    "Corporate_Customer_Name",
    "Corporate_Customer_Address",
    "Corporate_Customer_Town",
    "Corporate_Customer_State",
    "Corporate_Customer_Zip",
    "Corporate_Customer_Phone",
    "Corporate_Customer_Email",
    "Corporate_Customer_Email_2",
]

CUSTOMER_STORE_NUMBER_FIELD_BASIC = ""
CUSTOMER_STORE_NUMBER_FIELD_STEWARTS = 'dsabrep.abaknb AS "Customer Store Number",'

BASIC_CUSTOMER_FIELDS_LIST = CUSTOMER_FIELDS_LIST_BASE
STEWARTS_CUSTOMER_FIELDS_LIST = [
    "Salesperson_Name",
    "Invoice_Date",
    "Terms_Code",
    "Terms_Duration",
    "Customer_Status",
    "Customer_Number",
    "Customer_Name",
    "Customer_Store_Number",
    "Customer_Address",
    "Customer_Town",
    "Customer_State",
    "Customer_Zip",
    "Customer_Phone",
    "Customer_Email",
    "Customer_Email_2",
    "Corporate_Customer_Status",
    "Corporate_Customer_Number",
    "Corporate_Customer_Name",
    "Corporate_Customer_Address",
    "Corporate_Customer_Town",
    "Corporate_Customer_State",
    "Corporate_Customer_Zip",
    "Corporate_Customer_Phone",
    "Corporate_Customer_Email",
    "Corporate_Customer_Email_2",
]


def build_customer_query_sql(customer_store_number_field: str) -> str:
    """Build customer query SQL with specified store number field."""
    return CUSTOMER_QUERY_SQL_TEMPLATE.format(
        customer_store_number_field=customer_store_number_field
    )


BASIC_CUSTOMER_QUERY_SQL = build_customer_query_sql(
    CUSTOMER_STORE_NUMBER_FIELD_BASIC
)
STEWARTS_CUSTOMER_QUERY_SQL = build_customer_query_sql(
    CUSTOMER_STORE_NUMBER_FIELD_STEWARTS
)
