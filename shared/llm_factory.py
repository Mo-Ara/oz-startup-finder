from __future__ import annotations

import os
from dataclasses import dataclass

from openai import AsyncOpenAI


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "openrouter"
    model: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
    api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    base_url: str = "https://openrouter.ai/api/v1"
    max_retries: int = 2
    request_timeout: int = 30


def get_client() -> AsyncOpenAI:
    cfg = LLMConfig()
    if not cfg.api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. "
            "Get a free key at https://openrouter.ai/keys"
        )
    return AsyncOpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        max_retries=cfg.max_retries,
        timeout=cfg.request_timeout,
    )


get_llm = get_client


def get_model_name() -> str:
    return LLMConfig().model
