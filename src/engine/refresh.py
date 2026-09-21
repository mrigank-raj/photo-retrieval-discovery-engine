"""One-command refresh: collect only what is new, filter, classify, extract, and place new failures in the existing clusters.

Adding items is safe to repeat: every stage skips work it has already done, and inserts drop duplicates.
"""
from datetime import date, timedelta

from dotenv import load_dotenv

from engine import store

OVERLAP_DAYS = 3  # re-read a few days before the newest stored item so late-arriving posts are not missed; duplicates are dropped
PLAN = {  # per source: target items for a refresh run, plus source-specific options
    "appstore": {"limit": 300}, "play": {"limit": 300}, "youtube": {"limit": 300}, "google_community": {"limit": 120},
    "stackexchange": {"limit": 50}, "hackernews": {"limit": 50},
    "reddit": {"limit": 0,  # opt-in (--reddit): it is the only source that spends Apify credit
                "subs": 10, "posts_per_url": 15, "max_usd": 0.3},
}


def since_for(db, source, overlap_days=OVERLAP_DAYS):
    """ISO date to collect from: the newest stored item minus a few days, or None if the source has no items yet."""
    newest = db.execute("SELECT MAX(created_at) FROM raw_items WHERE source=?", (source,)).fetchone()[0]
    return (date.fromisoformat(newest[:10]) - timedelta(days=overlap_days)).isoformat() if newest else None


def snapshot(db):
    q = lambda sql: db.execute(sql).fetchone()[0]  # noqa: E731
    return {"raw_items": q("SELECT COUNT(*) FROM raw_items"),
            "classified": q("SELECT COUNT(*) FROM filter_results WHERE relevant IS NOT NULL"),
            "relevant": q("SELECT COUNT(*) FROM filter_results WHERE relevant=1"),
            "extracted": q("SELECT COUNT(*) FROM extractions"),
            "failures": q("SELECT COUNT(*) FROM extractions WHERE failure_mode != 'not_a_search_problem'"),
            "clustered": q("SELECT COUNT(*) FROM cluster_items")}


def known_videos(db):
    return {r[0].split(":", 1)[1]: r[1] for r in db.execute(
        "SELECT DISTINCT thread_id, title FROM raw_items WHERE source='youtube' AND thread_id LIKE 'youtube:%'")}


def run(sources=None, skip_collect=False, skip_extract=False, with_reddit=False):
    from engine import cli, cluster, pilot
    load_dotenv(cli.ROOT / ".env")
    cfg, models = cli.load_yaml("sources.yaml"), cli.load_yaml("llm.yaml")["providers"]["gemini"]["models"]
    cli.init_db()
    db = store.connect(cli.DB_PATH)
    before, started, errors = snapshot(db), store.now(), []
    chosen = [s for s in (sources or [k for k in PLAN if k != "reddit" or with_reddit]) if cfg["sources"].get(s, {}).get("enabled")]
    if not skip_collect:
        for s in chosen:
            since = since_for(db, s)
            extra = {k: v for k, v in PLAN[s].items() if k != "limit"}
            if since:
                extra["since"] = since
                if s == "youtube":
                    extra["known_videos"] = known_videos(db)
            print(f"\n== collect {s}" + (f" since {since}" if since else " (no data yet: first collection)"))
            try:
                cli.collect(s, PLAN[s]["limit"] or 300, [], extra)
            except (Exception, SystemExit) as e:  # one failing source must not stop the refresh
                errors.append(f"{s}: {type(e).__name__}: {e}")
                print(f"  skipped {s}: {e}")
    print("\n== keyword filter")
    cli.run_prefilter()
    print("\n== relevance classifier")
    stopped = cli.run_relevance(models["relevance"], 0)
    if not stopped and not skip_extract:
        print("\n== extraction")
        out = cli.ROOT / "data" / "refresh" / f"extract_{started.replace(':', '').replace('-', '')}.json"
        stopped = pilot.run("new", str(out), models["extraction"], True, 8)
    print("\n== place new failures in clusters")
    placed = cluster.assign_new(db)
    after = snapshot(db)
    diff = {k: after[k] - before[k] for k in after}
    store.log_run(db, "refresh", None, {"sources": chosen, "skip_collect": skip_collect, **store.versions()},
                  {**diff, **placed}, errors + ([f"stopped: {stopped}"] if stopped else []), started)
    print("\nRefresh summary (new since the start of this run):")
    for k, v in diff.items():
        print(f"  {k:<12} +{v}")
    print(f"  new failures placed in an existing cluster: {placed['assigned']} of {placed['new']}")
    if placed["new"] - placed["assigned"] > 0:
        print("  Some new failures fit no cluster; if there are many, re-run `cluster-build` and `cluster-apply-audit`.")
    if stopped:
        print(f"\nSTOPPED EARLY: a free daily quota ran out ({stopped}). Run `refresh` again later; it continues where it left off.")
    for e in errors:
        print("  source error:", e)
    return diff
