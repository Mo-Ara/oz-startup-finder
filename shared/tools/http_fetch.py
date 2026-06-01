from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from typing import Any

DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


async def fetch_homepage_summary(url: str) -> dict[str, Any]:
    if not url or not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "invalid_url"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            text = resp.text
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc), "status": getattr(exc, "response", None)}

    soup = BeautifulSoup(text, "html.parser")
    title = (soup.title.string or "").strip() if soup.title else ""

    meta_desc = ""
    for attr in ({"name": "description"}, {"property": "og:description"}):
        tag = soup.find("meta", attrs=attr)
        if tag and tag.get("content"):
            meta_desc = tag["content"].strip()
            break

    body_text = " ".join(soup.get_text(separator=" ", strip=True).split())[:1500]

    return {
        "ok": True,
        "url": str(resp.url),
        "title": title,
        "meta_description": meta_desc,
        "body_snippet": body_text,
        "status": resp.status_code,
    }
