from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.data_loader import search_companies, get_company_by_name


def db_search(query: str, limit: int = 10, db_path: str = "") -> dict:
    limit = max(1, min(int(limit), 50))
    results = search_companies(query, limit=limit, db_path=db_path or None)
    return {
        "query": query,
        "limit": limit,
        "results": results,
    }


def db_get_company(name: str, db_path: str = "") -> dict | None:
    row = get_company_by_name(name, db_path=db_path or None)
    if not row:
        return {"found": False, "name": name}
    return {"found": True, **row}
