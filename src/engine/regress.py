"""Regression check: re-run the relevance classifier and extractor on the labeled sets and compare with a saved baseline.

Run it after changing a prompt, the taxonomy or a model. It costs about 30 requests of the free daily quota.
"""
import json
from pathlib import Path

from engine import evaluate, pilot

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "eval" / "baseline.json"
METRICS = ["relevance_precision", "relevance_recall", "relevance_agreement", "extraction_failure_mode",
           "extraction_outcome", "extraction_photo_type", "extraction_cue_precision"]


def compare(current, baseline, tolerance):
    """Rows of (metric, current, baseline, change, ok). A metric fails if it falls by more than `tolerance` (0.05 = 5 points)."""
    rows = []
    for m in METRICS:
        cur, base = current.get(m), baseline.get(m)
        rows.append((m, cur, base, None if cur is None or base is None else cur - base,
                     True if base is None or cur is None else cur >= base - tolerance))
    return rows


def run(relevance_model, extraction_model, update_baseline=False, tolerance=0.05):
    rel = evaluate.run(relevance_model)
    out = ROOT / "data" / "regress_extract.json"
    out.unlink(missing_ok=True)
    pilot.run("sample", str(out), extraction_model, False, 8)
    ext = pilot.scores(str(out))
    current = {"relevance_precision": rel["precision"], "relevance_recall": rel["recall"], "relevance_agreement": rel["agreement"],
               "extraction_failure_mode": ext["failure_mode"], "extraction_outcome": ext["outcome"],
               "extraction_photo_type": ext["photo_type"], "extraction_cue_precision": ext["cue_precision"]}
    if update_baseline or not BASELINE.exists():
        BASELINE.write_text(json.dumps({"models": {"relevance": relevance_model, "extraction": extraction_model}, "metrics": current}, indent=1),
                            encoding="utf8")
        print(f"baseline {'updated' if update_baseline else 'created'}: {BASELINE}")
        return True
    base = json.loads(BASELINE.read_text(encoding="utf8"))["metrics"]
    rows = compare(current, base, tolerance)
    print(f"\n{'metric':<26}{'now':>8}{'baseline':>10}{'change':>9}")
    for m, cur, b, d, ok in rows:
        print(f"{m:<26}{cur:>8.0%}{b:>10.0%}{d:>+9.0%}  {'ok' if ok else 'REGRESSION'}")
    good = all(r[4] for r in rows)
    print("\nPASS: no metric fell by more than %d points." % round(tolerance * 100) if good else
          "\nFAIL: at least one metric fell by more than %d points. Review the change before keeping it." % round(tolerance * 100))
    return good
