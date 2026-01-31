from unittest.mock import patch

from proxy_agent.voice import canonicalize
from proxy_agent.prompts import VOICE_SYSTEM


class TestCanonicalize:
    def test_calls_route_call_with_voice_purpose(self):
        with patch("proxy_agent.voice.route_call", return_value="  canonicalized text  ") as mock_rc:
            result = canonicalize("raw draft", "self summary here")
        assert result == "canonicalized text"
        mock_rc.assert_called_once()
        args = mock_rc.call_args
        assert args[1]["purpose"] == "voice" or args[0][1] == "voice"

    def test_system_prompt_is_voice_system(self):
        with patch("proxy_agent.voice.route_call", return_value="ok") as mock_rc:
            canonicalize("text", "summary")
        messages = mock_rc.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == VOICE_SYSTEM

    def test_user_message_includes_text_and_summary(self):
        with patch("proxy_agent.voice.route_call", return_value="ok") as mock_rc:
            canonicalize("my draft text", "my self summary")
        messages = mock_rc.call_args[0][0]
        user_msg = messages[1]["content"]
        assert "my draft text" in user_msg
        assert "my self summary" in user_msg
