import sqlite3

from proxy_agent.db import get_conn, init_db


class TestInitDb:
    def test_creates_events_table(self):
        conn = get_conn()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        assert cur.fetchone() is not None
        conn.close()

    def test_creates_summaries_table(self):
        conn = get_conn()
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='summaries'")
        assert cur.fetchone() is not None
        conn.close()

    def test_creates_secrets_blocklist_table(self):
        conn = get_conn()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='secrets_blocklist'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_idempotent(self):
        # Calling init_db twice should not raise
        init_db()
        init_db()
        conn = get_conn()
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        conn.close()
        names = [t["name"] for t in tables]
        assert "events" in names
        assert "summaries" in names
        assert "secrets_blocklist" in names


class TestGetConn:
    def test_row_factory(self):
        conn = get_conn()
        conn.execute("INSERT INTO summaries(scope, text, ts) VALUES('t','t','t')")
        row = conn.execute("SELECT * FROM summaries WHERE scope='t'").fetchone()
        # sqlite3.Row should allow dict-like access
        assert row["scope"] == "t"
        conn.close()
