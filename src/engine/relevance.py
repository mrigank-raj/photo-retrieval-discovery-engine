"""LLM relevance classifier: is a post about finding or re-finding photos, and in what language?"""
from pathlib import Path

import yaml

from engine import llm

ROOT = Path(__file__).resolve().parents[2]
TEXT_LIMIT = 1200


def _taxonomy():
    return yaml.safe_load((ROOT / "config" / "taxonomy.yaml").read_text(encoding="utf8"))["problem_family"]


def schema():
    return {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "i": {"type": "INTEGER"},
        "language": {"type": "STRING", "enum": ["english", "not_english"]},
        "problem_family": {"type": "STRING", "enum": list(_taxonomy())},
        "confidence": {"type": "STRING", "enum": ["high", "medium", "low"]}},
        "required": ["i", "language", "problem_family", "confidence"]}}


def build_prompt(items):
    families = "\n".join(f"- {name}: {desc}" for name, desc in _taxonomy().items())
    blocks = []
    for i, it in enumerate(items):
        text = it["text"] if len(it["text"]) <= TEXT_LIMIT else it["text"][:TEXT_LIMIT] + " [...]"
        blocks.append(f"### {i} | source: {it['source']} | thread or review title: {it.get('title') or '-'}\n{text}")
    template = (ROOT / "prompts" / "relevance.md").read_text(encoding="utf8")
    return template.replace("{families}", families).replace("{items}", "\n\n".join(blocks))


def _classify_batch(items, model, generate):
    answer = generate(model, build_prompt(items), schema())
    return {a["i"]: a for a in answer if isinstance(a, dict) and a.get("i") in range(len(items))}


def classify(items, model, batch=20, generate=llm.generate_json, progress=None):
    """items: dicts with source, title, text. Returns one dict per item (or None if the model never answered for it)."""
    out = [None] * len(items)
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        got = _classify_batch(chunk, model, generate)
        missing = [i for i in range(len(chunk)) if i not in got]
        for i in missing:  # retry gaps one item at a time
            got.update({i: v for k, v in _classify_batch([chunk[i]], model, generate).items() if k == 0})
        for i in range(len(chunk)):
            out[start + i] = got.get(i) if i in got else None
        if progress:
            progress(min(start + batch, len(items)), len(items))
    return out


def to_label(pred):
    """Collapse language and family into the single label used in the labeled set."""
    if pred is None:
        return None
    return "not_english" if pred["language"] == "not_english" else pred["problem_family"]
