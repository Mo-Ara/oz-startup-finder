from __future__ import annotations

from pathlib import Path
from shared.tools.db_search import db_search, db_get_company

DB_PATH = Path("data") / "startups.db"


def test_db_search_with_valid_query():
    result = db_search("AI", limit=5)
    assert result["query"] == "AI"
    assert len(result["results"]) <= 5


def test_db_search_respects_limit():
    result = db_search("a", limit=10)
    assert len(result["results"]) <= 10


def test_db_search_respects_max_limit_fifty():
    result = db_search("a", limit=1_000)
    assert len(result["results"]) <= 50


def test_db_search_no_results_for_gibberish():
    result = db_search("zzzznonexistent")
    assert result["results"] == []


def test_db_get_company_existing():
    result = db_get_company("Acme AI")
    assert result is not None
    assert result["found"] is True
    assert result["company_name"] == "Acme AI"


def test_db_get_company_missing():
    result = db_get_company("NoSuchCo")
    assert result is not None
    assert result["found"] is False
    assert result["name"] == "NoSuchCo"
