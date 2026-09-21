"""Insights: turn the tables into findings a reader can act on.

Code finds notable contrasts in the data (detectors) and sets the confidence itself from sample size and source spread. An LLM
writes each one up as a headline, a "so what" and a caveat. A validator rejects write-ups that use a number the data does not
contain, or that call a minority "most", "often" or "significant". If the LLM fails, a plain fallback headline is used.
"""
import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from engine import cluster, llm, store

ROOT = Path(__file__).resolve().parents[2]
STORE_SOURCES = {"appstore", "play"}
FORUM_SOURCES = {"google_community", "reddit", "stackexchange", "hackernews"}
CHANGE = re.compile(r"used to|no longer|stopped (working|showing|appearing|finding)|since (the |last |this )?(latest |recent )?"
                    r"(update|upgrade|version)|after (the |an |a )?(latest |recent )?(update|upgrade)|took away|removed|"
                    r"(new|latest) (update|version|layout|format|design)|redesign|not (working )?like (it|before)|classic", re.I)
PEOPLE_WORKS = re.compile(r"(other than|except( for)?|only)[^.]{0,40}(people|faces?)|people (search )?(still )?works?", re.I)
STOP = set("a an the of in on at to for and or with my me i is it".split())
# What the items the first-pass classifier got wrong were actually about (first match wins).
TOPICS = [("recovering deleted photos", r"delet|recover|restor|trash|\bbin\b|permanent"),
          ("praise or no problem", r"great|love|thank|amazing|excellent|works well|best app|praise|helper|welcome to"),
          ("sync, backup or upload", r"backup|back up|sync|upload"),
          ("account, storage or billing", r"account|password|log ?in|storage|subscription|plan|pay|refund|price"),
          ("app bug, layout or update", r"crash|bug|layout|\bui\b|update|redesign|slow|lag|freez|error|button|feature")]
OVERCLAIM = re.compile(r"\b(most|majority|often|frequently|significant|dominat\w*|heavily|vast|almost all|widespread)\b", re.I)


def _pct(a, b):
    return round(100 * a / b) if b else 0


def _quotes(items, url, pick, n=3, min_len=28):
    """Up to n verbatim evidence quotes (already validated against the post text), one per source where possible."""
    out, seen = [], set()
    pool = [(i, q) for i in items for q in i["rec"]["evidence_quotes"] if len(q) >= min_len and pick(i)]
    for i, q in sorted(pool, key=lambda p: p[0]["confidence"] != "high"):
        if i["source"] not in seen and len(out) < n:
            out.append({"item_id": i["item_id"], "source": i["source"], "quote": q, "url": url[i["item_id"]]})
            seen.add(i["source"])
    return out


ANGLES = {
    "triage": "Counting search complaints alone overstates how broken search is. Say what the other complaints really were.",
    "unmet": "Name the problems with a high not-found rate and no workaround at all, and contrast them with the ones where some workaround exists.",
    "change": "How much of the problem is change (updates, AI search) versus things that never worked, and which clusters are change-driven.",
    "detail": "Store reviews versus forums: who supplies the diagnostic detail (cues, typed queries), and what that means for where to listen.",
    "products": "How the Apple Photos and Google Photos failure profiles differ.",
    "recency": "Which problems are new and which are long-standing.",
    "search_by": "What people search by when they say, and what it reveals about nouns versus dates.",
    "pain": "Where the high-stakes language (data loss, emotional loss) appears.",
    "partial": "Partial failures: what still works when search breaks.",
    "blind": "The biggest blind spots: what this data cannot tell us.",
}
WEAK_IDS = {"pain", "partial", "blind"}  # shown separately from the key insights


def _cand(id_, facts, fallback, quotes, n, sources, main_pct=None, heuristic=False, llm=True, so_what="", caveat=""):
    """llm=False candidates (small samples and blind spots) get plain code-written text, not LLM prose."""
    return {"id": id_, "angle": ANGLES[id_], "facts": facts, "fallback": fallback, "quotes": quotes, "n": n, "sources": sources,
            "main_pct": main_pct, "heuristic": heuristic, "llm": llm, "so_what": so_what, "caveat": caveat}


