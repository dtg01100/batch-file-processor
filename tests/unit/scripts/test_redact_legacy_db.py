"""Unit tests for scripts/redact_legacy_db.py."""

import sqlite3

import scripts.redact_legacy_db as redact_script


def _create_legacy_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE folders (
            id INTEGER PRIMARY KEY,
            alias TEXT,
            email_origin_address TEXT,
            email_origin_password TEXT,
            email_origin_username TEXT,
            email_origin_smtp_server TEXT,
            email_to TEXT,
            email_subject_line TEXT,
            ftp_server TEXT,
            ftp_username TEXT,
            ftp_password TEXT,
            report_email_address TEXT,
            report_email_username TEXT,
            report_email_password TEXT,
            report_email_smtp_server TEXT,
            report_email_destination TEXT,
            reporting_email TEXT,
            copy_to_directory TEXT,
            edi_converter_scratch_folder TEXT,
            folder_name TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE administrative (
            id INTEGER PRIMARY KEY,
            email_origin_address TEXT,
            email_origin_password TEXT,
            email_origin_username TEXT,
            email_origin_smtp_server TEXT,
            email_to TEXT,
            email_subject_line TEXT,
            ftp_server TEXT,
            ftp_username TEXT,
            ftp_password TEXT,
            report_email_address TEXT,
            report_email_username TEXT,
            report_email_password TEXT,
            report_email_smtp_server TEXT,
            report_email_destination TEXT,
            reporting_email TEXT,
            copy_to_directory TEXT,
            logs_directory TEXT,
            edi_converter_scratch_folder TEXT,
            errors_folder TEXT,
            folder_name TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE settings (
            id INTEGER PRIMARY KEY,
            email_address TEXT,
            email_username TEXT,
            email_password TEXT,
            email_smtp_server TEXT,
            as400_username TEXT,
            as400_password TEXT,
            as400_address TEXT
        )
        """)
    cur.execute("""
        CREATE TABLE processed_files (
            id INTEGER PRIMARY KEY,
            file_name TEXT,
            copy_destination TEXT,
            ftp_destination TEXT,
            email_destination TEXT
        )
        """)
    cur.execute("CREATE TABLE emails_to_send (id INTEGER PRIMARY KEY, log TEXT)")
    cur.execute(
        "CREATE TABLE working_batch_emails_to_send (id INTEGER PRIMARY KEY, log TEXT)"
    )
    cur.execute(
        "CREATE TABLE sent_emails_removal_queue (id INTEGER PRIMARY KEY, log TEXT)"
    )

    cur.executemany(
        """
        INSERT INTO folders VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                1,
                "A1",
                "origin1@real.com",
                "pw1",
                "user1",
                "smtp.real.com",
                "to1@real.com",
                "Subject",
                "ftp.real.com",
                "ftp_user",
                "ftp_pw",
                "rep1@real.com",
                "repuser1",
                "reppw1",
                "smtp.rep.com",
                "dest1@real.com",
                "reporting1@real.com",
                "C:/copy",
                "C:/scratch",
                "C:/folder",
            ),
            (
                2,
                "A2",
                "origin2@real.com",
                "pw2",
                "user2",
                "smtp.real.com",
                "",
                None,
                "",
                None,
                "",
                "",
                None,
                "",
                None,
                "",
                None,
                "",
                None,
                "",
            ),
        ],
    )

    cur.execute("""
        INSERT INTO administrative VALUES
        (1, 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't')
        """)
    cur.execute("""
        INSERT INTO settings VALUES
        (1, 'old@example.com', 'old_user', 'old_pw', 'smtp.old.com', 'u', 'p', '1.2.3.4')
        """)
    cur.executemany(
        """
        INSERT INTO processed_files VALUES
        (?, ?, ?, ?, ?)
        """,
        [
            (
                1,
                r"I:\MAILBOX\OUT\012258\012258.115",
                "C:/dest",
                "ftp.real/out",
                "to@real.com",
            ),
            (2, r"I:\MAILBOX\OUT\X\Y", "N/A", "N/A", "N/A"),
        ],
    )
    cur.executemany(
        "INSERT INTO emails_to_send VALUES (?, ?)", [(1, "sensitive"), (2, None)]
    )
    cur.executemany(
        "INSERT INTO working_batch_emails_to_send VALUES (?, ?)",
        [(1, "secret"), (2, None)],
    )
    cur.executemany(
        "INSERT INTO sent_emails_removal_queue VALUES (?, ?)",
        [(1, "private"), (2, None)],
    )

    conn.commit()
    conn.close()


