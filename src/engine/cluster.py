"""Phase 5: group retrieval failures into named problems and compare them (architecture sections 3.8 and 3.9)."""
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from engine import llm, store

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "engine.db"
NS = "not_a_search_problem"
# The 10 retrieval failure modes are too thin to analyse one by one (several have under 10 items), so they are grouped first.
GROUPS = {"regression": "regression", "identity_failure": "identity", "missing_wrong_metadata": "metadata",
          "vocabulary_mismatch": "search_quality", "not_indexed": "search_quality", "ranking_failure": "search_quality",
          "cue_mismatch": "search_quality", "scale_or_speed": "scale_and_content", "content_type_gap": "scale_and_content",
          "unspecified": "unspecified"}
SEVERITY_WEIGHT = {"inconvenience": 1, "unclear": 1, "time_loss": 2, "emotional_loss": 3, "data_loss": 3}
WEIGHTS = {"frequency": 0.35, "spread": 0.15, "severity": 0.20, "underserved": 0.20, "recency": 0.10}
PRODUCTS = [("google_photos", r"google"), ("apple_photos", r"apple|iphone|ios|icloud"), ("amazon_photos", r"amazon"),
            ("onedrive", r"onedrive|microsoft"), ("dropbox", r"dropbox"), ("ente", r"\bente\b"), ("immich", r"immich"),
            ("samsung_gallery", r"samsung")]


def norm_product(mentioned, fallback):
    for text in (mentioned, fallback):
        for key, pattern in PRODUCTS:
            if text and re.search(pattern, str(text).lower()):
                return key
    return "unknown"


def load(db):
    rows = db.execute(
        "SELECT e.item_id, e.json, e.failure_mode, e.severity, e.outcome, e.photo_type, e.product_mentioned, e.confidence, "
        "r.source, r.title, r.text, r.created_at, r.thread_id, r.product FROM extractions e JOIN raw_items r USING(item_id) "
        "WHERE e.failure_mode != ?", (NS,)).fetchall()
    out = []
    for r in rows:
        j = json.loads(r["json"])
        out.append({**dict(r), "rec": j, "group": GROUPS[r["failure_mode"]], "thread": r["thread_id"] or r["item_id"],
                    "product_norm": norm_product(r["product_mentioned"], r["product"]),
                    "signature": f"{r['title'] or ''}. {j['target_description']}"})
    return out


def embed(texts):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2").encode(texts, normalize_embeddings=True, show_progress_bar=False)


def subcluster(vectors, per_cluster=18, min_size=5):
    """Ward agglomerative clustering, about one cluster per `per_cluster` items; tiny clusters merge into the nearest one."""
    n = len(vectors)
    if n < 2 * per_cluster - 6:
        return np.zeros(n, dtype=int)
    from sklearn.cluster import AgglomerativeClustering
    labels = AgglomerativeClustering(n_clusters=max(2, round(n / per_cluster)), linkage="ward").fit_predict(vectors)  # unit vectors, so euclidean ranks like cosine; average linkage chained into one giant cluster
    while True:
        counts = Counter(labels)
        small = [c for c, k in counts.items() if k < min_size]
        if not small or len(counts) == 1:
            return labels
        c = small[0]
        centroids = {k: vectors[labels == k].mean(0) for k in counts}
        nearest = max((k for k in counts if k != c), key=lambda k: float(centroids[c] @ centroids[k]))
        labels[labels == c] = nearest


def build(model, name_clusters=True):
    db = store.connect(DB_PATH)
    items = load(db)
    vectors = embed([i["signature"] for i in items])
    by_group = defaultdict(list)
    for idx, it in enumerate(items):
        by_group[it["group"]].append(idx)
    clusters = []
    for group, idxs in sorted(by_group.items()):
        labels = subcluster(vectors[idxs])
        for lab in sorted(set(labels)):
            members = [idxs[k] for k in range(len(idxs)) if labels[k] == lab]
            clusters.append({"group": group, "members": members})
    for cid, c in enumerate(clusters, start=1):
        c["id"] = cid
        c["name"], c["definition"] = f"{c['group']} #{cid}", ""
    if name_clusters:
        _name(clusters, items, model)
    run_id = store.log_run(db, "cluster", None, {"model": model, "method": "group by failure mode, then Ward on MiniLM", **store.versions()},
                           {"clusters": len(clusters), "items": len(items)}, [], store.now())
    db.execute("DELETE FROM cluster_items")
    db.execute("DELETE FROM clusters")
    for c in clusters:
        db.execute("INSERT INTO clusters(cluster_id, name, definition, taxonomy_version, run_id, grp) VALUES(?,?,?,?,?,?)",
                   (c["id"], c["name"], c["definition"], "v1", run_id, c["group"]))
        db.executemany("INSERT INTO cluster_items VALUES(?,?)", [(c["id"], items[m]["item_id"]) for m in c["members"]])
    db.commit()
    print(f"{len(clusters)} clusters over {len(items)} retrieval failures")
    for c in clusters:
        print(f"  #{c['id']:<3}{c['group']:<18}n={len(c['members']):<4}{c['name']}")


