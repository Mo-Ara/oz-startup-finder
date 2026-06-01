from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any


DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "startups.db"


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def search_companies(
    query: str,
    limit: int = 20,
    offset: int = 0,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT
                c.company_name,
                c.company_website,
                c.company_linkedin,
                c.company_number_of_employees,
                c.industry,
                c.company_city,
                c.company_state,
                c.company_logo_url,
                bm25(companies_fts) AS rank
            FROM companies AS c
            JOIN companies_fts ON c.rowid = companies_fts.rowid
            WHERE companies_fts MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
            """,
            (query, limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_company_by_name(name: str, db_path: str | Path | None = None) -> dict[str, Any] | None:
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM companies WHERE company_name = ? LIMIT 1",
            (name,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
