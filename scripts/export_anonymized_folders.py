#!/usr/bin/env python3
"""Export anonymized folder rows from a SQLite DB to per-row JSON fixtures.

Reads every row from the ``folders`` table of an anonymized SQLite database
and writes one JSON file per row to ``tests/fixtures/anonymized_folders/folders/``.

Output is **deterministic and idempotent**: rows are sorted by ``id``, JSON
keys are sorted (``sort_keys=True``), filenames are zero-padded with the row
id and a slugified alias.

Usage:
    DB_PATH=/path/to/anonymized.sqlite \\
        .venv/bin/python scripts/export_anonymized_folders.py

By default the output directory is
``tests/fixtures/anonymized_folders/folders`` relative to the repo root. This
can be overridden with the ``OUT_DIR`` environment variable.

Anonymization note: this script trusts its input. The DB it reads must be
already anonymized (no real customer paths, credentials, or PII).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "fixtures" / "anonymized_folders" / "folders"

# Fields the 1.47 routing harness reads off ``parameters_dict`` directly.
# Anything not in this list is still emitted (1.47's dispatch delegates most
# fields back to the converter), but documenting the routing-critical set
# here makes drift easier to spot.
ROUTING_CRITICAL_FIELDS = (
    "id",
    "alias",
    "folder_name",
    "convert_to_format",
    "process_edi",
    "tweak_edi",
    "split_edi",
    "force_edi_validation",
    "rename_file",
    "process_backend_copy",
    "process_backend_ftp",
    "process_backend_email",
    "copy_to_directory",
    "ftp_server",
    "ftp_folder",
    "ftp_username",
    "ftp_password",
    "ftp_port",
    "email_to",
    "email_origin_address",
    "email_subject_line",
    "include_c_records",
    "include_a_records",
    "split_edi_include_credits",
    "split_edi_include_invoices",
)


def _slugify(text: str, *, max_len: int = 60) -> str:
    """Sanitize a folder alias for use in a filename."""
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", text or "").strip("_")
    if not sanitized:
        sanitized = "row"
    return sanitized[:max_len]


def _iter_rows(con: sqlite3.Connection) -> list[sqlite3.Row]:
    cur = con.execute("SELECT * FROM folders ORDER BY id ASC")
    return cur.fetchall()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict (json.dumps-friendly)."""
    return {
        k: row[k] for k in row.keys()
    }  # noqa: SIM118 - sqlite3.Row has its own .keys()


def main(argv: list[str]) -> int:
    db_path = os.environ.get("DB_PATH")
    if not db_path:
        print(
            "DB_PATH environment variable must be set to the anonymized DB path.",
            file=sys.stderr,
        )
        return 2
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"DB not found: {db_file}", file=sys.stderr)
        return 2
    active_only = os.environ.get("ACTIVE_ONLY", "1") not in ("0", "false", "False")

    out_dir = Path(os.environ.get("OUT_DIR", DEFAULT_OUT_DIR))
    out_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db_file))
    con.row_factory = sqlite3.Row
    try:
        if active_only:
            cur = con.execute(
                "SELECT * FROM folders WHERE folder_is_active = 'True' "
                "ORDER BY id ASC"
            )
        else:
            cur = con.execute("SELECT * FROM folders ORDER BY id ASC")
        rows = cur.fetchall()
    finally:
        con.close()

    if not rows:
        print(
            f"No rows in folders table of {db_file}; nothing to export.",
            file=sys.stderr,
        )
        return 1

    written = 0
    for row in rows:
        row_dict = _row_to_dict(row)
        # Store dict in insertion order, but keys are sorted on dump below.
        filename = (
            f"{int(row_dict['id']):04d}_{_slugify(str(row_dict.get('alias', '')))}.json"
        )
        out_path = out_dir / filename
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(row_dict, fh, sort_keys=True, indent=2, ensure_ascii=False)
            fh.write("\n")
        written += 1

    print(f"Wrote {written} folder rows to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
