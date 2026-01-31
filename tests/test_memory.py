import json

import pytest

from proxy_agent.memory import append_event, get_recent_events, get_summary, set_summary


class TestAppendEvent:
    def test_returns_positive_id(self):
        eid = append_event("input", "user", {"title": "test"})
        assert isinstance(eid, int)
        assert eid >= 1

    def test_sequential_ids(self):
        id1 = append_event("input", "user", {"n": 1})
        id2 = append_event("output", "agent", {"n": 2})
        assert id2 > id1


class TestGetRecentEvents:
    def test_empty_db(self):
        events = get_recent_events()
        assert events == []

    def test_returns_events_in_chronological_order(self):
        append_event("input", "user", {"seq": 1})
        append_event("output", "agent", {"seq": 2})
        append_event("tool", "moltbook.create_post", {"seq": 3})
        events = get_recent_events()
        assert len(events) == 3
        assert events[0]["payload"]["seq"] == 1
        assert events[1]["payload"]["seq"] == 2
        assert events[2]["payload"]["seq"] == 3

    def test_limit(self):
        for i in range(10):
            append_event("input", "user", {"i": i})
        events = get_recent_events(limit=3)
        assert len(events) == 3
        # Should return the *last* 3 events in chronological order
        assert events[0]["payload"]["i"] == 7
        assert events[2]["payload"]["i"] == 9

    def test_event_fields(self):
        append_event("input", "user", {"key": "value"})
        events = get_recent_events(1)
        e = events[0]
        assert "id" in e
        assert "ts" in e
        assert e["kind"] == "input"
        assert e["source"] == "user"
        assert e["payload"] == {"key": "value"}


class TestSummary:
    def test_get_missing_summary_returns_empty(self):
        assert get_summary("nonexistent") == ""

    def test_set_and_get(self):
        set_summary("self", "I am an agent.")
        assert get_summary("self") == "I am an agent."

    def test_upsert_overwrites(self):
        set_summary("self", "first version")
        set_summary("self", "second version")
        assert get_summary("self") == "second version"

    def test_multiple_scopes(self):
        set_summary("self", "self summary")
        set_summary("other", "other summary")
        assert get_summary("self") == "self summary"
        assert get_summary("other") == "other summary"
