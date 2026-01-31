import os

import requests


class MoltbookError(RuntimeError):
    pass


def _headers() -> dict:
    token = os.environ.get("MOLTBOOK_TOKEN", "")
    if not token:
        raise MoltbookError("Missing MOLTBOOK_TOKEN env var")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def create_post(submolt: str, title: str, body: str) -> dict:
    base = os.environ.get("MOLTBOOK_BASE_URL", "https://moltbook.com")
    url = base.rstrip("/") + "/api/posts"
    payload = {"submolt": submolt, "title": title, "body": body}
    response = requests.post(url, headers=_headers(), json=payload, timeout=30)
    if response.status_code >= 400:
        raise MoltbookError(f"HTTP {response.status_code}: {response.text[:500]}")
    return response.json()
