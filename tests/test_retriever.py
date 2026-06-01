from __future__ import annotations

import sqlite3
from pathlib import Path

from shared.data_loader import search_companies, get_company_by_name

DB_PATH = Path("data") / "startups.db"


def test_search_returns_expected_result_structure():
    rows = search_companies("melbourne", limit=5, db_path=DB_PATH)
    assert isinstance(rows, list)
    assert rows, "expected seed-backed rows for 'melbourne'"
    for row in rows:
        assert "company_name" in row
        assert "industry" in row
        assert "company_city" in row
        assert "company_website" in row
        assert "rank" in row


def test_search_limit_and_offset():
    first_page = search_companies("melbourne", limit=2, offset=0, db_path=DB_PATH)
    second_page = search_companies("melbourne", limit=2, offset=2, db_path=DB_PATH)
    assert len(first_page) == 2
    assert second_page == []


def test_search_offset_beyond_results_returns_nothing():
    page = search_companies("sydney", limit=1, offset=2, db_path=DB_PATH)
    assert page == []


def test_search_empty_result_for_gibberish():
    rows = search_companies("xyznonexistent12345", db_path=DB_PATH)
    assert rows == []


def test_get_company_by_name_returns_expected_row():
    row = get_company_by_name("MediScan", db_path=DB_PATH)
    assert row is not None
    assert row["industry"] == "HealthTech"
    assert row["company_city"] == "Sydney"


def test_database_contains_seed_companies():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    count = conn.execute("SELECT COUNT(*) AS c FROM companies").fetchone()["c"]
    conn.close()
    assert count >= 5  # seed_demo.py inserts 5 synthetic companies