def confidence(c):
    """Set by code, not by the LLM: high needs 50+ items across 4+ sources; a keyword heuristic is capped at medium."""
    level = "high" if c["n"] >= 50 and c["sources"] >= 4 else "medium" if c["n"] >= 20 and c["sources"] >= 2 else "low"
    return "medium" if c["heuristic"] and level == "high" else level


def candidates(db):
    items = cluster.load(db)
    n = len(items)
    url = {r["item_id"]: r["url"] for r in db.execute("SELECT item_id, url FROM raw_items")}
    ms = [m for m in cluster.metrics(db) if m["score"] is not None]
    by_cluster = {r["item_id"]: r["name"] for r in db.execute("SELECT ci.item_id, c.name FROM cluster_items ci JOIN clusters c USING(cluster_id)")}
    nsrc = lambda group: len({i["source"] for i in group})  # noqa: E731
    out = []

    # 1. triage: what the "can't find" complaints that are not search problems actually are
    rows = db.execute("SELECT e.item_id, e.json, r.source, r.text FROM extractions e JOIN raw_items r USING(item_id) JOIN filter_results f USING(item_id) "
                      "WHERE f.problem_family='search_or_retrieval'").fetchall()
    sr = len(rows)
    ns = [{"item_id": r["item_id"], "source": r["source"], "rec": json.loads(r["json"]), "text": r["text"]} for r in rows
          if json.loads(r["json"])["failure_mode"] == "not_a_search_problem"]
    for i in ns:
        i["confidence"] = i["rec"]["confidence"]
        blob = (i["rec"]["target_description"] + " " + i["text"]).lower()
        i["topic"] = next((name for name, pat in TOPICS if re.search(pat, blob)), "something else or unclear")
    topics = Counter(i["topic"] for i in ns)
    out.append(_cand("triage", {"first_pass_called_retrieval": sr, "on_closer_reading_not_a_search_problem": len(ns), "share_pct": _pct(len(ns), sr),
                                "what_those_posts_were_about_pct_keyword_guess": {k: _pct(v, len(ns)) for k, v in topics.most_common()}},
                     f"{_pct(len(ns), sr)}% of complaints that first looked like search problems were not about finding photos.",
                     _quotes(ns, url, lambda i: i["topic"] == "recovering deleted photos", n=1) + _quotes(ns, url, lambda i: i["topic"] == "app bug, layout or update", n=1)
                     + _quotes(ns, url, lambda i: i["topic"] == "sync, backup or upload", n=1), sr, nsrc(ns), _pct(len(ns), sr)))

    # 2. which problems have no way forward
    unmet = [m for m in ms if m["not_found_rate"] >= 0.7 and m["workaround_rate"] <= 0.05]
    coped = sorted(ms, key=lambda m: -m["workaround_rate"])[:2]
    names = {m["name"] for m in unmet}
    grp = [i for i in items if by_cluster.get(i["item_id"]) in names]
    out.append(_cand("unmet", {"clusters_not_found_70_plus_and_workaround_under_5": {m["name"]: {"items": m["items"], "not_found_pct": round(100 * m["not_found_rate"]),
                                                                                                 "workaround_pct": round(100 * m["workaround_rate"])} for m in unmet},
                               "clusters_with_most_workarounds_pct": {m["name"]: round(100 * m["workaround_rate"]) for m in coped},
                               "overall_not_found_pct": _pct(sum(i["outcome"] == "not_found" for i in items), n),
                               "overall_with_workaround_pct": _pct(sum(bool(i["rec"].get("workaround")) for i in items), n)},
                     "Several problems have a high not-found rate and almost no workaround.",
                     _quotes(grp, url, lambda i: i["outcome"] == "not_found"), len(grp), nsrc(grp)))

    # 3. how much of it is change (keyword heuristic)
    change = [i for i in items if CHANGE.search(i["text"])]
    per = {m["name"]: _pct(sum(bool(CHANGE.search(i["text"])) for i in items if by_cluster.get(i["item_id"]) == m["name"]),
                           sum(1 for i in items if by_cluster.get(i["item_id"]) == m["name"])) for m in ms}
    out.append(_cand("change", {"failures": n, "wording_signals_something_changed": len(change), "share_pct": _pct(len(change), n),
                                "share_of_each_cluster_that_uses_change_wording_pct": per},
                     f"{_pct(len(change), n)}% of failures describe something that used to work or was changed.",
                     _quotes(change, url, lambda i: True), len(change), nsrc(change), _pct(len(change), n), heuristic=True))

    # 4. who can say why: store reviews vs forums
    def profile(srcs):
        g = [i for i in items if i["source"] in srcs]
        return g, {"failures": len(g), "cause_not_given_pct": _pct(sum(i["failure_mode"] == "unspecified" for i in g), len(g)),
                   "state_a_cue_pct": _pct(sum(bool(i["rec"]["cues"]) for i in g), len(g)),
                   "quote_a_query_pct": _pct(sum(bool(i["rec"]["queries_tried"]) for i in g), len(g)),
                   "median_words": sorted(len(i["text"].split()) for i in g)[len(g) // 2] if g else 0}
    (gs, st), (gf, fo) = profile(STORE_SOURCES), profile(FORUM_SOURCES)
    out.append(_cand("detail", {"store_reviews": st, "forums_and_reddit": fo}, "Store reviews say something is wrong; forums say what.",
                     _quotes(gs, url, lambda i: i["failure_mode"] == "unspecified", n=2) + _quotes(gf, url, lambda i: bool(i["rec"]["queries_tried"]), n=1),
                     len(gs) + len(gf), nsrc(gs + gf)))

    # 5. Apple vs Google
    def mix(prod):
        g = [i for i in items if i["product_norm"] == prod and by_cluster.get(i["item_id"]) and not by_cluster[i["item_id"]].startswith("[residual]")]
        c = Counter(by_cluster[i["item_id"]] for i in g)
        return g, {k: _pct(v, len(g)) for k, v in c.items()}
    (gg, mg), (ga, ma) = mix("google_photos"), mix("apple_photos")
    diffs = sorted(((ma.get(k, 0) - mg.get(k, 0), k) for k in set(ma) | set(mg)), key=lambda t: t[0])
    out.append(_cand("products", {"google_photos_failures": len(gg), "apple_photos_failures": len(ga),
                                  "apple_share_minus_google_share_pct_points": {diffs[-1][1]: diffs[-1][0], diffs[-2][1]: diffs[-2][0]},
                                  "google_share_minus_apple_share_pct_points": {diffs[0][1]: -diffs[0][0], diffs[1][1]: -diffs[1][0]},
                                  "google_top_clusters_pct": dict(sorted(mg.items(), key=lambda t: -t[1])[:4]),
                                  "apple_top_clusters_pct": dict(sorted(ma.items(), key=lambda t: -t[1])[:4])},
                     "Apple Photos and Google Photos posts describe different kinds of problems.",
                     _quotes(ga, url, lambda i: True, n=2), len(ga), nsrc(ga)))

    # 6. what is recent
    cut = (date.today() - timedelta(days=183)).isoformat()
    dated = [i for i in items if i["created_at"]]
    newest = sorted(ms, key=lambda m: -m["recent_share"])[:3]
    oldest = min(ms, key=lambda m: m["recent_share"])
    nn = {m["name"] for m in newest}
    gn = [i for i in items if by_cluster.get(i["item_id"]) in nn]
    out.append(_cand("recency", {"failures_from_last_6_months_pct": _pct(sum(i["created_at"] >= cut for i in dated), len(dated)),
                                 "newest_clusters_last_6_months_pct": {m["name"]: round(100 * m["recent_share"]) for m in newest},
                                 "least_recent_cluster_pct": {oldest["name"]: round(100 * oldest["recent_share"])}},
                     "Some problems are recent and others long-standing.", _quotes(gn, url, lambda i: True), len(gn), nsrc(gn)))

    # 7. what people search by
    words = Counter(w for i in items for w in {w for q in i["rec"]["queries_tried"] for w in re.findall(r"[a-z]{3,}", q.lower()) if w not in STOP})
    pats = Counter(i["rec"]["search_pattern"] for i in items)
    stated = sum(v for k, v in pats.items() if k != "not_stated")
    withq = [i for i in items if i["rec"]["queries_tried"]]
    out.append(_cand("search_by", {"failures_stating_how_they_searched": stated, "descriptive_keyword": pats["descriptive"], "year_or_date": pats["time_anchor"],
                                   "browse_after_broad_search": pats["broad_then_browse"],
                                   "most_common_words_in_typed_queries_posts_containing_each": dict(words.most_common(6))},
                     "People search by everyday nouns far more often than by dates.", _quotes(withq, url, lambda i: True), stated, nsrc(withq)))

    # 8. where the high-stakes language is (severity is model-assigned and defaults to 'inconvenience', so only loss language is used)
    sev_f = Counter(i["severity"] for i in items)
    sev_n = Counter(r[0] for r in db.execute("SELECT severity FROM extractions WHERE failure_mode='not_a_search_problem'"))
    high = db.execute("SELECT e.item_id, e.json, r.source FROM extractions e JOIN raw_items r USING(item_id) WHERE e.failure_mode='not_a_search_problem' "
                      "AND e.severity IN ('emotional_loss','data_loss')").fetchall()
    hi = [{"item_id": r["item_id"], "source": r["source"], "rec": json.loads(r["json"]), "confidence": "high"} for r in high]
    lf, ln, tn = sev_f["data_loss"] + sev_f["emotional_loss"], sev_n["data_loss"] + sev_n["emotional_loss"], sum(sev_n.values())
    out.append(_cand("pain", {"retrieval_failures": n, "with_data_or_emotional_loss_language": lf, "share_of_failures_pct": _pct(lf, n),
                              "not_search_items": tn, "not_search_with_data_or_emotional_loss_language": ln, "share_of_not_search_pct": _pct(ln, tn)},
                     f"Data or emotional loss is mentioned in {lf} of {n} failures ({_pct(lf, n)}%) against {ln} of {tn} non-search posts ({_pct(ln, tn)}%).",
                     _quotes(hi, url, lambda i: True), ln + lf, nsrc(hi), llm=False,
                     so_what="Explicit stakes language is rare in both groups but about three times more common in recovery, sync and other non-search posts than in search failures.",
                     caveat="Severity is assigned by the extraction model and most posts do not state stakes, so this counts only explicit loss language."))

    # 9. partial success
    pw = [i for i in items if PEOPLE_WORKS.search(i["text"])]
    if len(pw) >= 3:
        out.append(_cand("partial", {"posts_saying_people_search_still_works_or_is_the_only_part_that_does": len(pw)},
                         f"{len(pw)} posts say people or face search still works while other search does not.", _quotes(pw, url, lambda i: True), len(pw),
                         nsrc(pw), heuristic=True, llm=False, caveat="A small group matched by keywords; read the quotes before drawing conclusions."))

    # 10. blind spots
    forgotten = db.execute("SELECT COUNT(*) FROM cue_mentions WHERE status='forgotten'").fetchone()[0]
    out.append(_cand("blind", {"failures": n, "state_photo_type_pct": _pct(sum(i["photo_type"] != "unknown" for i in items), n),
                               "state_photo_age_pct": _pct(sum(bool(i["rec"].get("photo_age")) for i in items), n),
                               "state_how_they_searched_pct": _pct(stated, n), "forgotten_cues_in_whole_corpus": forgotten,
                               "not_google_photos_pct": _pct(sum(i["product_norm"] != "google_photos" for i in items), n)},
                     f"Only {_pct(sum(i['photo_type'] != 'unknown' for i in items), n)}% of failures state a photo type, "
                     f"{_pct(sum(bool(i['rec'].get('photo_age')) for i in items), n)}% a photo age and {_pct(stated, n)}% how they searched; "
                     f"the whole corpus holds {forgotten} forgotten cues.", [], n, len({i["source"] for i in items}), llm=False,
                     so_what="What people remember and forget, and anything specific to old photos, cannot be answered from public reviews and forums; it needs primary research such as a short survey or interviews.",
                     caveat="Absence from public posts does not mean people do not remember these things, only that they do not write them down."))
    return out


def _numbers(obj, acc=None):
    acc = acc if acc is not None else set()
    if isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, acc)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers(v, acc)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        acc.add(float(obj))
    return acc


def check_numbers(text, facts):
    """Return numbers in `text` (10 or more, or written with a %) that do not appear in the facts."""
    allowed = _numbers(facts)
    bad = []
    for m in re.finditer(r"\d[\d,]*\.?\d*\s*%?", text):
        raw = m.group(0)
        x = float(raw.replace(",", "").replace("%", "").strip() or 0)
        if (x >= 10 or "%" in raw) and not any(abs(x - a) < 0.51 for a in allowed):
            bad.append(raw.strip())
    return bad


def overclaims(text, main_pct):
    """Words like 'most' or 'often' are only allowed when the headline share is 50% or more (or unknown)."""
    return sorted({m.group(0).lower() for m in OVERCLAIM.finditer(text)}) if main_pct is not None and main_pct < 50 else []


SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "id": {"type": "STRING"}, "headline": {"type": "STRING"}, "so_what": {"type": "STRING"}, "caveat": {"type": "STRING"}},
    "required": ["id", "headline", "so_what", "caveat"]}}

