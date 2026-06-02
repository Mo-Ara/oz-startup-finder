from __future__ import annotations

from unittest.mock import MagicMock, patch

from shared.llm_adapter import chat_completion


def _fake_openai(return_value):
    fake = MagicMock()
    fake.chat.completions.create.return_value = return_value
    return fake


def test_chat_completion_returns_expected_results():
    fake_choice = MagicMock()
    fake_choice.message.content = "pong"
    fake_choice.finish_reason = "stop"

    fake_response = MagicMock()
    fake_response.model = "mock-model"
    fake_response.choices = [fake_choice]

    with patch("shared.llm_adapter.OpenAI") as MockOpenAI:
        MockOpenAI.return_value = _fake_openai(fake_response)
        result = chat_completion(
            messages=[{"role": "user", "content": "ping"}],
            api_key="test-key",
            base_url="https://example.com",
            model="mock-model",
        )

    assert result["content"] == "pong"
    assert result["model"] == "mock-model"
    assert result["finish_reason"] == "stop"
