from __future__ import annotations

from shared.data_loader import search_companies, get_company_by_name


def db_search(query: str, limit: int = 10) -> dict:
    """
    Search the startup knowledge base for companies matching the query.

    Uses SQLite FTS5 full-text search across company metadata (name, industry,
    city, description). Results are returned ranked by relevance.

    Args:
        query: Natural-language search query. Examples: "AI code review", "fintech Melbourne".
        limit: Maximum number of results to return (default 10, max 50).

    Returns:
        dict with keys: query, limit, results (list of company dicts)
    """
    limit = max(1, min(limit, 50))
    results = search_companies(query, limit=limit)
    return {
        "query": query,
        "limit": limit,
        "results": results,
    }


def db_get_company(name: str) -> dict | None:
    """
    Fetch a single company by exact name from the knowledge base.

    Args:
        name: Exact company name.

    Returns:
        dict with company fields, or None if not found.
    """
    row = get_company_by_name(name)
    if not row:
        return {"found": False, "name": name}
    return {"found": True, **row}