PROMPT = """You are a product analyst writing findings from a study of what public reviews, forum posts and comments say about finding photos in photo apps.
Below are candidate findings, each with an `angle` (the point it should make), its measured facts and example quotes. Write about the angle, using the facts. For each one write:
- `headline`: ONE sentence that states the insight, meaning what the numbers imply that a reader would not already assume. Include the one or two numbers that make the point. A skeptic must be able to test it against the facts.
- `so_what`: one or two sentences on what this suggests about why people fail to find photos, or which area is worth investigating. State it as a plain sentence, never as a question, and do not use a question mark. Do NOT name a feature or give a recommendation.
- `caveat`: one sentence, the main reason to limit this finding.
Hard rules:
- Use ONLY numbers in that candidate's facts. Never invent a number, a percentage, a cause, a product mechanism or a source.
- Do not explain WHY something happens unless the facts or quotes say so. Never speculate about algorithms, architecture or causes.
- Counts are mentions in a sample of posts, not how many people have a problem. Say "posts", never "users" or "people generally".
- If a share is under 50%, state it plainly ("one in five posts"; do not use the word minority). Never write most, majority, often, frequently, significant, dominated, heavily or almost all for it.
- No repeated ideas across findings. Plain words, no jargon.
Weak: "Many posts describe other problems." Strong: "Six in ten complaints that read like search failures are about something else, so counting search complaints alone overstates how much search is broken."

Candidates (JSON):
{candidates}
"""


