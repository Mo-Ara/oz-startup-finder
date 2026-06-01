from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest
from shared.tools.http_fetch import fetch_homepage_summary


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "<html><head><title>Test Co</title><meta name='description' content='A test company'></head><body>Test body</body></html>"
    mock_response.status_code = 200
    mock_response.url = "https://testco.example.com"
    mock.get = AsyncMock(return_value=mock_response)
    mock.close = AsyncMock()
    monkeypatch.setattr("shared.tools.http_fetch.httpx.AsyncClient", lambda **kwargs: mock)
    return mock


@pytest.mark.asyncio
async def test_fetch_homepage_summary_returns_metadata(mock_client: MagicMock) -> None:
    result = await fetch_homepage_summary("https://testco.example.com")
    assert result["ok"] is True
    assert result["title"] == "Test Co"
    assert result["meta_description"] == "A test company"
    assert "body_snippet" in result


@pytest.mark.asyncio
async def test_fetch_homepage_summary_returns_false_on_invalid_url() -> None:
    result = await fetch_homepage_summary("not-a-url")
    assert result["ok"] is False
    assert result["error"] == "invalid_url"
