from __future__ import annotations

import os
from typing import Any, Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover - optional in lib/tests
    pass

from openai import OpenAI
from openai.types.chat import ChatCompletion


def _cfg() -> dict:
    return {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
        "model": os.getenv("OPENROUTER_MODEL", "openrouter/free"),
        "timeout_s": float(os.getenv("OPENROUTER_TIMEOUT_S", "20")),
        "max_retries": int(os.getenv("OPENROUTER_RETRIES", "1")),
    }


def _client_sync(*, api_key: str, base_url: str, max_retries: int) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url.rstrip("/"), max_retries=max_retries)


def _normalize(exc: Exception) -> Exception:
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    if status == 400:
        raise RuntimeError(
            "OpenRouter rejected the request. Use OPENROUTER_MODEL with a valid model ID, e.g. poolside/laguna-m.1-20260312:free"
        ) from exc
    raise RuntimeError(f"OpenRouter request failed: {exc}") from exc


def chat_completion(
    messages: List[Dict[str, str]],
    *,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> Dict[str, Any]:
    cfg = _cfg()
    key = api_key or cfg["api_key"]
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    url = base_url or cfg["base_url"]
    model_id = model or cfg["model"]
    if not model_id:
        raise RuntimeError("OPENROUTER_MODEL is not set.")

    client = _client_sync(
        api_key=key,
        base_url=url,
        max_retries=max_retries if max_retries is not None else cfg["max_retries"],
    )
    effective_timeout = timeout if timeout is not None else cfg["timeout_s"]

    try:
        response: ChatCompletion = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=effective_timeout,
        )
    except Exception as exc:
        raise _normalize(exc)

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
