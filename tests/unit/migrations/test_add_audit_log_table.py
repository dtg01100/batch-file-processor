import migrations.add_audit_log_table as migration


class FakeDatabaseConnection:
    def __init__(self, runtime_error_on_sql=None, exception_on_sql=None):
        self.runtime_error_on_sql = runtime_error_on_sql or []
        self.exception_on_sql = exception_on_sql or []
        self.queries = []

    def query(self, sql):
        self.queries.append(sql)
        if any(sql.strip().startswith(s) for s in self.runtime_error_on_sql):
            raise RuntimeError("already exists")
        if any(sql.strip().startswith(s) for s in self.exception_on_sql):
            raise ValueError("unexpected failure")


def test_apply_migration_creates_table_and_indexes():
    db = FakeDatabaseConnection()

    result = migration.apply_migration(db)

    assert result is True
    query_strs = [q.strip() for q in db.queries]
    has_table = any("CREATE TABLE" in q and "audit_log" in q for q in query_strs)
    assert has_table, f"Missing audit_log CREATE TABLE. Queries: {query_strs}"
    assert any("CREATE INDEX" in q and "idx_audit_correlation" in q for q in query_strs)
    assert any("CREATE INDEX" in q and "idx_audit_folder" in q for q in query_strs)


def test_apply_migration_tolerates_runtime_errors_for_idempotency():
    db = FakeDatabaseConnection(
        runtime_error_on_sql=["CREATE TABLE IF NOT EXISTS audit_log"]
    )

    result = migration.apply_migration(db)

    assert result is True


def test_apply_migration_returns_false_on_unexpected_failure():
    db = FakeDatabaseConnection(
        exception_on_sql=["CREATE TABLE IF NOT EXISTS audit_log"]
    )

    result = migration.apply_migration(db)

    assert result is False