VERIFY_SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "id": {"type": "STRING"}, "ok": {"type": "BOOLEAN"}, "issue": {"type": "STRING"}}, "required": ["id", "ok", "issue"]}}
VERIFY_PROMPT = """You check written findings against the facts behind them. For each finding decide whether EVERY claim is supported by its facts.
Mark ok=false and state the issue in one sentence if the text: says two numbers match, are similar or are comparable when they differ; claims a cause
("driven by", "because", "due to", "leading to") that the facts do not state; generalises beyond the sample (for example says "users" or "people" where the facts
count posts); or describes a measure as something other than what its fact name says (for example treats a share of each group as a share of the whole).
Otherwise ok=true with an empty issue. Be strict.

Findings (JSON):
{items}
"""


def verify(written, cands, model, fallback_model, generate=llm.generate_json):
    """Second LLM pass whose only job is to reject write-ups that the facts do not support. Returns {id: issue}."""
    facts = {c["id"]: c["facts"] for c in cands}
    payload = [{"id": k, "facts": facts[k], "text": " ".join((v["headline"], v["so_what"], v["caveat"]))} for k, v in written.items()]
    if not payload:
        return {}
    prompt = VERIFY_PROMPT.replace("{items}", json.dumps(payload, indent=1))
    try:
        answer = generate(model, prompt, VERIFY_SCHEMA, max_output_tokens=8192)
    except llm.DailyQuotaExhausted:
        answer = generate(fallback_model, prompt, VERIFY_SCHEMA, max_output_tokens=8192)
    return {a["id"]: a["issue"] or "unsupported claim" for a in answer if isinstance(a, dict) and not a.get("ok", True)}


