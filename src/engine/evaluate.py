"""Measure the LLM relevance classifier against the labeled sample (eval/labeled_relevance.csv)."""
import collections
import csv
import json
from pathlib import Path

from engine import llm, relevance

ROOT = Path(__file__).resolve().parents[2]
POSITIVE = "search_or_retrieval"


def metrics(gold, pred):
    """gold/pred: parallel lists of labels. Returns dict with binary precision/recall/F1 for POSITIVE and 8-class agreement."""
    tp = sum(g == POSITIVE and p == POSITIVE for g, p in zip(gold, pred))
    fp = sum(g != POSITIVE and p == POSITIVE for g, p in zip(gold, pred))
    fn = sum(g == POSITIVE and p != POSITIVE for g, p in zip(gold, pred))
    prec, rec = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
            "agreement": sum(g == p for g, p in zip(gold, pred)) / len(gold)}


def run(model):
    rows = list(csv.DictReader(open(ROOT / "eval" / "labeled_relevance.csv", encoding="utf-8-sig")))
    items = [{"source": r["source"], "title": r["title"], "text": r["text"]} for r in rows]
    preds = relevance.classify(items, model, progress=lambda d, n: print(f"  classified {d}/{n}", flush=True))
    labels = [relevance.to_label(p) for p in preds]
    answered = [i for i, p in enumerate(labels) if p is not None]
    gold = [rows[i]["problem_family"] for i in answered]
    pred = [labels[i] for i in answered]
    m = metrics(gold, pred)
    print(f"\nmodel {model}: answered {len(answered)}/{len(rows)} | requests {llm.usage['requests']} "
          f"(retries {llm.usage['retries']}) | tokens in {llm.usage['prompt_tokens']} out {llm.usage['output_tokens']}")
    print(f"relevant (search_or_retrieval): precision {m['precision']:.0%}  recall {m['recall']:.0%}  F1 {m['f1']:.0%}  "
          f"[tp {m['tp']} fp {m['fp']} fn {m['fn']}]")
    print(f"8-way agreement with labels: {m['agreement']:.0%}")
    conf = collections.Counter((g, p) for g, p in zip(gold, pred) if g != p)
    print("most common disagreements (gold -> model):", conf.most_common(6))
    print("\nrelevance disagreements:")
    for i in answered:
        g, p = rows[i]["problem_family"], labels[i]
        if (g == POSITIVE) != (p == POSITIVE):
            tag = "MISSED" if g == POSITIVE else "EXTRA "
            print(f"  {tag} gold={g} model={p} [{rows[i]['source']}] {rows[i]['text'][:110]!r} note={rows[i]['notes']!r}")
    out = ROOT / "eval" / "results"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"relevance_preds_{model}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "gold", "model_label", "language", "model_family", "confidence"])
        for r, p in zip(rows, preds):
            w.writerow([r["item_id"], r["problem_family"], relevance.to_label(p) or "",
                        (p or {}).get("language", ""), (p or {}).get("problem_family", ""), (p or {}).get("confidence", "")])
    (out / f"relevance_metrics_{model}.json").write_text(json.dumps(m, indent=1), encoding="utf8")
    return m
