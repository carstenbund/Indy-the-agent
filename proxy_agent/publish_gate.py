import re

from .db import get_conn

DEFAULT_BLOCK_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",
    r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*",
    r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
]


def _load_extra_patterns() -> list[str]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pattern FROM secrets_blocklist")
    rows = cur.fetchall()
    conn.close()
    return [row["pattern"] for row in rows]


def check_publishable(text: str) -> tuple[bool, str]:
    patterns = DEFAULT_BLOCK_PATTERNS + _load_extra_patterns()
    for pattern in patterns:
        if re.search(pattern, text):
            return (False, f"Blocked by pattern: {pattern}")
    return (True, "ok")
