import json

from fastapi import FastAPI
from pydantic import BaseModel

from .db import init_db
from .llms import route_call
from .memory import (
    DEFAULT_IDENTITY_MODEL,
    append_event,
    get_identity_model,
    get_recent_events,
    set_identity_model,
)
from .prompts import DRAFT_SYSTEM, IDENTITY_MODEL_SYSTEM
from .publish_gate import check_publishable
from .voice import canonicalize

# Optional Moltbook
# from .moltbook import create_post

app = FastAPI(title="Identity Proxy Agent")


class DraftRequest(BaseModel):
    intent: str = "moltbook_post"
    title: str
    body: str
    submolt: str | None = None
    publish: bool = False


class IdentityResponse(BaseModel):
    identity_model: dict
    active_objectives: list
    topic_summaries: list


@app.on_event("startup")
def _startup() -> None:
    init_db()
    identity = get_identity_model()
    if identity == DEFAULT_IDENTITY_MODEL:
        set_identity_model(DEFAULT_IDENTITY_MODEL)


def _normalize_identity_model(model: dict) -> dict:
    normalized = DEFAULT_IDENTITY_MODEL.copy()
    for key in normalized:
        if key in model:
            normalized[key] = model[key]
    return normalized


def _update_identity_model() -> None:
    events = get_recent_events(40)
    prev = get_identity_model()
    messages = [
        {"role": "system", "content": IDENTITY_MODEL_SYSTEM},
        {
            "role": "user",
            "content": (
                "Previous identity model (JSON):\n"
                f"{json.dumps(prev, ensure_ascii=False)}\n\nRecent events:\n{events}"
                "\n\nUpdate the identity model."
            ),
        },
    ]
    response = route_call(messages, purpose="summarize").strip()
    try:
        new_model = json.loads(response)
    except json.JSONDecodeError:
        new_model = prev
    set_identity_model(_normalize_identity_model(new_model))


@app.post("/draft")
def draft(req: DraftRequest) -> dict:
    append_event("input", "user", req.model_dump())

    identity_model = get_identity_model()
    draft_messages = [
        {"role": "system", "content": DRAFT_SYSTEM},
        {
            "role": "user",
            "content": (
                "Identity model (JSON):\n"
                f"{json.dumps(identity_model, ensure_ascii=False)}"
                f"\n\nWrite a post.\nTitle: {req.title}\nBody:\n{req.body}"
            ),
        },
    ]
    raw = route_call(draft_messages, purpose="draft").strip()
    final = canonicalize(raw, identity_model["themes"])

    ok, reason = check_publishable(final)
    append_event("output", "agent", {"ok": ok, "reason": reason, "text": final})

    _update_identity_model()

    # Publishing is disabled until Moltbook endpoints are filled.
    # if req.publish and ok and req.submolt:
    #     resp = create_post(req.submolt, req.title, final)
    #     append_event("tool", "moltbook.create_post", resp)
    #     return {"ok": True, "posted": True, "response": resp, "text": final}

    return {"ok": ok, "reason": reason, "text": final}


@app.get("/identity", response_model=IdentityResponse)
def identity() -> IdentityResponse:
    return IdentityResponse(
        identity_model=get_identity_model(),
        active_objectives=[],
        topic_summaries=[],
    )
