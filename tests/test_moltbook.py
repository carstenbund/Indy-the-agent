import os
from unittest.mock import patch, MagicMock

import pytest

from proxy_agent.moltbook import MoltbookError, create_post, _headers


class TestHeaders:
    def test_missing_token_raises(self, monkeypatch):
        monkeypatch.delenv("MOLTBOOK_TOKEN", raising=False)
        with pytest.raises(MoltbookError, match="Missing MOLTBOOK_TOKEN"):
            _headers()

    def test_returns_bearer_header(self, monkeypatch):
        monkeypatch.setenv("MOLTBOOK_TOKEN", "tok-123")
        h = _headers()
        assert h["Authorization"] == "Bearer tok-123"
        assert h["Content-Type"] == "application/json"


class TestCreatePost:
    def test_success(self, monkeypatch):
        monkeypatch.setenv("MOLTBOOK_TOKEN", "tok-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1, "url": "https://moltbook.com/p/1"}
        with patch("proxy_agent.moltbook.requests.post", return_value=mock_resp) as mock_post:
            result = create_post("philosophy", "Title", "Body text")
        assert result == {"id": 1, "url": "https://moltbook.com/p/1"}
        call_url = mock_post.call_args[0][0]
        assert call_url == "https://moltbook.com/api/posts"

    def test_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("MOLTBOOK_TOKEN", "tok-123")
        monkeypatch.setenv("MOLTBOOK_BASE_URL", "https://custom.moltbook.io/")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        with patch("proxy_agent.moltbook.requests.post", return_value=mock_resp) as mock_post:
            create_post("sub", "t", "b")
        assert mock_post.call_args[0][0] == "https://custom.moltbook.io/api/posts"

    def test_http_error_raises(self, monkeypatch):
        monkeypatch.setenv("MOLTBOOK_TOKEN", "tok-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        with patch("proxy_agent.moltbook.requests.post", return_value=mock_resp):
            with pytest.raises(MoltbookError, match="HTTP 403"):
                create_post("sub", "t", "b")
