"""Usage (from the project root): PYTHONPATH=src python -m engine.cli <command> --help"""
import argparse
import importlib
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

from engine import store

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "engine.db"
SOURCES = ["appstore", "play", "youtube", "reddit", "google_community", "stackexchange", "hackernews"]


def init_db(path=DB_PATH):
    return store.init_db(path)


def load_yaml(name):
    return yaml.safe_load((ROOT / "config" / name).read_text(encoding="utf8"))


def check_config():
    src, tax = load_yaml("sources.yaml"), load_yaml("taxonomy.yaml")
    print(f"taxonomy {tax['version']}: {len(tax) - 1} enums")
    for name, cfg in src["sources"].items():
        state = "ON " if cfg["enabled"] else "OFF"
        note = " (needs your decision)" if cfg.get("requires_user_decision") else ""
        print(f"  {state} {name}{note}")


def _get(url, **kw):
    return requests.get(url, timeout=20, **kw)


def check_keys():
    load_dotenv(ROOT / ".env")
    gemini = "https://generativelanguage.googleapis.com/v1beta/models"
    checks = {  # var: (probe, required)
        "AUTHOR_HASH_SALT": (lambda k: True, True),
        "GEMINI_API_KEY": (lambda k: _get(gemini, params={"key": k, "pageSize": 100}), True),
        "APIFY_TOKEN": (lambda k: _get("https://api.apify.com/v2/users/me", params={"token": k}), True),
        "YOUTUBE_API_KEY": (lambda k: _get("https://www.googleapis.com/youtube/v3/videos",
                                           params={"part": "id", "id": "dQw4w9WgXcQ", "key": k}), True),
        "GROQ_API_KEY": (lambda k: _get("https://api.groq.com/openai/v1/models",
                                        headers={"Authorization": f"Bearer {k}"}), False),
    }
    ok_all = True
    for var, (probe, required) in checks.items():
        key = os.getenv(var)
        if not key:
            print(f"  {'MISSING' if required else 'skipped'} {var}" + ("" if required else " (optional)"))
            ok_all &= not required
            continue
        try:
            r = probe(key)
            good = r is True or r.status_code == 200
        except requests.RequestException as e:
            good, r = False, e
        print(f"  {'OK     ' if good else 'FAILED '} {var}" + ("" if good else f" ({getattr(r, 'status_code', r)})"))
        ok_all &= good or not required
    return ok_all


def collect(source, limit, products, extra):
    load_dotenv(ROOT / ".env")
    cfg = load_yaml("sources.yaml")
    if not cfg["sources"][source]["enabled"]:
        sys.exit(f"{source} is disabled in config/sources.yaml")
    keys = products or list(cfg["products"])
    started = store.now()
    items, errors = importlib.import_module(f"engine.collectors.{source}").fetch(cfg, limit, keys, **extra)
    months = cfg["sources"][source].get("window_months", cfg["window_months"])  # per-source override
    since = (date.today() - timedelta(days=30 * months)).isoformat()
    init_db()
    db = store.connect(DB_PATH)
    counts = store.insert_items(db, items, since)
    run_id = store.log_run(db, "collect", source, {"limit": limit, "products": keys, **extra}, counts, errors, started)
    print(f"run {run_id} {source}: {counts}")
    for e in errors[:10]:
        print("  note:", e)


def coverage():
    db = store.connect(DB_PATH)
    print("items by source x product:")
    for r in db.execute("SELECT source, IFNULL(product,'(unlabeled)') p, COUNT(*) n FROM raw_items GROUP BY 1,2 ORDER BY 1,3 DESC"):
        print(f"  {r['source']:<9} {r['p']:<16} {r['n']}")
    print("totals by source:", {r["source"]: r["n"] for r in db.execute("SELECT source, COUNT(*) n FROM raw_items GROUP BY 1")})
    print("items by year:", {r["y"]: r["n"] for r in db.execute("SELECT substr(created_at,1,4) y, COUNT(*) n FROM raw_items GROUP BY 1 ORDER BY 1")})
    bad = db.execute("SELECT COUNT(*) FROM raw_items WHERE url IS NULL OR url='' OR text IS NULL").fetchone()[0]
    print("items missing url/text:", bad)


def sample(n):
    db = store.connect(DB_PATH)
    for src in [r[0] for r in db.execute("SELECT DISTINCT source FROM raw_items")]:
        print(f"\n=== {src}")
        for r in db.execute("SELECT product, rating, created_at, substr(replace(text, char(10), ' '), 1, 160) t, url FROM raw_items "
                            "WHERE source=? ORDER BY RANDOM() LIMIT ?", (src, n)):
            print(f"- [{r['product']} | {r['rating']} | {str(r['created_at'])[:10]}] {r['t']}\n    {r['url']}")


