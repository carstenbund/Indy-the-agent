import sqlite3
from pathlib import Path

DB_PATH = Path("agent.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            kind TEXT NOT NULL,
            source TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )"""
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS summaries(
            scope TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            ts TEXT NOT NULL
        )"""
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS secrets_blocklist(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern TEXT NOT NULL
        )"""
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS identity_models(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            model_json TEXT NOT NULL
        )"""
    )
    conn.commit()
    conn.close()
