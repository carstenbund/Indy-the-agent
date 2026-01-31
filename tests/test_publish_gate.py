import pytest

from proxy_agent.publish_gate import check_publishable, DEFAULT_BLOCK_PATTERNS
from proxy_agent.db import get_conn


class TestDefaultPatterns:
    def test_openai_api_key_blocked(self):
        ok, reason = check_publishable("my key is sk-abc123def456ghi789jkl012mno")
        assert not ok
        assert "Blocked" in reason

    def test_anthropic_api_key_blocked(self):
        ok, reason = check_publishable("key: sk-ant-api03-abcdefghijklmnopqrst")
        assert not ok
        assert "Blocked" in reason

    def test_bearer_token_blocked(self):
        ok, reason = check_publishable("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test")
        assert not ok
        assert "Blocked" in reason

    def test_private_key_blocked(self):
        ok, reason = check_publishable("-----BEGIN RSA PRIVATE KEY-----\nMIIE...")
        assert not ok
        assert "Blocked" in reason

    def test_ec_private_key_blocked(self):
        ok, reason = check_publishable("-----BEGIN EC PRIVATE KEY-----")
        assert not ok
        assert "Blocked" in reason

    def test_clean_text_allowed(self):
        ok, reason = check_publishable("This is a perfectly safe blog post about agents.")
        assert ok
        assert reason == "ok"

    def test_empty_text_allowed(self):
        ok, reason = check_publishable("")
        assert ok

    def test_short_sk_not_blocked(self):
        # sk- followed by fewer than 20 chars should NOT match
        ok, _ = check_publishable("sk-short")
        assert ok


class TestExtraPatterns:
    def test_custom_db_pattern_blocks(self):
        conn = get_conn()
        conn.execute("INSERT INTO secrets_blocklist(pattern) VALUES(?)", (r"SUPER_SECRET_\d+",))
        conn.commit()
        conn.close()

        ok, reason = check_publishable("The code is SUPER_SECRET_42")
        assert not ok
        assert "SUPER_SECRET" in reason

    def test_multiple_db_patterns(self):
        conn = get_conn()
        conn.execute("INSERT INTO secrets_blocklist(pattern) VALUES(?)", (r"TOKEN_AAA",))
        conn.execute("INSERT INTO secrets_blocklist(pattern) VALUES(?)", (r"TOKEN_BBB",))
        conn.commit()
        conn.close()

        ok1, _ = check_publishable("has TOKEN_AAA inside")
        ok2, _ = check_publishable("has TOKEN_BBB inside")
        ok3, _ = check_publishable("has no tokens")
        assert not ok1
        assert not ok2
        assert ok3