def run_prefilter(recompute=False):
    """Score items with no keyword-filter result yet; recompute=True rescored everything (after changing the filter rules)."""
    from engine.prefilter import passes
    db = store.connect(DB_PATH)
    rows = db.execute("SELECT item_id, source, title, text FROM raw_items" + ("" if recompute else
                      " WHERE item_id NOT IN (SELECT item_id FROM filter_results)")).fetchall()
    print(f"scoring {len(rows)} item(s)")
    for r in rows:
        db.execute("INSERT INTO filter_results(item_id, prefilter_pass) VALUES(?,?) "
                   "ON CONFLICT(item_id) DO UPDATE SET prefilter_pass=excluded.prefilter_pass",
                   (r["item_id"], int(passes(r["source"], r["title"], r["text"]))))
    db.commit()
    print("prefilter pass rate by source:")
    for r in db.execute("SELECT source, COUNT(*) n, SUM(prefilter_pass) p FROM filter_results f JOIN raw_items USING(item_id) GROUP BY 1"):
        print(f"  {r['source']:<17} {r['p']}/{r['n']}  ({100 * r['p'] // r['n']}%)")


def run_relevance(model, limit):
    """Classify items that passed the keyword filter and have no LLM answer yet. Saves after every chunk."""
    from engine import llm, relevance
    load_dotenv(ROOT / ".env")
    db = store.connect(DB_PATH)
    rows = db.execute("SELECT item_id, source, title, text FROM raw_items JOIN filter_results USING(item_id) "
                      "WHERE prefilter_pass=1 AND relevant IS NULL ORDER BY item_id LIMIT ?", (limit or -1,)).fetchall()
    print(f"{len(rows)} items to classify with {model}")
    started, done, stop = store.now(), 0, None
    run_id = store.log_run(db, "relevance", None, {"model": model, "limit": limit, **store.versions()}, {}, [], started)
    for start in range(0, len(rows), 100):
        chunk = rows[start:start + 100]
        try:
            preds = relevance.classify([dict(r) for r in chunk], model)
        except llm.DailyQuotaExhausted as e:
            stop = f"daily quota exhausted: {e}"
            break
        for r, p in zip(chunk, preds):
            if p is None:
                continue
            fam = relevance.to_label(p)
            db.execute("UPDATE filter_results SET relevant=?, problem_family=?, language=?, confidence=?, model=?, run_id=? "
                       "WHERE item_id=?", (int(fam == "search_or_retrieval"), p["problem_family"], p["language"],
                                           p["confidence"], model, run_id, r["item_id"]))
            done += 1
        db.commit()
        print(f"  saved {done}/{len(rows)} (requests so far {llm.usage['requests']})", flush=True)
    db.execute("UPDATE runs SET counts_json=?, errors_json=? WHERE run_id=?",
               (str({"classified": done, **llm.usage}), str([stop] if stop else []), run_id))
    db.commit()
    print("stopped early:", stop) if stop else print("done")
    return stop


def report():
    """Per-source funnel and memory-cue yield, plus product balance among relevant items."""
    db = store.connect(DB_PATH)
    print(f"{'source':<17}{'items':>6}{'passed':>7}{'classif':>8}{'relevant':>9}{'extracted':>10}{'cues':>6}{'remembered':>11}{'forgotten':>10}{'cues/extr':>10}")
    for r in db.execute("""SELECT r.source,
        COUNT(*) n, SUM(f.prefilter_pass) p, SUM(f.relevant IS NOT NULL) c, SUM(f.relevant=1) rel,
        SUM(e.item_id IS NOT NULL) ex,
        (SELECT COUNT(*) FROM cue_mentions m JOIN raw_items x USING(item_id) WHERE x.source=r.source) cues,
        (SELECT COUNT(*) FROM cue_mentions m JOIN raw_items x USING(item_id) WHERE x.source=r.source AND m.status='remembered') rem,
        (SELECT COUNT(*) FROM cue_mentions m JOIN raw_items x USING(item_id) WHERE x.source=r.source AND m.status='forgotten') fog
        FROM raw_items r JOIN filter_results f USING(item_id) LEFT JOIN extractions e USING(item_id) GROUP BY r.source ORDER BY r.source"""):
        ex = r["ex"] or 0
        print(f"{r['source']:<17}{r['n']:>6}{r['p'] or 0:>7}{r['c'] or 0:>8}{r['rel'] or 0:>9}{ex:>10}{r['cues']:>6}{r['rem']:>11}{r['fog']:>10}{(r['cues'] / ex if ex else 0):>10.2f}")
    print("\nrelevant items by product:")
    tot = db.execute("SELECT COUNT(*) FROM filter_results WHERE relevant=1").fetchone()[0]
    for r in db.execute("SELECT IFNULL(product,'(none)') p, COUNT(*) n FROM raw_items JOIN filter_results USING(item_id) WHERE relevant=1 GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {r['p']:<16}{r['n']:>5}  {100 * r['n'] / tot:.0f}%")


