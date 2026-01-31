import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch

from proxy_agent import db


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    """Redirect the database to a temporary file for every test."""
    test_db = tmp_path / "test_agent.db"
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield test_db
