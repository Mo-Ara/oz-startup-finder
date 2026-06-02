from __future__ import annotations

import os
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover - optional in lib/tests
    pass

from openai import OpenAI


def _cfg() -> dict:
    return {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        "model": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
    }


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> Dict[str, Any]:
    cfg = _cfg()
    key = api_key or cfg["api_key"]
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    url = (base_url or cfg["base_url"]).rstrip("/")
    model_id = model or cfg["model"]
    if not model_id:
        raise RuntimeError("OPENROUTER_MODEL is not set.")

    client = OpenAI(api_key=key, base_url=url)
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        status = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        if status == 400:
            raise RuntimeError(
                f"OpenRouter rejected the model '{model_id}'. "
                f"Set OPENROUTER_MODEL in .env to a valid model ID like 'openrouter/free'."
            ) from exc
        raise RuntimeError(f"OpenRouter request failed: {exc}") from exc

    choice = response.choices[0]
    return {
        "model": response.model,
        "content": choice.message.content or "",
        "finish_reason": choice.finish_reason,
        "raw": response,
    }


if __name__ == "__main__":
    result = chat_completion(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Reply with the word 'pong' only."},
        ]
    )
    print("MODEL:", result.get("model"))
    print("CONTENT:", result.get("content"))
    print("FINISH_REASON:", result.get("finish_reason"))