def narrate(cands, model, fallback_model, generate=llm.generate_json):
    cands = [c for c in cands if c["llm"]]
    payload = [{"id": c["id"], "angle": c["angle"], "facts": c["facts"], "example_quotes": [q["quote"] for q in c["quotes"]]} for c in cands]
    by_id, note = {}, ""
    for attempt in range(2):
        prompt = PROMPT.replace("{candidates}", json.dumps(payload, indent=1)) + (f"\nYour previous answer was rejected: {note}\nFix only those findings.\n" if note else "")
        try:
            answer = generate(model if attempt == 0 else fallback_model, prompt, SCHEMA, max_output_tokens=16384)
        except llm.DailyQuotaExhausted:
            answer = generate(fallback_model, prompt, SCHEMA, max_output_tokens=16384)
        by_id.update({a["id"]: a for a in answer if isinstance(a, dict)})
        problems = []
        for c in cands:
            a = by_id.get(c["id"])
            if a:
                text = " ".join((a["headline"], a["so_what"], a["caveat"]))
                bad, over = check_numbers(text, c["facts"]), overclaims(text, c["main_pct"])
                if "?" in a["so_what"]:
                    over = over + ["a question in so_what"]
                if bad or over:
                    problems.append(f"{c['id']}: " + (f"numbers not in its facts {bad}; " if bad else "") + (f"words not allowed for a {c['main_pct']}% share {over}" if over else ""))
                    by_id.pop(c["id"])
        for cid, issue in verify(dict(by_id), cands, model, fallback_model, generate).items():
            problems.append(f"{cid}: {issue}")
            by_id.pop(cid, None)
        if not problems:
            return by_id
        note = " | ".join(problems)[:600]
        payload = [p for p in payload if p["id"] not in by_id]
    return by_id


