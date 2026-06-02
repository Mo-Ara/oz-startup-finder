from __future__ import annotations

import os
import threading

from dotenv import load_dotenv
from google.adk.models import LLMRegistry
from google.adk.models.lite_llm import LiteLLM

load_dotenv()

_lock = threading.Lock()
_registered = False


def _get_openrouter_model() -> str:
    # Read once from env so .env / HF Space secrets both work.
    return os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()


def _register_openrouter(model_name: str) -> None:
    global _registered
    if _registered:
        return
    with _lock:
        if _registered:
            return
        LLMRegistry._register("openrouter/.*$", LiteLLM)
        _registered = True


def get_model_name() -> str:
    _register_openrouter("openrouter/.*$")
    return _get_openrouter()
