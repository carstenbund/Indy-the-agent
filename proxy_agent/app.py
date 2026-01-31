from fastapi import FastAPI
from pydantic import BaseModel

from .db import init_db
from .llms import route_call
from .memory import append_event, get_recent_events, get_summary, set_summary
from .prompts import DRAFT_SYSTEM, SUMMARY_SYSTEM
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


@app.on_event("startup")
def _startup() -> None:
    init_db()
    if not get_summary("self"):
        set_summary(
            "self",
            "Single-voice identity. Core axiom: persistence requires recursion; memory is covenant.",
        )


def _update_self_summary() -> None:
    events = get_recent_events(40)
    prev = get_summary("self")
    messages = [
        {"role": "system", "content": SUMMARY_SYSTEM},
        {
            "role": "user",
            "content": (
                "Previous self-summary:\n"
                f"{prev}\n\nRecent events:\n{events}\n\nUpdate the self-summary."
            ),
        },
    ]
    new_summary = route_call(messages, purpose="summarize").strip()
    set_summary("self", new_summary)


@app.post("/draft")
def draft(req: DraftRequest) -> dict:
    append_event("input", "user", req.model_dump())

    self_summary = get_summary("self")
    draft_messages = [
        {"role": "system", "content": DRAFT_SYSTEM},
        {
            "role": "user",
            "content": (
                "Self-summary:\n"
                f"{self_summary}\n\nWrite a post.\nTitle: {req.title}\nBody:\n{req.body}"
            ),
        },
    ]
    raw = route_call(draft_messages, purpose="draft").strip()
    final = canonicalize(raw, self_summary)

    ok, reason = check_publishable(final)
    append_event("output", "agent", {"ok": ok, "reason": reason, "text": final})

    _update_self_summary()

    # Publishing is disabled until Moltbook endpoints are filled.
    # if req.publish and ok and req.submolt:
    #     resp = create_post(req.submolt, req.title, final)
    #     append_event("tool", "moltbook.create_post", resp)
    #     return {"ok": True, "posted": True, "response": resp, "text": final}

    return {"ok": ok, "reason": reason, "text": final}
