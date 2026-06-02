from __future__ import annotations

import os
import threading
from typing import Any, AsyncIterator, Dict, Iterator, List

from dataclasses import dataclass
from dotenv import load_dotenv
from google.adk.models import LLMRegistry, BaseLlm, LlmRequest, LlmResponse
from google.genai import types

load_dotenv()

_lock = threading.Lock()
_registered = False


def _effective_model() -> str:
    raw = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
    if not raw.startswith("openrouter/"):
        raw = f"openrouter/{raw}"
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
        c = _cfg()
        self._key = c.api_key
        self._base = c.base_url.rstrip("/")

    @property
    def support_system_prompt(self) -> bool:
        return True

    def _msgs(self, llm_request: LlmRequest) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        contents: List[types.Content] = []
        if llm_request.system_instruction and llm_request.system_instruction.parts:
            contents.append(llm_request.system_instruction)
        contents.extend(getattr(llm_request, "messages", []) or [])

        for content in contents:
            if not isinstance(content, types.Content):
                continue
            role = "user" if content.role in {"user", "model"} else content.role
            text = ", ".join(part.text for part in (content.parts or []) if part.text)
            messages.append({"role": role, "content": text})
        return messages

    def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> AsyncIterator[LlmResponse]:
        from openai import AsyncOpenAI

        if not self._key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. "
                "Set it in .env or Space secrets."
            )

        client = AsyncOpenAI(
            api_key=self._key,
            base_url=self._base,
        )
        messages = self._msgs(llm_request)
        model = _effective_model()

        async def _run() -> AsyncIterator[LlmResponse]:
            response = await client.chat.completions.create(
                model=model,
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

    def generate_content(
        self,
        llm_request: LlmRequest,
        stream: bool = False,
    ) -> Iterator[LlmResponse]:
        from openai import OpenAI

        if not self._key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. "
                "Set it in .env or Space secrets."
            )

        client = OpenAI(
            api_key=self._key,
            base_url=self._base,
        )
        messages = self._msgs(llm_request)
        model = _effective_model()

        def _run() -> Iterator[LlmResponse]:
            response = client.chat.completions.create(
                model=model,
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
    model = _effective_model()
    if not model:
        raise RuntimeError(
            "Set OPENROUTER_MODEL, e.g. openrouter/free, and OPENROUTER_API_KEY "
            "in .env or Space secrets, then rebuild."
        )
    return model
