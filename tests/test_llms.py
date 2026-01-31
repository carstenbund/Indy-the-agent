import os
from unittest.mock import patch, MagicMock

import pytest

from proxy_agent.llms import (
    LLMError,
    _post_json,
    call_openai_compat,
    call_ollama,
    call_claude,
    route_call,
)


# ---------------------------------------------------------------------------
# _post_json
# ---------------------------------------------------------------------------

class TestPostJson:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "ok"}
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp) as mock_post:
            data = _post_json("http://example.com/api", {"X-Key": "k"}, {"q": 1})
        mock_post.assert_called_once_with(
            "http://example.com/api",
            headers={"X-Key": "k"},
            json={"q": 1},
            timeout=60,
        )
        assert data == {"result": "ok"}

    def test_http_error_raises(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp):
            with pytest.raises(LLMError, match="LLM HTTP 500"):
                _post_json("http://example.com/api", {}, {})

    def test_custom_timeout(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp) as mock_post:
            _post_json("http://example.com", {}, {}, timeout=30)
        assert mock_post.call_args.kwargs["timeout"] == 30


# ---------------------------------------------------------------------------
# call_openai_compat
# ---------------------------------------------------------------------------

class TestCallOpenaiCompat:
    def test_returns_content(self):
        api_response = {"choices": [{"message": {"content": "Hello from OpenAI"}}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            result = call_openai_compat(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": "hi"}],
                base_url="https://api.openai.com/v1",
                api_key="sk-test",
            )
        assert result == "Hello from OpenAI"
        call_args = mock_pj.call_args
        assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
        assert call_args[0][1]["Authorization"] == "Bearer sk-test"
        payload = call_args[0][2]
        assert payload["model"] == "gpt-4.1-mini"
        assert payload["temperature"] == 0.4

    def test_trailing_slash_stripped(self):
        api_response = {"choices": [{"message": {"content": "ok"}}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_openai_compat("m", [], "https://api.openai.com/v1/", "k")
        assert mock_pj.call_args[0][0] == "https://api.openai.com/v1/chat/completions"

    def test_max_tokens_included_when_set(self):
        api_response = {"choices": [{"message": {"content": "ok"}}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_openai_compat("m", [], "http://url", "k", max_tokens=100)
        assert mock_pj.call_args[0][2]["max_tokens"] == 100

    def test_max_tokens_excluded_when_none(self):
        api_response = {"choices": [{"message": {"content": "ok"}}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_openai_compat("m", [], "http://url", "k")
        assert "max_tokens" not in mock_pj.call_args[0][2]


# ---------------------------------------------------------------------------
# call_ollama
# ---------------------------------------------------------------------------

class TestCallOllama:
    def test_returns_content(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "Hello from Ollama"}}
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp) as mock_post:
            result = call_ollama("llama3.1", [{"role": "user", "content": "hi"}])
        assert result == "Hello from Ollama"
        call_url = mock_post.call_args[0][0]
        assert call_url == "http://localhost:11434/api/chat"

    def test_custom_base_url(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "ok"}}
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp) as mock_post:
            call_ollama("m", [], base_url="http://remote:11434/")
        assert mock_post.call_args[0][0] == "http://remote:11434/api/chat"

    def test_http_error_raises(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp):
            with pytest.raises(LLMError, match="Ollama HTTP 404"):
                call_ollama("m", [])

    def test_temperature_passed(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"message": {"content": "ok"}}
        with patch("proxy_agent.llms.requests.post", return_value=mock_resp) as mock_post:
            call_ollama("m", [], temperature=0.9)
        payload = mock_post.call_args.kwargs["json"]
        assert payload["options"]["temperature"] == 0.9


# ---------------------------------------------------------------------------
# call_claude
# ---------------------------------------------------------------------------

class TestCallClaude:
    def test_returns_content(self):
        api_response = {"content": [{"type": "text", "text": "Hello from Claude"}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            result = call_claude(
                model="claude-sonnet-4-20250514",
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "hi"},
                ],
                api_key="sk-ant-test123",
            )
        assert result == "Hello from Claude"
        url, headers, payload = mock_pj.call_args[0]
        assert url == "https://api.anthropic.com/v1/messages"
        assert headers["x-api-key"] == "sk-ant-test123"
        assert headers["anthropic-version"] == "2023-06-01"

    def test_system_prompt_extracted(self):
        api_response = {"content": [{"type": "text", "text": "ok"}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_claude(
                model="claude-sonnet-4-20250514",
                messages=[
                    {"role": "system", "content": "Be concise."},
                    {"role": "user", "content": "hi"},
                ],
                api_key="k",
            )
        payload = mock_pj.call_args[0][2]
        assert payload["system"] == "Be concise."
        # system message must NOT appear in the messages list
        for msg in payload["messages"]:
            assert msg["role"] != "system"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"

    def test_no_system_prompt(self):
        api_response = {"content": [{"type": "text", "text": "ok"}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_claude(
                model="m",
                messages=[{"role": "user", "content": "hi"}],
                api_key="k",
            )
        payload = mock_pj.call_args[0][2]
        assert "system" not in payload

    def test_custom_base_url(self):
        api_response = {"content": [{"type": "text", "text": "ok"}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_claude("m", [{"role": "user", "content": "hi"}], "k",
                        base_url="https://custom.api.com/")
        assert mock_pj.call_args[0][0] == "https://custom.api.com/v1/messages"

    def test_max_tokens_and_temperature(self):
        api_response = {"content": [{"type": "text", "text": "ok"}]}
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_claude("m", [{"role": "user", "content": "hi"}], "k",
                        temperature=0.8, max_tokens=2048)
        payload = mock_pj.call_args[0][2]
        assert payload["temperature"] == 0.8
        assert payload["max_tokens"] == 2048

    def test_multiple_user_assistant_messages_preserved(self):
        api_response = {"content": [{"type": "text", "text": "ok"}]}
        messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "reply1"},
            {"role": "user", "content": "msg2"},
        ]
        with patch("proxy_agent.llms._post_json", return_value=api_response) as mock_pj:
            call_claude("m", messages, "k")
        payload = mock_pj.call_args[0][2]
        assert len(payload["messages"]) == 3
        assert payload["messages"][0] == {"role": "user", "content": "msg1"}
        assert payload["messages"][1] == {"role": "assistant", "content": "reply1"}
        assert payload["messages"][2] == {"role": "user", "content": "msg2"}


# ---------------------------------------------------------------------------
# route_call
# ---------------------------------------------------------------------------

class TestRouteCall:
    def test_routes_to_openai_compat_by_default(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch("proxy_agent.llms.call_openai_compat", return_value="openai result") as mock_fn:
            result = route_call([{"role": "user", "content": "hi"}], "draft")
        assert result == "openai result"
        mock_fn.assert_called_once()

    def test_routes_to_ollama(self, monkeypatch):
        monkeypatch.setenv("LLM_DRAFT_BACKEND", "ollama")
        with patch("proxy_agent.llms.call_ollama", return_value="ollama result") as mock_fn:
            result = route_call([{"role": "user", "content": "hi"}], "draft")
        assert result == "ollama result"
        mock_fn.assert_called_once()

    def test_routes_to_claude(self, monkeypatch):
        monkeypatch.setenv("LLM_VOICE_BACKEND", "claude")
        monkeypatch.setenv("LLM_VOICE_MODEL", "claude-sonnet-4-20250514")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        with patch("proxy_agent.llms.call_claude", return_value="claude result") as mock_fn:
            result = route_call([{"role": "user", "content": "hi"}], "voice")
        assert result == "claude result"
        mock_fn.assert_called_once()
        kwargs = mock_fn.call_args
        assert kwargs[0][0] == "claude-sonnet-4-20250514"  # model
        assert kwargs[0][2] == "sk-ant-test"  # api_key

    def test_claude_max_tokens_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_SUMMARIZE_BACKEND", "claude")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("LLM_SUMMARIZE_MAX_TOKENS", "1024")
        with patch("proxy_agent.llms.call_claude", return_value="ok") as mock_fn:
            route_call([], "summarize")
        assert mock_fn.call_args.kwargs["max_tokens"] == 1024

    def test_claude_custom_base_url(self, monkeypatch):
        monkeypatch.setenv("LLM_DRAFT_BACKEND", "claude")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://custom.proxy.com")
        with patch("proxy_agent.llms.call_claude", return_value="ok") as mock_fn:
            route_call([], "draft")
        assert mock_fn.call_args.kwargs["base_url"] == "https://custom.proxy.com"

    def test_unknown_backend_raises(self, monkeypatch):
        monkeypatch.setenv("LLM_DRAFT_BACKEND", "nonexistent")
        with pytest.raises(LLMError, match="Unknown backend: nonexistent"):
            route_call([], "draft")

    def test_custom_temperature(self, monkeypatch):
        monkeypatch.setenv("LLM_DRAFT_BACKEND", "ollama")
        monkeypatch.setenv("LLM_DRAFT_TEMP", "0.9")
        with patch("proxy_agent.llms.call_ollama", return_value="ok") as mock_fn:
            route_call([], "draft")
        assert mock_fn.call_args.kwargs["temperature"] == 0.9

    def test_custom_model(self, monkeypatch):
        monkeypatch.setenv("LLM_VOICE_BACKEND", "ollama")
        monkeypatch.setenv("LLM_VOICE_MODEL", "mistral")
        with patch("proxy_agent.llms.call_ollama", return_value="ok") as mock_fn:
            route_call([], "voice")
        assert mock_fn.call_args[0][0] == "mistral"
