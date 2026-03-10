import migrations.add_plugin_config_column as migration


class FakeDatabaseConnection:
    def __init__(self, runtime_error_on_sql=None, exception_on_sql=None):
        self.runtime_error_on_sql = set(runtime_error_on_sql or [])
        self.exception_on_sql = set(exception_on_sql or [])
        self.queries = []

    def query(self, sql):
        self.queries.append(sql)
        if sql in self.runtime_error_on_sql:
            raise RuntimeError("already exists")
        if sql in self.exception_on_sql:
            raise ValueError("unexpected failure")


def test_apply_migration_success_executes_expected_sql():
    db = FakeDatabaseConnection()

    result = migration.apply_migration(db)

    assert result is True
    assert db.queries == [
        "ALTER TABLE 'folders' ADD COLUMN 'plugin_config' TEXT",
        "UPDATE 'folders' SET plugin_config = '{}' WHERE plugin_config IS NULL",
        "ALTER TABLE 'administrative' ADD COLUMN 'plugin_config' TEXT",
        "UPDATE 'administrative' SET plugin_config = '{}' WHERE plugin_config IS NULL",
        "ALTER TABLE 'folders' ADD COLUMN 'split_edi_filter_categories' TEXT",
        "UPDATE 'folders' SET split_edi_filter_categories = 'ALL' WHERE split_edi_filter_categories IS NULL",
        "ALTER TABLE 'folders' ADD COLUMN 'split_edi_filter_mode' TEXT",
        "UPDATE 'folders' SET split_edi_filter_mode = 'include' WHERE split_edi_filter_mode IS NULL",
        "ALTER TABLE 'administrative' ADD COLUMN 'split_edi_filter_categories' TEXT",
        "UPDATE 'administrative' SET split_edi_filter_categories = 'ALL' WHERE split_edi_filter_categories IS NULL",
        "ALTER TABLE 'administrative' ADD COLUMN 'split_edi_filter_mode' TEXT",
        "UPDATE 'administrative' SET split_edi_filter_mode = 'include' WHERE split_edi_filter_mode IS NULL",
    ]


def test_apply_migration_tolerates_runtime_errors_for_idempotency():
    db = FakeDatabaseConnection(
        runtime_error_on_sql={
            "ALTER TABLE 'folders' ADD COLUMN 'plugin_config' TEXT",
            "ALTER TABLE 'folders' ADD COLUMN 'split_edi_filter_categories' TEXT",
            "UPDATE 'administrative' SET split_edi_filter_mode = 'include' WHERE split_edi_filter_mode IS NULL",
        }
    )

    result = migration.apply_migration(db)

    assert result is True
    assert "ALTER TABLE 'administrative' ADD COLUMN 'plugin_config' TEXT" in db.queries
    assert "UPDATE 'administrative' SET plugin_config = '{}' WHERE plugin_config IS NULL" in db.queries
    assert "ALTER TABLE 'administrative' ADD COLUMN 'split_edi_filter_mode' TEXT" in db.queries


def test_apply_migration_returns_false_and_prints_on_unexpected_failure(capsys):
    db = FakeDatabaseConnection(
        exception_on_sql={"ALTER TABLE 'administrative' ADD COLUMN 'plugin_config' TEXT"}
    )

    result = migration.apply_migration(db)
    captured = capsys.readouterr()

    assert result is False
    assert "Migration failed:" in captured.out
    assert "unexpected failure" in captured.out
