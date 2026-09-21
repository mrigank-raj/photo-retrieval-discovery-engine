import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import evaluate, relevance  # noqa: E402

ITEMS = [{"source": "reddit", "title": "T", "text": f"post {i}"} for i in range(5)]


def fake_generate(model, prompt, schema):
    """Answers every item except number 3 in the first pass; answers a one-item retry normally."""
    n = prompt.count("### ")
    ids = range(n) if n == 1 else [i for i in range(n) if i != 3]
    return [{"i": i, "language": "english", "problem_family": "search_or_retrieval", "confidence": "high"} for i in ids]


def test_prompt_contains_definitions_and_items():
    p = relevance.build_prompt(ITEMS[:2])
    assert "search_or_retrieval:" in p and "### 0 | source: reddit" in p and "### 1 |" in p and "{items}" not in p


def test_classify_retries_items_the_model_skipped():
    out = relevance.classify(ITEMS, "m", batch=5, generate=fake_generate)
    assert all(o is not None for o in out) and len(out) == 5


def test_to_label_language_wins_over_family():
    assert relevance.to_label({"language": "not_english", "problem_family": "search_or_retrieval"}) == "not_english"
    assert relevance.to_label({"language": "english", "problem_family": "other"}) == "other"
    assert relevance.to_label(None) is None


def test_metrics_precision_recall():
    gold = ["search_or_retrieval"] * 4 + ["other"] * 6
    pred = ["search_or_retrieval"] * 3 + ["other"] + ["search_or_retrieval"] + ["other"] * 5
    m = evaluate.metrics(gold, pred)
    assert (m["tp"], m["fp"], m["fn"]) == (3, 1, 1)
    assert m["precision"] == 0.75 and m["recall"] == 0.75 and m["agreement"] == 0.8
