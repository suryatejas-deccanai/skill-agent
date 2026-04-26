"""
Thin wrapper around the Google Gen AI SDK so the rest of the codebase
never imports `google.genai` directly. Swapping providers later (Claude,
OpenAI, local Llama via Ollama, etc.) only requires editing this file.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from google import genai
from google.genai import types

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
JSON_MODEL = os.getenv("GEMINI_JSON_MODEL", "gemini-2.5-flash-lite")

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Lazy-initialise a single client. Picks up GEMINI_API_KEY automatically."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at "
                "https://aistudio.google.com/app/apikey and put it in .env"
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generate_text(
    prompt: str,
    *,
    system: str | None = None,
    temperature: float = 0.3,
    model: str = DEFAULT_MODEL,
    max_retries: int = 3,
) -> str:
    """Generate plain text. Retries on transient errors (e.g. 429 rate limits)."""
    client = get_client()
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
    )

    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return (resp.text or "").strip()
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)
    return ""


def generate_json(
    prompt: str,
    *,
    schema: dict,
    system: str | None = None,
    temperature: float = 0.2,
    model: str = JSON_MODEL,
    max_retries: int = 3,
) -> Any:
    """
    Generate JSON output that conforms to `schema`. We use Gemini's structured
    output mode rather than parsing free-form text — much more reliable.
    """
    client = get_client()
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
        response_mime_type="application/json",
        response_json_schema=schema,
    )

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            text = (resp.text or "").strip()
            return json.loads(text)
        except json.JSONDecodeError as exc:
            last_err = exc
            time.sleep(1)
        except Exception as exc:
            last_err = exc
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)

    raise RuntimeError(f"Failed to get valid JSON after {max_retries} attempts: {last_err}")