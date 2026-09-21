"""Numbers behind the report: the funnel, and evidence for each hypothesis in docs/context.md section 10."""
import re
from collections import Counter

from engine import cluster, store

CONTROL = re.compile(r"classic|old search|back to|revert|turn(ed)? off|disable|toggle|option to|normal search", re.I)
ACCURACY = re.compile(r"inaccurate|wrong|irrelevant|worse|awful|useless|sh\*t|crapshoot|not as good|nowhere near|"
                      r"can'?t find|no longer (work|find|search)|gone|broken", re.I)

# Verdicts are my reading of the evidence below, written after computing it.
VERDICTS = {
    1: ("Tentatively supported", "Among the 34 failures about old-type or age-stated photos, missing or wrong metadata is the largest identified cause, but the group is small and partly circular (migrated photos are defined by metadata loss)."),
    2: ("Not supported", "Remembered cues are where (16) and when (12) more often than who (10) or event (3). The counts are tiny, mostly example searches, and there are no forgotten who or event cues to compare."),
    3: ("Inconclusive", "17 screenshot or functional-image failures, with the same not-found rate as everything else and few purpose cues. Too few to call it a distinct problem."),
    4: ("Not supported", "Fewer than one in five AI-search complaints ask for the old search back or a switch (4 of 23 in the cluster, 7 of 37 across every AI-related failure); most describe worse or wrong results (10 of 23)."),
    5: ("Inconclusive", "Migrated photos are 4% of failures, though a higher share are unresolved (67% not found, 8 of 12, against 53% overall). Too few to call disproportionate, and 'unrecoverable' cannot be judged from posts."),
    6: ("Not supported", "Reddit workaround rate (8%) is no higher than App Store (6%) or Google Community (7%); Hacker News is highest (15%) on 27 items. Workarounds are rare everywhere."),
    7: ("Strongly supported", "About two thirds of the extracted items, and 61% of items the classifier first called retrieval, were on closer reading not a failure to find photos."),
}


def _frac(a, b):
    return {"n": a, "of": b, "pct": round(100 * a / b) if b else 0}


def funnel(db):
    return [dict(r) for r in db.execute(
        """SELECT r.source, COUNT(*) items, SUM(f.prefilter_pass) passed, SUM(f.relevant IS NOT NULL) classified,
           SUM(f.relevant=1) relevant, SUM(e.item_id IS NOT NULL) extracted,
           SUM(e.item_id IS NOT NULL AND e.failure_mode != 'not_a_search_problem') failures
           FROM raw_items r JOIN filter_results f USING(item_id) LEFT JOIN extractions e USING(item_id)
           GROUP BY r.source ORDER BY failures DESC""")]


def hypotheses(db):
    items = cluster.load(db)
    n = len(items)
    out = {}
    old = [i for i in items if i["photo_type"] in ("early_digital", "scanned_print", "migrated") or i["rec"].get("photo_age")]
    out[1] = {"old_type_or_age_stated": len(old), "by_failure_mode": dict(Counter(i["failure_mode"] for i in old)),
              "metadata_share_old": _frac(sum(i["failure_mode"] == "missing_wrong_metadata" for i in old), len(old)),
              "metadata_share_all": _frac(sum(i["failure_mode"] == "missing_wrong_metadata" for i in items), n)}
    cues = {}
    for r in db.execute("SELECT m.cue_type, m.status, COUNT(*) c FROM cue_mentions m JOIN extractions e USING(item_id) "
                        "WHERE e.failure_mode != 'not_a_search_problem' GROUP BY 1,2"):
        cues.setdefault(r["cue_type"], {})[r["status"]] = r["c"]
    out[2] = {"cues": cues}
    sc = [i for i in items if i["photo_type"] == "screenshot_functional"]
    ids = [i["item_id"] for i in sc]
    sc_cues = (Counter(r[0] for r in db.execute(f"SELECT cue_type FROM cue_mentions WHERE item_id IN ({','.join('?' * len(ids))})", ids))
               if ids else {})
    out[3] = {"screenshot_failures": len(sc), "cue_types": dict(sc_cues),
              "not_found": _frac(sum(i["outcome"] == "not_found" for i in sc), len(sc)),
              "not_found_all": _frac(sum(i["outcome"] == "not_found" for i in items), n)}
    c4 = {r[0] for r in db.execute("SELECT item_id FROM cluster_items c JOIN clusters k USING(cluster_id) WHERE k.name LIKE 'AI (Gemini)%'")}
    t4 = [i for i in items if i["item_id"] in c4]
    ai = [i for i in items if re.search(r"gemini|ask photos|\bai\b", i["text"] + " " + (i["title"] or ""), re.I)]
    out[4] = {"cluster_items": len(t4), "control_words": sum(bool(CONTROL.search(i["text"])) for i in t4),
              "accuracy_words": sum(bool(ACCURACY.search(i["text"])) for i in t4),
              "all_ai_mentions": len(ai), "ai_control_words": sum(bool(CONTROL.search(i["text"])) for i in ai)}
    mg = [i for i in items if i["photo_type"] == "migrated"]
    out[5] = {"migrated": len(mg), "share_of_failures": _frac(len(mg), n),
              "not_found": _frac(sum(i["outcome"] == "not_found" for i in mg), len(mg)),
              "not_found_all": _frac(sum(i["outcome"] == "not_found" for i in items), n)}
    by = {}
    for i in items:
        d = by.setdefault(i["source"], [0, 0])
        d[0] += 1
        d[1] += bool(i["rec"].get("workaround"))
    out[6] = {"workaround_by_source": {s: _frac(w, t) for s, (t, w) in by.items()}}
    tot = db.execute("SELECT COUNT(*) FROM extractions").fetchone()[0]
    ns = db.execute("SELECT COUNT(*) FROM extractions WHERE failure_mode='not_a_search_problem'").fetchone()[0]
    sr = db.execute("SELECT COUNT(*) FROM extractions e JOIN filter_results f USING(item_id) WHERE f.problem_family='search_or_retrieval'").fetchone()[0]
    srns = db.execute("SELECT COUNT(*) FROM extractions e JOIN filter_results f USING(item_id) WHERE f.problem_family='search_or_retrieval' "
                      "AND e.failure_mode='not_a_search_problem'").fetchone()[0]
    out[7] = {"extracted_not_search": _frac(ns, tot), "classifier_search_but_not": _frac(srns, sr),
              "classifier_families": dict(db.execute("SELECT problem_family, COUNT(*) FROM filter_results WHERE relevant IS NOT NULL "
                                                     "AND language='english' GROUP BY 1 ORDER BY 2 DESC").fetchall())}
    return out


def search_behaviour(db):
    rows = db.execute("SELECT json_extract(e.json,'$.search_pattern') p, COUNT(*) n FROM extractions e "
                      "WHERE e.failure_mode != 'not_a_search_problem' GROUP BY 1 ORDER BY 2 DESC").fetchall()
    return {r["p"]: r["n"] for r in rows}
