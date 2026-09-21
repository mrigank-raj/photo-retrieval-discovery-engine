import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import insights  # noqa: E402

FACTS = {"called": 740, "not_search": 455, "share_pct": 61}


def test_check_numbers_accepts_facts_and_flags_invented_numbers():
    assert insights.check_numbers("61% of 740 posts, and 455 were something else, in the top 3", FACTS) == []
    assert insights.check_numbers("about 62% were something else", FACTS) == ["62%"]
    assert insights.check_numbers("a total of 900 posts", FACTS) == ["900"]


def test_overclaim_words_are_blocked_only_for_minorities():
    assert insights.overclaims("Most posts describe updates", 20) == ["most"]
    assert insights.overclaims("Most posts describe updates", 61) == []
    assert insights.overclaims("Most posts describe updates", None) == []


def test_confidence_comes_from_sample_size_and_source_spread():
    c = lambda n, s, h=False: insights._cand("triage", {}, "x", [], n, s, heuristic=h)  # noqa: E731
    assert insights.confidence(c(100, 5)) == "high"
    assert insights.confidence(c(100, 5, True)) == "medium"      # keyword heuristics are capped
    assert insights.confidence(c(30, 2)) == "medium"
    assert insights.confidence(c(8, 3)) == "low"
    assert insights.confidence(c(200, 1)) == "low"                # one source is never enough


def test_narrate_retries_an_invented_number_and_drops_what_the_verifier_rejects():
    cands = [insights._cand("triage", FACTS, "fb", [], 740, 7, 61), insights._cand("unmet", {"a": 34}, "fb", [], 34, 4)]
    calls = {"write": 0}

    def fake(model, prompt, schema, **kw):
        if schema is insights.VERIFY_SCHEMA:
            return [{"id": i["id"], "ok": i["id"] != "unmet", "issue": "claims a cause" if i["id"] == "unmet" else ""}
                    for i in [{"id": "triage"}, {"id": "unmet"}]]
        calls["write"] += 1
        bad = calls["write"] == 1
        return [{"id": "triage", "headline": "62% of 740 were something else" if bad else "61% of 740 were something else", "so_what": "s", "caveat": "c"},
                {"id": "unmet", "headline": "34 posts have no workaround", "so_what": "s", "caveat": "c"}]

    out = insights.narrate(cands, "m", "m2", generate=fake)
    assert out["triage"]["headline"].startswith("61%")           # the invented 62% was rejected and rewritten
    assert "unmet" not in out                                     # the verifier rejected it twice, so plain text will be used
