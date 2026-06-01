from __future__ import annotations

from pathlib import Path
from shared.data_loader import get_connection, search_companies, get_company_by_name


DB_PATH = Path("data") / "startups.db"


def test_get_connection_returns_sqlite3_connection():
    conn = get_connection(DB_PATH)
    assert conn is not None
    conn.close()


def test_search_companies_returns_rows_for_matching_query():
    results = search_companies("Acme", db_path=DB_PATH)
    assert isinstance(results, list)
    assert len(results) >= 1
    assert results[0]["company_name"] == "Acme AI"


def test_search_companies_returns_empty_for_unrelated_query():
    results = search_companies("zzzzzz_not_a_real_company", db_path=DB_PATH)
    assert results == []


def test_get_company_by_name_returns_existing_company():
    row = get_company_by_name("Acme AI", db_path=DB_PATH)
    assert row is not None
    assert row["company_city"] == "Sydney"


def test_get_company_by_name_returns_none_for_missing_company():
    row = get_company_by_name("Nonexistent Company XYZ", db_path=DB_PATH)
    assert row is None
