"""Phase 3 extraction pilot: choose items, run the extractor, score it against a hand-labeled sample, measure stability."""
import collections
import json
import random
from pathlib import Path

from engine import extract, llm, store

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "engine.db"
SAMPLE = ROOT / "eval" / "extraction_sample.jsonl"
GOLD = ROOT / "eval" / "labeled_extraction.jsonl"
KEYS = ("failure_mode", "outcome", "photo_type", "severity")


def _rows(db, ids):
    q = ",".join("?" * len(ids))
    by_id = {r["item_id"]: r for r in db.execute(
        f"SELECT item_id, source, product, title, text, thread_id FROM raw_items WHERE item_id IN ({q})", ids)}
    return extract.with_starters(db, [by_id[i] for i in ids])


def make_sample(n=100, seed=5):
    db = store.connect(DB_PATH)
    pool = extract.pilot_pool(db)
    rel = {r[0] for r in db.execute("SELECT item_id FROM filter_results WHERE relevant=1")}
    a, b = [i for i in pool if i in rel], [i for i in pool if i not in rel]
    rnd = random.Random(seed)
    rnd.shuffle(a)
    rnd.shuffle(b)
    ids = a[: round(n * 0.7)] + b[: n - round(n * 0.7)]
    rnd.shuffle(ids)
    with open(SAMPLE, "w", encoding="utf8") as f:
        for r in _rows(db, ids):
            f.write(json.dumps({k: r[k] for k in ("item_id", "source", "product", "title", "text", "starter")}) + "\n")
    print(f"pool {len(pool)} items ({len(a)} relevant, {len(b)} comparison); wrote {len(ids)} to {SAMPLE.name}")


def run(pool, out, model, save_db, batch=5):
    db = store.connect(DB_PATH)
    if pool == "sample":
        ids = [json.loads(x)["item_id"] for x in open(SAMPLE, encoding="utf8")]
    elif pool == "recheck":  # non-search items that carry cues or a found/not_found outcome, where the prompt was tightened
        ids = [r[0] for r in db.execute(
            "SELECT e.item_id FROM extractions e WHERE e.failure_mode='not_a_search_problem' AND (e.outcome IN ('found','not_found') "
            "OR EXISTS (SELECT 1 FROM cue_mentions m WHERE m.item_id=e.item_id)) ORDER BY e.item_id")]
    elif pool == "new":  # relevant English items not yet extracted (used by refresh)
        ids = extract.new_pool(db)
    else:
        ids = extract.pilot_pool(db)
    tax_version = extract.taxonomy()["version"]
    path = Path(out)
    state = {"model": model, "taxonomy": tax_version, "records": {}, "review": []}
    if path.exists():  # resume: a free-tier daily quota can stop a run part-way
        prior = json.loads(path.read_text(encoding="utf8"))
        if (prior["model"], prior["taxonomy"]) != (model, tax_version):
            raise SystemExit(f"{path.name} was made with {prior['model']}/{prior['taxonomy']}; use a new --out file")
        state = prior
    done = set(state["records"]) | {r[0] for r in state["review"]}
    rows = _rows(db, [i for i in ids if i not in done]) if len(done) < len(ids) else []
    print(f"{len(ids)} items in the {pool} pool; {len(done)} already done; extracting {len(rows)} with {model}")
    path.parent.mkdir(parents=True, exist_ok=True)

    def flush():
        state["usage"] = llm.usage
        path.write_text(json.dumps(state, indent=1), encoding="utf8")

    def on_batch(start, recs, review):
        for r, rec in zip(rows[start:start + len(recs)], recs):
            if rec:
                state["records"][r["item_id"]] = rec
        state["review"] += [[rows[i]["item_id"], why] for i, why in review if [rows[i]["item_id"], why] not in state["review"]]
        flush()

    stopped = None
    try:
        extract.extract(rows, model, batch=batch, on_batch=on_batch, progress=lambda d, n: print(f"  {d}/{len(rows)}", flush=True))
    except llm.DailyQuotaExhausted as e:
        stopped = str(e)
    flush()
    if save_db:
        run_id = store.log_run(db, "extract", None, {"model": model, "pool": pool, "batch": batch, **store.versions()}, {"saved": len(state["records"])},
                               [stopped] if stopped else [], store.now())
        for item_id, rec in state["records"].items():
            extract.save(db, item_id, rec, model, run_id, tax_version)
        db.executemany("INSERT INTO needs_review VALUES(?,?,?)", [(i, why, None) for i, why in state["review"]])
        db.commit()
    print(f"valid {len(state['records'])}/{len(ids)}; needs_review {len(state['review'])}; requests {llm.usage['requests']}; "
          f"tokens in {llm.usage['prompt_tokens']} out {llm.usage['output_tokens']}; saved {out}")
    if stopped:
        print(f"STOPPED: daily free quota used ({stopped}). Run the same command again later to resume.")
    return stopped