def _name(clusters, items, model):
    schema = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "cluster": {"type": "INTEGER"}, "name": {"type": "STRING"}, "definition": {"type": "STRING"}},
        "required": ["cluster", "name", "definition"]}}
    for group in sorted({c["group"] for c in clusters}):
        block = []
        for c in [c for c in clusters if c["group"] == group]:
            ex = "\n".join(f"  - {items[m]['rec']['target_description']} | \"{(items[m]['rec']['evidence_quotes'] or [''])[0][:100]}\""
                           for m in c["members"][:12])
            block.append(f"Cluster {c['id']} ({len(c['members'])} posts):\n{ex}")
        prompt = (f"These clusters group public posts about photo-app retrieval problems (all in the broad category '{group}'). "
                  "For each cluster give a plain-language name of at most 6 words and a one-sentence definition precise enough "
                  "for a reader to decide whether a new post belongs. Base them only on the examples and make the clusters in "
                  "this category distinguishable from each other.\n\n" + "\n\n".join(block))
        for a in llm.generate_json(model, prompt, schema):
            c = next((c for c in clusters if c["id"] == a["cluster"]), None)
            if c:
                c["name"], c["definition"] = a["name"], a["definition"]


def apply_audit(path=None):
    """Apply the merge, rename and residual actions from eval/cluster_audit.json to the clusters table."""
    db = store.connect(DB_PATH)
    spec = json.loads((path or ROOT / "eval" / "cluster_audit.json").read_text(encoding="utf8"))
    for a in spec["actions"]:
        if "merge" in a:
            for src in a["merge"]:
                db.execute("UPDATE cluster_items SET cluster_id=? WHERE cluster_id=?", (a["into"], src))
                db.execute("DELETE FROM clusters WHERE cluster_id=?", (src,))
            db.execute("UPDATE clusters SET name=?, definition=? WHERE cluster_id=?", (a["rename"], a["definition"], a["into"]))
        elif "rename_id" in a:
            db.execute("UPDATE clusters SET name=?, definition=? WHERE cluster_id=?", (a["name"], a["definition"], a["rename_id"]))
        elif "residual" in a:
            for cid in a["residual"]:
                db.execute("UPDATE clusters SET name='[residual] ' || name WHERE cluster_id=? AND name NOT LIKE '[residual]%'", (cid,))
    db.commit()
    print("audit applied:", [(r["cluster_id"], r["name"]) for r in db.execute("SELECT cluster_id, name FROM clusters ORDER BY cluster_id")])


def _norm01(values):
    lo, hi = min(values), max(values)
    return [0.0 if hi == lo else (v - lo) / (hi - lo) for v in values]


