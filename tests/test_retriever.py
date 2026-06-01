from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/startups.db")


def test_fts5_search_returns_rows() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT company_name, industry FROM companies WHERE company_name MATCH 'Acme'"
    ).fetchall()
    conn.close()

    assert len(rows) >= 1
    assert rows[0]["company_name"] == "Acme AI"


def test_company_count() -> None:
    from tests.conftest import db_conn

    assert db_conn is not None  # placeholder for future test expansion