def build(model, fallback_model, use_llm=True):
    db = store.connect(cluster.DB_PATH)
    cands = candidates(db)
    written = narrate(cands, model, fallback_model) if use_llm else {}
    out = []
    for c in cands:
        w = written.get(c["id"])
        out.append({"id": c["id"], "headline": w["headline"] if w else c["fallback"], "so_what": w["so_what"] if w else c["so_what"],
                    "caveat": w["caveat"] if w else c["caveat"], "confidence": confidence(c), "n": c["n"], "sources": c["sources"],
                    "weak": c["id"] in WEAK_IDS or confidence(c) == "low", "written_by_llm": bool(w), "plain_text": not c["llm"], "facts": c["facts"], "quotes": c["quotes"]})
    res = ROOT / "eval" / "results"
    (res / "insights.json").write_text(json.dumps({"versions": store.versions(), "insights": out}, indent=1), encoding="utf8")
    (res / "insights.md").write_text(to_markdown(out), encoding="utf8")
    return out


def to_markdown(out):
    L = []
    for k, i in enumerate([x for x in out if x["id"] not in WEAK_IDS] + [x for x in out if x["id"] in WEAK_IDS], 1):
        L += [f"### {k}. {i['headline']}", ""]
        if i["so_what"]:
            L += [f"**Interpretation (a hypothesis to test, not a finding).** {i['so_what']}", ""]
        L += [f"**Confidence: {i['confidence']}** ({i['n']} items, {i['sources']} sources)." + (f" **Caveat.** {i['caveat']}" if i["caveat"] else "")]
        for q in i["quotes"]:
            L.append(f"- \"{q['quote']}\" ({q['source']}, [link]({q['url']}))")
        L.append("")
    return "\n".join(L)


START, END = "<!-- insights:start -->", "<!-- insights:end -->"


def write_report(out, path):
    """Replace the block between the insight markers in a markdown report with the current key insights."""
    key = [i for i in out if not i["weak"]]
    weak = [i for i in out if i["weak"]]
    block = "\n".join([START, "## Key insights", "",
                       "Written by the engine from measured contrasts in the data, then checked in code: every number must appear in the "
                       "facts behind it, confidence is set from sample size and source spread, and wording that overstates a minority is "
                       "rejected. Read the evidence links before relying on any of them.", "", to_markdown(key), "",
                       "### Weaker signals and blind spots", "", to_markdown(weak), END])
    text = Path(path).read_text(encoding="utf8")
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
    else:
        text = text.replace("## Read this first", block + "\n\n## Read this first", 1)
    Path(path).write_text(text, encoding="utf8")