def metrics(db):
    items = {i["item_id"]: i for i in load(db)}
    cl = db.execute("SELECT cluster_id, name, definition, grp FROM clusters ORDER BY cluster_id").fetchall()
    members = defaultdict(list)
    for r in db.execute("SELECT cluster_id, item_id FROM cluster_items"):
        members[r["cluster_id"]].append(items[r["item_id"]])
    cues = defaultdict(list)
    for r in db.execute("SELECT item_id, cue_type, status FROM cue_mentions"):
        cues[r["item_id"]].append((r["cue_type"], r["status"]))
    recent = (date.today() - timedelta(days=183)).isoformat()
    out = []
    for c in cl:
        ms = members[c["cluster_id"]]
        n = len(ms)
        dated = [m for m in ms if m["created_at"]]
        cands = []
        for m in sorted(ms, key=lambda m: m["confidence"] != "high"):
            q = next((q for q in m["rec"]["evidence_quotes"] if len(q) > 25), None)
            if q:
                cands.append((m["item_id"], m["source"], q))
        chosen, seen = [], set()
        for c_ in cands:  # one quote per source first, then fill up to five
            if c_[1] not in seen:
                chosen.append(c_)
                seen.add(c_[1])
        chosen += [c_ for c_ in cands if c_ not in chosen][: max(0, 5 - len(chosen))]
        chosen = chosen[:5]
        out.append({
            "id": c["cluster_id"], "name": c["name"], "definition": c["definition"], "group": c["grp"], "items": n,
            "threads": len({m["thread"] for m in ms}), "sources": dict(Counter(m["source"] for m in ms)),
            "products": dict(Counter(m["product_norm"] for m in ms).most_common(4)),
            "failure_modes": dict(Counter(m["failure_mode"] for m in ms)),
            "photo_types": dict(Counter(m["photo_type"] for m in ms if m["photo_type"] != "unknown")),
            "severity": dict(Counter(m["severity"] for m in ms)),
            "not_found_rate": sum(m["outcome"] == "not_found" for m in ms) / n,
            "workaround_rate": sum(bool(m["rec"].get("workaround")) for m in ms) / n,
            "severity_score": sum(SEVERITY_WEIGHT[m["severity"]] for m in ms) / n,
            "recent_share": (sum(m["created_at"] >= recent for m in dated) / len(dated)) if dated else 0.0,
            "cues_remembered": dict(Counter(t for m in ms for t, s in cues.get(m["item_id"], []) if s == "remembered")),
            "cues_forgotten": dict(Counter(t for m in ms for t, s in cues.get(m["item_id"], []) if s == "forgotten")),
            "quotes": [{"item_id": i, "source": src, "quote": q} for i, src, q in chosen],
            "sources_with_quote": len({src for _, src, _ in chosen}),
        })
    ranked = [m for m in out if not m["name"].startswith("[residual]")]  # mixed clusters are shown but not ranked
    parts = {"frequency": _norm01([m["threads"] for m in ranked]), "spread": _norm01([len(m["sources"]) for m in ranked]),
             "severity": _norm01([m["severity_score"] for m in ranked]),
             "underserved": _norm01([m["not_found_rate"] * (1 - m["workaround_rate"]) for m in ranked]),
             "recency": _norm01([m["recent_share"] for m in ranked])}
    for k, m in enumerate(ranked):
        m["score_parts"] = {p: round(parts[p][k], 2) for p in parts}
        m["score"] = round(sum(WEIGHTS[p] * parts[p][k] for p in parts), 3)
    for m in out:
        m.setdefault("score", None)
    return sorted(out, key=lambda m: (m["score"] is None, -(m["score"] or 0)))


def remember_forget(db):
    """Counts of cue type x status, overall and by photo type, over retrieval failures and over every extracted item."""
    q = ("SELECT m.cue_type, m.status, e.photo_type, e.failure_mode FROM cue_mentions m JOIN extractions e USING(item_id)")
    rows = db.execute(q).fetchall()
    fail = [r for r in rows if r["failure_mode"] != NS]
    def table(rs):
        return {t: {s: sum(1 for r in rs if r["cue_type"] == t and r["status"] == s) for s in ("remembered", "forgotten", "unknown")}
                for t in sorted({r["cue_type"] for r in rs})}
    return {"all_extracted": table(rows), "retrieval_failures": table(fail),
            "by_photo_type": {p: table([r for r in fail if r["photo_type"] == p]) for p in sorted({r["photo_type"] for r in fail}) if p != "unknown"}}


SCHEMES = {"default weights": WEIGHTS,
           "equal weights": {k: 0.2 for k in WEIGHTS},
           "frequency only": {"frequency": 1.0, "spread": 0, "severity": 0, "underserved": 0, "recency": 0},
           "underserved and severity": {"frequency": 0, "spread": 0, "severity": 0.5, "underserved": 0.5, "recency": 0}}


def sensitivity(ms):
    """Rank the (non-residual) clusters under several weightings to show how much the order depends on the rule."""
    ranked = [m for m in ms if m["score"] is not None]
    out = {}
    for name, w in SCHEMES.items():
        sc = {m["id"]: sum(w[p] * m["score_parts"][p] for p in w) for m in ranked}
        out[name] = sorted(sc, key=lambda i: -sc[i])
    return out