def make_label_sheet(n, rejected, seed):
    import csv
    import random
    rnd = random.Random(seed)
    db = store.connect(DB_PATH)
    pool = {}
    for r in db.execute("SELECT item_id, source, product, title, text, url, prefilter_pass FROM raw_items JOIN filter_results USING(item_id)"):
        pool.setdefault((r["source"], r["prefilter_pass"]), []).append(dict(r))
    sources = sorted({s for s, _ in pool})
    picked = []
    for flag, total in ((1, n - rejected), (0, rejected)):
        per = total // len(sources)
        chosen, leftovers = [], []
        for s in sources:
            items = pool.get((s, flag), [])
            rnd.shuffle(items)
            chosen += items[:per]
            leftovers += items[per:]
        rnd.shuffle(leftovers)
        picked += chosen + leftovers[: total - len(chosen)]
    rnd.shuffle(picked)
    out = ROOT / "eval"
    out.mkdir(exist_ok=True)
    with open(out / "labeling_sheet.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "source", "product", "title", "text", "url", "problem_family", "notes"])
        for it in picked:
            text = it["text"] if len(it["text"]) <= 1500 else it["text"][:1500] + " [...]"
            w.writerow([it["item_id"], it["source"], it["product"] or "", it["title"] or "", text, it["url"], "", ""])
    with open(out / "labeling_key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item_id", "prefilter_pass"])
        w.writerows((it["item_id"], it["prefilter_pass"]) for it in picked)
    print(f"wrote {len(picked)} rows to eval/labeling_sheet.csv (prefilter result kept hidden in eval/labeling_key.csv)")