def test_redact_updates_expected_columns_and_preserves_empty_values(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "legacy.db"
    _create_legacy_db(db_path)
    monkeypatch.setattr(redact_script, "DB_PATH", str(db_path))

    redact_script.redact()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        SELECT
            email_origin_address,
            email_origin_password,
            email_to,
            email_subject_line,
            ftp_server,
            ftp_username,
            copy_to_directory,
            folder_name
        FROM folders WHERE id = 1
        """)
    row1 = cur.fetchone()
    assert row1 == (
        "user1@example.com",
        "redacted_password",
        "recipient1@example.com",
        "Invoice",
        "ftp.example.com",
        "ftp_user_1",
        "D:/OUTPUT/A1",
        "D:/DATA/OUT/A1",
    )

    cur.execute("""
        SELECT
            email_to,
            email_subject_line,
            ftp_server,
            ftp_username,
            copy_to_directory,
            folder_name
        FROM folders WHERE id = 2
        """)
    row2 = cur.fetchone()
    assert row2 == ("", None, "", None, "", "D:/DATA/OUT/A2")

    cur.execute("""
        SELECT
            email_origin_address,
            ftp_server,
            logs_directory,
            folder_name
        FROM administrative WHERE id = 1
        """)
    assert cur.fetchone() == (
        "admin@example.com",
        "ftp.example.com",
        "C:/ProgramData/BatchFileSender/Logs",
        "template",
    )

    cur.execute("""
        SELECT
            email_address,
            email_username,
            email_password,
            as400_address
        FROM settings WHERE id = 1
        """)
    assert cur.fetchone() == ("settings@example.com", "", "", "10.0.0.100")

    cur.execute("""
        SELECT file_name, copy_destination, ftp_destination, email_destination
        FROM processed_files WHERE id = 1
        """)
    assert cur.fetchone() == (
        r"D:\DATA\OUT\012258\012258.115",
        "D:/OUTPUT/redacted",
        "ftp.example.com/redacted",
        "redacted@example.com",
    )

    cur.execute("""
        SELECT file_name, copy_destination, ftp_destination, email_destination
        FROM processed_files WHERE id = 2
        """)
    assert cur.fetchone() == (r"D:\DATA\OUT\X\Y", "N/A", "N/A", "N/A")

    cur.execute("SELECT log FROM emails_to_send ORDER BY id")
    assert cur.fetchall() == [("redacted",), (None,)]
    cur.execute("SELECT log FROM working_batch_emails_to_send ORDER BY id")
    assert cur.fetchall() == [("redacted",), (None,)]
    cur.execute("SELECT log FROM sent_emails_removal_queue ORDER BY id")
    assert cur.fetchall() == [("redacted",), (None,)]

    conn.close()


def test_redact_commits_before_vacuum_and_closes_connection(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    _create_legacy_db(db_path)
    monkeypatch.setattr(redact_script, "DB_PATH", str(db_path))

    real_connect = sqlite3.connect
    state = {
        "commit_called": False,
        "vacuum_seen": False,
        "commit_before_vacuum": False,
        "close_called": False,
    }

    class CursorProxy:
        def __init__(self, inner):
            self._inner = inner

        def execute(self, sql, *args, **kwargs):
            if sql.strip().upper().startswith("VACUUM"):
                state["vacuum_seen"] = True
                state["commit_before_vacuum"] = state["commit_called"]
            return self._inner.execute(sql, *args, **kwargs)

        def __getattr__(self, name):
            return getattr(self._inner, name)

    class ConnectionProxy:
        def __init__(self, inner):
            self._inner = inner

        def cursor(self):
            return CursorProxy(self._inner.cursor())

        def commit(self):
            state["commit_called"] = True
            return self._inner.commit()

        def close(self):
            state["close_called"] = True
            return self._inner.close()

        def __getattr__(self, name):
            return getattr(self._inner, name)

    def connect_proxy(*args, **kwargs):
        return ConnectionProxy(real_connect(*args, **kwargs))

    monkeypatch.setattr(redact_script.sqlite3, "connect", connect_proxy)

    redact_script.redact()

    assert state["commit_called"] is True
    assert state["vacuum_seen"] is True
    assert state["commit_before_vacuum"] is True
    assert state["close_called"] is True
