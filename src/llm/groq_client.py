"""Light wrapper around the Groq client with a simple fallback message.
"""
from __future__ import annotations

import os
from typing import Any

try:
    import groq
except Exception:  # pragma: no cover - optional dependency
    groq = None


class GroqClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if groq is not None:
            self._client = groq.Groq(api_key=self.api_key) if self.api_key else groq.Groq()
        else:
            self._client = None

    def generate(self, prompt: str, model: str = "llama-3.3-70b-versatile", temperature: float = 0.2) -> str:
        if self._client is None:
            raise RuntimeError("Groq client is not available. Install `groq` and set GROQ_API_KEY if required")
        resp = self._client.generate(prompt=prompt, model=model, temperature=temperature)
        # resp shape may vary; try to be tolerant
        if isinstance(resp, dict) and "text" in resp:
            return resp["text"].strip()
        if isinstance(resp, str):
            return resp.strip()
        try:
            return str(resp).strip()
        except Exception:
            return ""


default_client = GroqClient()
