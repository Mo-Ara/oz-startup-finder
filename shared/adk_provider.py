from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field, replace
from typing import Any, AsyncGenerator, AsyncIterator, Dict, List, Optional

from dotenv import load_dotenv
from google.adk.models import LLMRegistry, BaseLlm, LlmRequest, LlmResponse
from google.genai import types

load_dotenv()

_lock = threading.Lock()
_registered = False


@dataclass
class Reg:
    model: str
    api_key: str | None = None
    base_url: str = "https://openrouter.ai/api/v1"
    max_retries: int = 2
    request_timeout: int = 30

    @property
    def effective_model(self) -> str:
        raw = os.getenv("OPENROUTER_MODEL", "").strip()
        if raw:
            return raw if raw.startswith("openrouter/") else f"openrouter/{raw}"
        return raw


@dataclass(frozen=True)
class _Cfg:
    api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    base_url: str = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")


def _cfg() -> _Cfg:
    return _Cfg()


def _register_openrouter() -> None:
    global _registered
    if _registered:
        return
    with _lock:
        if _registered:
            return
        LLMRegistry._register("openrouter/.*$", _OpenRouterLlm)
        _registered = True


class _OpenRouterLlm(BaseLlm):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._model_field: str = kwargs.get("model", "")
        c = _cfg()
        self._key = c.api_key
        self._base = c.base_url.rstrip("/")

    @property
    def support_system_prompt(self) -> bool:
        return True

    def _state(self) -> Reg:
        model = _cfg().effective_model
        return Reg(
            model=model,
            api_key=self._key,
            base_url=self._base,
        )

    def _msgs(self, llm_request: LlmRequest) -> List[Dict[str, Any]]:
        # ADK sends InvocationContext.user_content as a system instruction
        # on first turn; preserve ADK's role semantics.
        messages: List[Dict[str, Any]] = []

        contents: List[types.Content] = []
        if llm_request.system_instruction and llm_request.system_instruction.parts:
            contents.append(llm_request.system_instruction)
        contents.extend(getattr(llm_request, "messages", []) or [])

        for content in contents:
            if not isinstance(content, types.Content):
                continue
            role = "user" if content.role in {"user", "model"} else content.role
            text = ", ".join(p.text for p in (content.parts or []) if p.text)
            messages.append({"role": role, "content": text})
        return messages

    def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncIterator[LlmResponse]:
        from openai import AsyncOpenAI

        msg = self._state()
        if not msg.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. "
                "Set it in .env or Space secrets."
            )

        client = AsyncOpenAI(
            api_key=msg.api_key,
            base_url=msg.base_url,
            max_retries=msg.max_retries,
            timeout=msg.request_timeout,
        )
        messages = self._msgs(llm_request)

        async def _run() -> AsyncIterator[LlmResponse]:
            response = await client.chat.completions.create(
                model=msg.model,
                messages=messages,
            )
            text = response.choices[0].message.content or ""
            chunk = LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)],
                )
            )
            yield chunk

        return _run()

    def generate_content(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> Iterator[LlmResponse]:
        from openai import OpenAI

        msg = self._state()
        if not msg.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. "
                "Set it in .env or Space secrets."
            )

        client = OpenAI(
            api_key=msg.api_key,
            base_url=msg.base_url,
            max_retries=msg.max_retries,
            timeout=msg.request_timeout,
        )
        messages = self._msgs(llm_request)

        def _run() -> Iterator[LlmResponse]:
            response = client.chat.completions.create(
                model=msg.model,
                messages=messages,
            )
            text = response.choices[0].message.content or ""
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=text)],
                )
            )

        return _run()


def get_model_name() -> str:
    _register_openrouter()
    c = _cfg()
    m = c.effective_model
    if not m:
        raise RuntimeError(
            "Set OPENROUTER_MODEL, e.g. openrouter/prefix and OPENROUTER_API_KEY "
            "in `.env` or Space secrets, then rebuild."
        )
    return m
