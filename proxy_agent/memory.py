import json
from datetime import datetime, timezone

from .db import get_conn


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(kind: str, source: str, payload: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events(ts, kind, source, payload_json) VALUES(?,?,?,?)",
        (utc_now(), kind, source, json.dumps(payload, ensure_ascii=False)),
    )
    conn.commit()
    eid = cur.lastrowid
    conn.close()
    return int(eid)


def get_recent_events(limit: int = 30) -> list[dict]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    events = []
    for row in reversed(rows):
        events.append(
            {
                "id": row["id"],
                "ts": row["ts"],
                "kind": row["kind"],
                "source": row["source"],
                "payload": json.loads(row["payload_json"]),
            }
        )
    return events


def get_summary(scope: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT text FROM summaries WHERE scope = ?", (scope,))
    row = cur.fetchone()
    conn.close()
    return row["text"] if row else ""


def set_summary(scope: str, text: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO summaries(scope, text, ts)
        VALUES(?,?,?)
        ON CONFLICT(scope) DO UPDATE SET text=excluded.text, ts=excluded.ts
        """,
        (scope, text, utc_now()),
    )
    conn.commit()
    conn.close()
