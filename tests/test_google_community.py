import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine.collectors import google_community as gc  # noqa: E402

TID = 333561993
MICROS = 1742907274568635  # 2025-03-25T12:54:34Z


def page_with(data):
    """Build a page the way Google does: JSON in a JS string, backslashes doubled and quotes written as \\x22."""
    js = json.dumps(data).replace("\\", "\\\\").replace('"', "\\x22").replace(",null,", ",,").replace("[null,", "[,")
    return f"<html><script>var thread_view='{js}';</script></html>"


def fake_thread():
    thread = [None] * 40
    thread[0] = [TID, "a", 24053, 1]
    thread[8], thread[12] = "Search shows nothing", 'I typed "March" and <b>nothing</b> came up.'
    thread[15], thread[16], thread[21], thread[38] = [["platform", "Android_Pixel"]], MICROS, "photos_searching", MICROS
    reply = [None] * 40
    reply[0], reply[3], reply[16] = [777, "a", TID, 1], "Hi!<div><br></div><div>Try clearing the cache.</div>", MICROS + 60_000_000
    other = [None] * 40  # a reply belonging to a different thread must be ignored
    other[0], other[3], other[16] = [888, "a", 999, 1], "unrelated", MICROS
    return [[[24053]], thread, [[reply]], [[reply]], [other]]


def test_parse_thread_handles_elided_slots_escaped_quotes_and_duplicate_replies():
    t = gc.parse_thread(page_with(fake_thread()), TID)
    assert t["title"] == "Search shows nothing"
    assert t["body"] == 'I typed "March" and nothing came up.'
    assert (t["category"], t["platform"], t["created_at"]) == ("photos_searching", "Android_Pixel", "2025-03-25T12:54:34+00:00")
    assert [r["id"] for r in t["replies"]] == [777]
    assert t["replies"][0]["text"] == "Hi!\n\nTry clearing the cache."


def test_parse_thread_returns_none_when_page_has_no_data():
    assert gc.parse_thread("<html>Security Verification</html>", TID) is None
