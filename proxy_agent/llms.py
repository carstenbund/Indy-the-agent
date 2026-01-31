import os
from typing import Optional

import requests


class LLMError(RuntimeError):
    pass


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code >= 400:
        raise LLMError(f"LLM HTTP {response.status_code}: {response.text[:500]}")
    return response.json()


def call_openai_compat(
    model: str,
    messages: list[dict],
    base_url: str,
    api_key: str,
    temperature: float = 0.4,
    max_tokens: Optional[int] = None,
) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    data = _post_json(url, headers, payload)
    return data["choices"][0]["message"]["content"]


def call_ollama(
    model: str,
    messages: list[dict],
    base_url: str = "http://localhost:11434",
    temperature: float = 0.4,
) -> str:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {"model": model, "messages": messages, "options": {"temperature": temperature}}
    response = requests.post(url, json=payload, timeout=120)
    if response.status_code >= 400:
        raise LLMError(f"Ollama HTTP {response.status_code}: {response.text[:500]}")
    data = response.json()
    return data["message"]["content"]


def route_call(messages: list[dict], purpose: str) -> str:
    """
    purpose: 'draft' | 'voice' | 'summarize'
    Configure backends via env.
    """
    backend = os.environ.get(f"LLM_{purpose.upper()}_BACKEND", "openai_compat")
    model = os.environ.get(f"LLM_{purpose.upper()}_MODEL", "gpt-4.1-mini")
    temp = float(os.environ.get(f"LLM_{purpose.upper()}_TEMP", "0.4"))

    if backend == "openai_compat":
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL", "https://api.openai.com/v1")
        api_key = os.environ["OPENAI_API_KEY"]
        return call_openai_compat(model, messages, base_url, api_key, temperature=temp)
    if backend == "ollama":
        ollama_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        return call_ollama(model, messages, base_url=ollama_url, temperature=temp)

    raise LLMError(f"Unknown backend: {backend}")