def report():
    db = store.connect(DB_PATH)
    ms = metrics(db)
    print(f"{'#':<4}{'score':>6} {'name':<38}{'items':>6}{'thr':>5}{'src':>4}{'notfound':>9}{'workaround':>11}{'sev':>5}{'recent':>7}")
    for m in ms:
        sc = f"{m['score']:.2f}" if m["score"] is not None else "n/a"
        print(f"{m['id']:<4}{sc:>6} {m['name'][:37]:<38}{m['items']:>6}{m['threads']:>5}{len(m['sources']):>4}"
              f"{m['not_found_rate']:>9.0%}{m['workaround_rate']:>11.0%}{m['severity_score']:>5.1f}{m['recent_share']:>7.0%}")
    rf, sens = remember_forget(db), sensitivity(ms)
    total = sum(m["items"] for m in ms)
    valid = sum(m["items"] for m in ms if m["score"] is not None)
    out = ROOT / "eval" / "results"
    (out / "clusters.json").write_text(json.dumps({"weights": WEIGHTS, "clusters": ms, "remember_forget": rf, "sensitivity": sens},
                                                  indent=1), encoding="utf8")
    for name, order in sens.items():
        print(f"  {name:<26} top 3: {order[:3]}")
    print(f"\nitems in ranked clusters: {valid}/{total} ({valid / total:.0%}); every ranked cluster has 3+ quotes from 2+ sources:",
          all(len(m["quotes"]) >= 3 and m["sources_with_quote"] >= 2 for m in ms if m["score"] is not None))
    _write_markdown(out / "clusters.md", ms, rf, sens, total, valid)
    print(f"wrote {out / 'clusters.md'} and clusters.json")


def _write_markdown(path, ms, rf, sens, total, valid):
    L = ["# Phase 5 result: retrieval problem clusters", "",
         f"{total} retrieval failures (extractions whose failure mode is not `not_a_search_problem`) grouped into {sum(m['score'] is not None for m in ms)} "
         f"ranked clusters ({valid} items, {valid / total:.0%}) plus {sum(m['score'] is None for m in ms)} residual clusters that were too mixed to rank. "
         "Counts are mentions in a sample of public posts, not prevalence, and one thread can contribute many items (see the threads column).", "",
         "## Ranking rule", "",
         "Each cluster gets five measures scaled 0 to 1 across the ranked clusters, then a weighted sum: "
         + ", ".join(f"{k} {v:.0%}" for k, v in WEIGHTS.items()) + ". *Frequency* is distinct threads; *spread* is the number of sources; "
         "*severity* is the mean of inconvenience/unclear 1, time loss 2, emotional or data loss 3; *underserved* is the share of items where the person "
         "could not find the photo, times the share with no workaround; *recency* is the share of dated items from the last six months. "
         "The weights are a judgment, not a measurement.", "",
         "| # | Score | Cluster | Items | Threads | Sources | Not found | Workaround | Recent |", "|---|---|---|---|---|---|---|---|---|"]
    for m in ms:
        sc = f"{m['score']:.2f}" if m["score"] is not None else "n/a"
        L.append(f"| {m['id']} | {sc} | {m['name']} | {m['items']} | {m['threads']} | {len(m['sources'])} | {m['not_found_rate']:.0%} | "
                 f"{m['workaround_rate']:.0%} | {m['recent_share']:.0%} |")
    L += ["", "**How much the order depends on the rule** (top three cluster numbers under each weighting): "
          + "; ".join(f"{k}: {v[:3]}" for k, v in sens.items()) + ".", "", "## Clusters", ""]
    for m in ms:
        L += [f"### {m['id']}. {m['name']}", "", m["definition"], "",
              f"- Items {m['items']} in {m['threads']} threads; sources {m['sources']}; products {m['products']}",
              f"- Failure modes {m['failure_modes']}; severity {m['severity']}; photo types (where stated) {m['photo_types'] or 'none stated'}",
              f"- Memory cues remembered {m['cues_remembered'] or 'none'}; forgotten {m['cues_forgotten'] or 'none'}", "- Quotes:"]
        L += [f"  - \"{q['quote'][:220].strip()}\" ({q['source']}, `{q['item_id']}`)" for q in m["quotes"]] + [""]
    def rows(t):
        return ["| Cue type | Remembered | Forgotten | Unknown |", "|---|---|---|---|"] + [
            f"| {k} | {v['remembered']} | {v['forgotten']} | {v['unknown']} |" for k, v in t.items()]
    L += ["## What people remember and forget", "",
          "Over retrieval failures only. These counts are small and include example searches, not just memories of one specific photo.", ""] + rows(rf["retrieval_failures"])
    for p, t in rf["by_photo_type"].items():
        L += ["", f"Photo type `{p}`:", ""] + rows(t)
    L += ["", "## Limitations", "",
          "- Clusters were checked by a single model rater on 10 items each; six of fifteen first-pass clusters failed the 8-of-10 rule and were merged, renamed or set aside (`eval/cluster_audit.json`).",
          "- After the merges, a fresh 10-item re-check gave cluster 1 10/10, cluster 4 10/10, cluster 8 8/10 and cluster 5 7/10. Cluster 5 is a borderline fail: two of its ten items are off-topic Hacker News and Stack Exchange comments the extractor should have set aside. Treat its rank with caution.",
          "- Failure-mode groups came from the extractor, which agreed with my labels about 75% of the time on 100 items; 'unspecified' clusters may hide regressions the extractor did not call.",
          "- Threads, not items, are the fair unit for frequency; a single popular thread can inflate an item count.",
          "- Sources skew: Google Photos is about half of the items and most non-Google clusters rest on very few threads."]
    path.write_text("\n".join(L) + "\n", encoding="utf8")


