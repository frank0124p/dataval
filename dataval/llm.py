"""LLM client. Adapted for a company self-hosted model behind an OpenAI-compatible
endpoint (the common case for opencode setups). Configure via env vars:

  DATAVAL_LLM_BASE_URL   e.g. http://localhost:4000/v1  (your gateway)
  DATAVAL_LLM_MODEL      e.g. company-default
  DATAVAL_LLM_API_KEY    optional; many internal gateways ignore it

If no base URL is set, NullLLM is used: the advisory zone is simply skipped.
Advisory LLM output NEVER affects the compliance verdict, so running without an
LLM is fully supported (matches the 'runs unattended' constraint).
"""
from __future__ import annotations
import json
import os
from typing import Optional, Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class NullLLM:
    def complete(self, system: str, user: str) -> str:
        return ""


class OpenAICompatLLM:
    """Minimal OpenAI-compatible chat client using urllib (no extra deps)."""
    def __init__(self, base_url: str, model: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.last_error = ""

    def complete(self, system: str, user: str) -> str:
        import urllib.request
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(self.base_url + "/chat/completions",
                                     data=payload, headers=headers)
        self.last_error = ""
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            # Advisory zone must never break the run.
            self.last_error = f"{type(e).__name__}: {e}"
            return ""


def from_env() -> LLMClient:
    base = os.environ.get("DATAVAL_LLM_BASE_URL", "").strip()
    if not base:
        return NullLLM()
    return OpenAICompatLLM(
        base_url=base,
        model=os.environ.get("DATAVAL_LLM_MODEL", "company-default"),
        api_key=os.environ.get("DATAVAL_LLM_API_KEY", ""),
    )


def call_json(llm: LLMClient, system: str, user: str) -> Optional[list | dict]:
    raw = (llm.complete(system, user) or "").strip()
    if not raw:
        return None
    raw = raw.replace("```json", "").replace("```", "").strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        i, j = raw.find(opener), raw.rfind(closer)
        if i != -1 and j != -1 and j > i:
            try:
                return json.loads(raw[i:j + 1])
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None
