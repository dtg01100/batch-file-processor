from dispatch.converters.customer_queries import (
    BASIC_CUSTOMER_QUERY_SQL,
    CUSTOMER_FIELDS_LIST_BASE,
    STEWARTS_CUSTOMER_FIELDS_LIST,
    STEWARTS_CUSTOMER_QUERY_SQL,
    build_customer_query_sql,
)


class TestCustomerQueries:
    def test_basic_query_sql_has_no_store_number(self):
        assert "Customer Store Number" not in BASIC_CUSTOMER_QUERY_SQL

    def test_stewarts_query_sql_has_store_number(self):
        assert "Customer Store Number" in STEWARTS_CUSTOMER_QUERY_SQL

    def test_build_customer_query_sql(self):
        sql = build_customer_query_sql("dsabrep.abaknb AS 'Store'")
        assert "dsabrep.abaknb" in sql
        assert "FROM dacdata.ohhst" in sql

    def test_stewarts_fields_list_has_store_number(self):
        assert "Customer_Store_Number" in STEWARTS_CUSTOMER_FIELDS_LIST

    def test_basic_fields_list_no_store_number(self):
        assert "Customer_Store_Number" not in CUSTOMER_FIELDS_LIST_BASE