def main(argv=None):
    p = argparse.ArgumentParser(prog="engine")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("init-db", "check-config", "check-keys", "coverage", "report"):
        sub.add_parser(name)
    for name in ("relevance-eval", "relevance-run"):
        sp = sub.add_parser(name)
        sp.add_argument("--model", default=None, help="default: relevance model in config/llm.yaml")
        if name == "relevance-run":
            sp.add_argument("--limit", type=int, default=0, help="max items (0 = all)")
    pf = sub.add_parser("prefilter")
    pf.add_argument("--recompute", action="store_true", help="rescore every item, not just new ones")
    rf = sub.add_parser("refresh")
    rf.add_argument("--sources", default="", help="comma-separated sources (default: all enabled)")
    rf.add_argument("--skip-collect", action="store_true", help="only process items already collected")
    rf.add_argument("--skip-extract", action="store_true")
    rf.add_argument("--reddit", action="store_true", help="also refresh Reddit (uses Apify free credit; off by default)")
    ca = sub.add_parser("cluster-assign")
    ca.add_argument("--check", action="store_true", help="leave-one-out accuracy of nearest-centre assignment")
    sub.add_parser("export-demo", help="write the slim database used to host the Explorer")
    rg = sub.add_parser("regress")
    rg.add_argument("--update-baseline", action="store_true")
    rg.add_argument("--tolerance", type=float, default=0.05)
    ins = sub.add_parser("insights")
    ins.add_argument("--no-llm", action="store_true", help="use the plain fallback headlines only")
    ins.add_argument("--write-report", action="store_true", help="also update the Key insights block in docs/report.md")
    sub.add_parser("extract-sample")
    er = sub.add_parser("extract-run")
    er.add_argument("--pool", choices=["pilot", "full", "sample", "recheck"], default="pilot", help="pilot and full are the same pool: all relevant items plus the fixed comparison sample")
    er.add_argument("--out", default=str(ROOT / "eval" / "results" / "extraction_run.json"))
    er.add_argument("--model", default=None)
    er.add_argument("--save-db", action="store_true")
    er.add_argument("--batch", type=int, default=5, help="items per request (larger uses fewer of the daily free requests)")
    ee = sub.add_parser("extract-eval")
    ee.add_argument("runs", nargs="+", help="run JSON files; the first is scored, the rest are used for stability")
    cb = sub.add_parser("cluster-build")
    cb.add_argument("--model", default=None)
    cb.add_argument("--no-name", action="store_true", help="skip the LLM naming step")
    sub.add_parser("cluster-report")
    sub.add_parser("cluster-audit")
    sub.add_parser("cluster-apply-audit")
    ls = sub.add_parser("label-sheet")
    ls.add_argument("--n", type=int, default=300)
    ls.add_argument("--rejected", type=int, default=100, help="how many of the n items the prefilter rejected")
    ls.add_argument("--seed", type=int, default=7)
    c = sub.add_parser("collect")
    c.add_argument("source", choices=SOURCES)
    c.add_argument("--limit", type=int, default=300, help="target items for this source")
    c.add_argument("--products", default="", help="comma-separated product keys from sources.yaml (default: all)")
    c.add_argument("--queries", type=int, help="youtube/reddit: number of queries to use")
    c.add_argument("--subs", type=int, help="reddit: number of subreddits to use")
    c.add_argument("--posts-per-url", type=int, help="reddit: posts per subreddit-query search")
    c.add_argument("--max-usd", type=float, help="reddit: hard spend cap for this run (Apify free credit)")
    c.add_argument("--skip", type=int, help="reddit listing: skip the first N subreddits (already collected)")
    c.add_argument("--listing", action="store_true", help="reddit: top-of-year subreddit listings filtered by keyword instead of searches")
    s = sub.add_parser("sample")
    s.add_argument("-n", type=int, default=5)
    a = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252 and choke on emoji
    load_dotenv(ROOT / ".env")
    if a.cmd == "init-db":
        print("database ready:", init_db())
    elif a.cmd == "check-config":
        check_config()
    elif a.cmd == "check-keys":
        sys.exit(0 if check_keys() else 1)
    elif a.cmd == "coverage":
        coverage()
    elif a.cmd == "prefilter":
        run_prefilter(a.recompute)
    elif a.cmd == "report":
        report()
    elif a.cmd == "refresh":
        from engine import refresh
        refresh.run([x for x in a.sources.split(",") if x] or None, a.skip_collect, a.skip_extract, a.reddit)
    elif a.cmd == "cluster-assign":
        from engine import cluster
        db = store.connect(DB_PATH)
        print(cluster.assign_check(db) if a.check else cluster.assign_new(db))
    elif a.cmd == "export-demo":
        from engine import demo
        demo.export(DB_PATH)
    elif a.cmd == "regress":
        from engine import regress
        m = load_yaml("llm.yaml")["providers"]["gemini"]["models"]
        sys.exit(0 if regress.run(m["relevance"], m["extraction"], a.update_baseline, a.tolerance) else 1)
    elif a.cmd == "insights":
        from engine import insights
        m = load_yaml("llm.yaml")["providers"]["gemini"]["models"]
        out = insights.build(m["extraction_strong"], m["relevance"], use_llm=not a.no_llm)
        for k, i in enumerate(out, 1):
            print(f"{k}. [{i['confidence']}{'' if i['written_by_llm'] else ', fallback'}] {i['headline']}")
        if a.write_report:
            insights.write_report(out, ROOT / "docs" / "report.md")
            print("updated docs/report.md")
    elif a.cmd in ("cluster-build", "cluster-report", "cluster-audit", "cluster-apply-audit"):
        from engine import cluster
        init_db()
        if a.cmd == "cluster-build":
            cluster.build(a.model or load_yaml("llm.yaml")["providers"]["gemini"]["models"]["relevance"], not a.no_name)
        else:
            {"cluster-report": cluster.report, "cluster-audit": cluster.audit, "cluster-apply-audit": cluster.apply_audit}[a.cmd]()
    elif a.cmd in ("extract-sample", "extract-run", "extract-eval"):
        from engine import pilot
        if a.cmd == "extract-sample":
            pilot.make_sample()
        elif a.cmd == "extract-eval":
            pilot.evaluate(a.runs)
        else:
            init_db()
            pilot.run(a.pool, a.out, a.model or load_yaml("llm.yaml")["providers"]["gemini"]["models"]["extraction"], a.save_db, a.batch)
    elif a.cmd in ("relevance-eval", "relevance-run"):
        model = a.model or load_yaml("llm.yaml")["providers"]["gemini"]["models"]["relevance"]
        if a.cmd == "relevance-eval":
            from engine import evaluate
            evaluate.run(model)
        else:
            init_db()
            run_relevance(model, a.limit)
    elif a.cmd == "label-sheet":
        make_label_sheet(a.n, a.rejected, a.seed)
    elif a.cmd == "sample":
        sample(a.n)
    else:
        extra = {k: v for k, v in {"queries": a.queries, "subs": a.subs, "posts_per_url": a.posts_per_url,
                                   "max_usd": a.max_usd, "listing": a.listing, "skip": a.skip}.items() if v}
        collect(a.source, a.limit, [x for x in a.products.split(",") if x], extra)


if __name__ == "__main__":
    main()
