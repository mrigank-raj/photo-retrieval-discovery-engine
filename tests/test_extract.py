import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import extract  # noqa: E402

TAX = extract.taxonomy()
TEXT = "I can’t find my 2014 photos.  I typed \"Paris\" and got nothing;\nI don't remember the month."


def rec(**kw):
    base = {"i": 0, "photo_type": "unknown", "photo_age": None, "target_description": "find 2014 photos",
            "cues": [], "queries_tried": [], "search_pattern": "not_stated", "workaround": None,
            "failure_mode": "cue_mismatch", "severity": "unclear", "outcome": "not_found", "product_mentioned": None,
            "confidence": "high", "evidence_quotes": []}
    return {**base, **kw}


def test_valid_record_with_verbatim_quotes_passes_despite_curly_quotes_and_whitespace():
    r = rec(cues=[{"type": "when", "value": "2014", "status": "remembered", "quote": "I can't find my 2014 photos"},
                  {"type": "when", "value": "month", "status": "forgotten", "quote": "I don't remember the month"}],
            queries_tried=["Paris"], evidence_quotes=["got nothing"])
    assert extract.validate(r, TEXT, TAX) == []


def test_paraphrased_quote_and_bad_enum_are_rejected():
    r = rec(failure_mode="made_up", cues=[{"type": "when", "value": "2014", "status": "remembered",
                                           "quote": "cannot locate photos from 2014"}])
    errs = extract.validate(r, TEXT, TAX)
    assert any("failure_mode" in e for e in errs) and any("not verbatim" in e for e in errs)


def test_query_not_in_text_is_rejected():
    assert any("query" in e for e in extract.validate(rec(queries_tried=["London"]), TEXT, TAX))


def test_extract_retries_an_invalid_item_once_then_sends_it_to_review():
    calls = []

    def fake(model, prompt, schema, **kw):
        calls.append("rejected" in prompt)
        bad = rec(evidence_quotes=["this is invented"])
        good = rec(evidence_quotes=["got nothing"])
        return [bad] if "rejected" not in prompt else ([good] if len(calls) == 2 else [bad])

    items = [{"source": "reddit", "title": "t", "text": TEXT}]
    records, review = extract.extract(items, "m", generate=fake)
    assert records[0] is not None and review == [] and calls == [False, True]

    def always_bad(model, prompt, schema, **kw):
        return [rec(evidence_quotes=["this is invented"])]

    records, review = extract.extract(items, "m", generate=always_bad)
    assert records[0] is None and review and "not verbatim" in review[0][1]


def test_prompt_marks_thread_starter_as_context_only_and_injects_definitions():
    p = extract.build_prompt([{"source": "reddit", "title": "T", "text": "reply text", "starter": "the original post"}], TAX)
    assert "context only, never quote" in p and "the original post" in p and "- missing_wrong_metadata:" in p and "{failure_mode}" not in p
