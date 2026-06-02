from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY is not set in .env")
    raise SystemExit(2)

client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")

try:
    r = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Reply with the word 'pong' only."},
        ],
    )
    content = r.choices[0].message.content or ""
    print(f"OK model={r.model}")
    print(f"CONTENT={content}")
except Exception as e:
    print(f"ERR status={getattr(getattr(e, 'response', None), 'status_code', None)} msg={e}")
    raise SystemExit(1) from e
