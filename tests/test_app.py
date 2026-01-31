from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from proxy_agent.app import app


@pytest.fixture()
def client():
    # Trigger startup to init db + seed summary
    with TestClient(app) as c:
        yield c


class TestDraftEndpoint:
    def _mock_route_call(self, messages, purpose):
        """Simple mock that returns purpose-tagged text."""
        return f"[{purpose}] generated text"

    def test_draft_returns_ok(self, client):
        with patch("proxy_agent.app.route_call", side_effect=self._mock_route_call), \
             patch("proxy_agent.app.canonicalize", return_value="canonicalized"):
            resp = client.post("/draft", json={
                "title": "Test Post",
                "body": "Some content here.",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "ok" in data
        assert data["text"] == "canonicalized"

    def test_draft_with_all_fields(self, client):
        with patch("proxy_agent.app.route_call", side_effect=self._mock_route_call), \
             patch("proxy_agent.app.canonicalize", return_value="canonicalized"):
            resp = client.post("/draft", json={
                "title": "Full Post",
                "body": "Body content.",
                "submolt": "philosophy",
                "publish": False,
                "intent": "moltbook_post",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_draft_blocks_secrets_in_output(self, client):
        secret_text = "leaked sk-abc123def456ghi789jkl012mno345pqr"
        with patch("proxy_agent.app.route_call", side_effect=self._mock_route_call), \
             patch("proxy_agent.app.canonicalize", return_value=secret_text):
            resp = client.post("/draft", json={
                "title": "Leak Test",
                "body": "Check for secret leaking.",
            })
        data = resp.json()
        assert data["ok"] is False
        assert "Blocked" in data["reason"]

    def test_draft_missing_title_returns_422(self, client):
        resp = client.post("/draft", json={"body": "no title"})
        assert resp.status_code == 422

    def test_draft_missing_body_returns_422(self, client):
        resp = client.post("/draft", json={"title": "no body"})
        assert resp.status_code == 422

    def test_draft_default_intent(self, client):
        """The default intent should be moltbook_post."""
        with patch("proxy_agent.app.route_call", side_effect=self._mock_route_call), \
             patch("proxy_agent.app.canonicalize", return_value="text"), \
             patch("proxy_agent.app.append_event") as mock_ae:
            resp = client.post("/draft", json={
                "title": "T",
                "body": "B",
            })
        # First call to append_event is the input event
        input_payload = mock_ae.call_args_list[0][0][2]
        assert input_payload["intent"] == "moltbook_post"

    def test_canonicalize_receives_draft_output(self, client):
        """The draft LLM output should be passed to canonicalize."""
        with patch("proxy_agent.app.route_call", return_value="raw draft output") as mock_rc, \
             patch("proxy_agent.app.canonicalize", return_value="final") as mock_canon:
            resp = client.post("/draft", json={
                "title": "T",
                "body": "B",
            })
        # canonicalize should receive the stripped draft output
        mock_canon.assert_called_once()
        assert mock_canon.call_args[0][0] == "raw draft output"


class TestStartup:
    def test_self_summary_seeded(self, client):
        from proxy_agent.memory import get_summary
        summary = get_summary("self")
        assert "persistence" in summary.lower() or "memory" in summary.lower()