def audit(per_cluster=10, seed=3):
    import random
    db = store.connect(DB_PATH)
    items = {i["item_id"]: i for i in load(db)}
    rnd = random.Random(seed)
    for c in db.execute("SELECT cluster_id, name, definition FROM clusters ORDER BY cluster_id"):
        ids = [r[0] for r in db.execute("SELECT item_id FROM cluster_items WHERE cluster_id=?", (c["cluster_id"],))]
        rnd.shuffle(ids)
        print(f"\n### #{c['cluster_id']} {c['name']} -- {c['definition']}")
        for k, i in enumerate(ids[:per_cluster]):
            it = items[i]
            print(f"  [{c['cluster_id']}.{k}] ({it['source']}, {it['failure_mode']}) {it['rec']['target_description'][:100]!r} | {it['text'][:110].replace(chr(10), ' ')!r}")


ASSIGN_MIN_SIM = 0.35  # a new failure joins the nearest cluster only if its cosine similarity to that cluster's centre is at least this


def _unit(v):
    return v / (np.linalg.norm(v) or 1.0)


def assign_new(db, embed_fn=embed, min_sim=ASSIGN_MIN_SIM):
    """Put failures that have no cluster into the nearest existing (non-residual) cluster. Returns counts."""
    items = load(db)
    assigned = {r["item_id"]: r["cluster_id"] for r in db.execute("SELECT item_id, cluster_id FROM cluster_items")}
    valid = {r["cluster_id"] for r in db.execute("SELECT cluster_id FROM clusters WHERE name NOT LIKE '[residual]%'")}
    todo = [i for i in items if i["item_id"] not in assigned]
    if not todo or not valid:
        return {"new": len(todo), "assigned": 0}
    vecs = embed_fn([i["signature"] for i in items])
    pos = {i["item_id"]: k for k, i in enumerate(items)}
    cents = {}
    for cid in valid:
        members = [pos[i] for i, c in assigned.items() if c == cid and i in pos]
        if members:
            cents[cid] = _unit(vecs[members].mean(0))
    n = 0
    for it in todo:
        sims = {cid: float(vecs[pos[it["item_id"]]] @ c) for cid, c in cents.items()}
        best = max(sims, key=sims.get)
        if sims[best] >= min_sim:
            db.execute("INSERT OR IGNORE INTO cluster_items VALUES(?,?)", (best, it["item_id"]))
            n += 1
    db.commit()
    return {"new": len(todo), "assigned": n}


def assign_check(db, embed_fn=embed):
    """Leave-one-out test of nearest-centre assignment: how often does an existing item land back in its own cluster?"""
    items = {i["item_id"]: i for i in load(db)}
    valid = {r["cluster_id"] for r in db.execute("SELECT cluster_id FROM clusters WHERE name NOT LIKE '[residual]%'")}
    rows = [(r["item_id"], r["cluster_id"]) for r in db.execute("SELECT item_id, cluster_id FROM cluster_items") if r["cluster_id"] in valid]
    X = embed_fn([items[i]["signature"] for i, _ in rows])
    y = np.array([c for _, c in rows])
    sums = {c: X[y == c].sum(0) for c in valid}
    counts = {c: int((y == c).sum()) for c in valid}
    result = []
    for k, x in enumerate(X):
        sims = {}
        for c in valid:
            s, n = sums[c] - (x if y[k] == c else 0), counts[c] - (1 if y[k] == c else 0)
            if n > 0:
                sims[c] = float(x @ _unit(s / n))
        best = max(sims, key=sims.get)
        result.append((sims[best], best == y[k]))
    out = {"items": len(rows), "accuracy": sum(ok for _, ok in result) / len(result), "by_threshold": {}}
    for thr in (0.25, 0.35, 0.45, 0.55):
        kept = [ok for s, ok in result if s >= thr]
        out["by_threshold"][thr] = {"coverage": len(kept) / len(result), "accuracy": (sum(kept) / len(kept)) if kept else 0.0}
    return out
