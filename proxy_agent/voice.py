from .llms import route_call
from .prompts import VOICE_SYSTEM


def canonicalize(text: str, self_summary: str) -> str:
    messages = [
        {"role": "system", "content": VOICE_SYSTEM},
        {
            "role": "user",
            "content": (
                "Self-summary (for consistency):\n"
                f"{self_summary}\n\nText to canonicalize:\n{text}"
            ),
        },
    ]
    return route_call(messages, purpose="voice").strip()
