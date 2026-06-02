from __future__ import annotations

import os
import threading

from dotenv import load_dotenv
from google.adk.models import LLMRegistry

load_dotenv()

_lock = threading.Lock()
_registered = False


def _get_openrouter_model() -> str:
    return os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def _load_lite_llm_class():  # pragma: no cover - runtime compatibility helper
    import google.adk.models.lite_llm as lite_llm_module  # noqa: WPS433

    for candidate_name in ("LiteLLM", "LiteLlm"):
        if hasattr(lite_llm_module, candidate_name):
            return getattr(lite_llm_module, candidate_name)

    raise ImportError(
        "LiteLLM support not found in google.adk.models.lite_llm. "
        "Install it with: pip install 'google-adk[extensions]'"
    )


def _register_openrouter(model_name: str) -> None:
    global _registered
    if _registered:
        return
    with _lock:
        if _registered:
            return
        LiteLLMClass = _load_lite_llm_class()
        LLMRegistry._register("openrouter/.*$", LiteLLMClass)
        _registered = True


def get_model_name() -> str:
    _register_openrouter("openrouter/.*$")
    return _get_openrouter_model()