def _agree(a, b, keys=KEYS):
    both = [i for i in a if i in b]
    return {k: sum(a[i][k] == b[i][k] for i in both) / len(both) for k in keys} if both else {}


def scores(run_file):
    """Headline agreement numbers for one extraction run against the gold labels (used by the regression check)."""
    recs = json.loads(Path(run_file).read_text(encoding="utf8"))["records"]
    gold = {}
    for line in open(GOLD, encoding="utf8"):
        g = json.loads(line)
        gold[g["item_id"]] = g
    scored = [i for i in gold if i in recs]
    out = {k: sum(gold[i][k] == recs[i][k] for i in scored) / len(scored) for k in ("failure_mode", "outcome", "photo_type")}
    tp = fp = 0
    for i in scored:
        g = {(c["type"], c["status"]) for c in gold[i]["cues"]}
        m = {(c["type"], c["status"]) for c in recs[i]["cues"]}
        tp, fp = tp + len(g & m), fp + len(m - g)
    out["cue_precision"] = tp / (tp + fp) if tp + fp else 0.0
    out["scored"] = len(scored)
    return out


def evaluate(run_files):
    runs = [json.loads(Path(f).read_text(encoding="utf8")) for f in run_files]
    gold = {}
    for line in open(GOLD, encoding="utf8"):
        g = json.loads(line)
        gold[g["item_id"]] = g
    recs = runs[0]["records"]
    n_gold = len(gold)
    scored = [i for i in gold if i in recs]
    print(f"gold items {n_gold}; extracted and valid in run 1: {len(scored)}; needs_review: {len(runs[0]['review'])}")
    for k in KEYS:
        ok = sum(gold[i][k] == recs[i][k] for i in scored)
        print(f"  {k:<13} agreement {ok / len(scored):.0%} ({ok}/{len(scored)})")
    ns = "not_a_search_problem"
    gs, ms = [gold[i]["failure_mode"] != ns for i in scored], [recs[i]["failure_mode"] != ns for i in scored]
    tp_, fp_ = sum(g and m for g, m in zip(gs, ms)), sum(m and not g for g, m in zip(gs, ms))
    fn_ = sum(g and not m for g, m in zip(gs, ms))
    print(f"  coarse 'is a retrieval failure' (failure_mode is not {ns}): agreement {sum(g == m for g, m in zip(gs, ms)) / len(gs):.0%}, "
          f"precision {tp_ / (tp_ + fp_):.0%}, recall {tp_ / (tp_ + fn_):.0%} [gold positives {sum(gs)}]")
    sub = [i for i in scored if gold[i]["failure_mode"] != ns and recs[i]["failure_mode"] != ns]
    print(f"  among items both call a retrieval failure: exact failure_mode match {sum(gold[i]['failure_mode'] == recs[i]['failure_mode'] for i in sub)}/{len(sub)}")
    known = [i for i in scored if gold[i]["photo_type"] != "unknown"]
    if known:
        print(f"  photo_type where gold is not 'unknown': {sum(gold[i]['photo_type'] == recs[i]['photo_type'] for i in known)}/{len(known)}")
    fm = collections.Counter((gold[i]["failure_mode"], recs[i]["failure_mode"]) for i in scored if gold[i]["failure_mode"] != recs[i]["failure_mode"])
    print("  top failure_mode disagreements (gold -> model):", fm.most_common(6))
    tp = fp = fn = 0
    for i in scored:
        g = {(c["type"], c["status"]) for c in gold[i]["cues"]}
        m = {(c["type"], c["status"]) for c in recs[i]["cues"]}
        tp, fp, fn = tp + len(g & m), fp + len(m - g), fn + len(g - m)
    p, r_ = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn) if tp + fn else 0
    print(f"  cues as (type,status) pairs: precision {p:.0%} recall {r_:.0%} [tp {tp} fp {fp} fn {fn}]")
    remembered = sum(1 for i in scored for c in recs[i]["cues"] if c["status"] == "remembered")
    forgotten = sum(1 for i in scored for c in recs[i]["cues"] if c["status"] == "forgotten")
    print(f"  model cues: remembered {remembered}, forgotten {forgotten}; gold: "
          f"{sum(1 for i in scored for c in gold[i]['cues'] if c['status'] == 'remembered')} / "
          f"{sum(1 for i in scored for c in gold[i]['cues'] if c['status'] == 'forgotten')}")
    for j in range(1, len(runs)):
        s = _agree(recs, runs[j]["records"], KEYS[:3])
        print(f"  stability run 1 vs run {j + 1}: " + ", ".join(f"{k} {v:.0%}" for k, v in s.items()))
    print("\ndisagreements on failure_mode:")
    for i in scored:
        if gold[i]["failure_mode"] != recs[i]["failure_mode"]:
            print(f"  gold={gold[i]['failure_mode']} model={recs[i]['failure_mode']} note={gold[i].get('notes', '')!r} | "
                  f"{recs[i]['target_description'][:90]}")
