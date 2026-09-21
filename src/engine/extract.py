"""Structured extraction of retrieval evidence with a verbatim-quote validator (architecture sections 3.5 to 3.7)."""
import json
import random
import re
from pathlib import Path

import yaml

from engine import llm, store

ROOT = Path(__file__).resolve().parents[2]
TEXT_LIMIT, STARTER_LIMIT = 2500, 600
ENUMS = ["photo_type", "cue_type", "cue_status", "search_pattern", "failure_mode", "severity", "outcome", "confidence"]


def taxonomy():
    return yaml.safe_load((ROOT / "config" / "taxonomy.yaml").read_text(encoding="utf8"))


def _enum(tax, name):
    return {"type": "STRING", "enum": list(tax[name])}


def schema(tax):
    cue = {"type": "OBJECT", "properties": {
        "type": _enum(tax, "cue_type"), "value": {"type": "STRING"}, "status": _enum(tax, "cue_status"),
        "quote": {"type": "STRING"}}, "required": ["type", "value", "status", "quote"]}
    rec = {"type": "OBJECT", "properties": {
        "i": {"type": "INTEGER"}, "photo_type": _enum(tax, "photo_type"),
        "photo_age": {"type": "STRING", "nullable": True}, "target_description": {"type": "STRING"},
        "cues": {"type": "ARRAY", "items": cue},
        "queries_tried": {"type": "ARRAY", "items": {"type": "STRING"}},
        "search_pattern": _enum(tax, "search_pattern"), "workaround": {"type": "STRING", "nullable": True},
        "failure_mode": _enum(tax, "failure_mode"), "severity": _enum(tax, "severity"), "outcome": _enum(tax, "outcome"),
        "product_mentioned": {"type": "STRING", "nullable": True}, "confidence": _enum(tax, "confidence"),
        "evidence_quotes": {"type": "ARRAY", "items": {"type": "STRING"}}},
        "required": ["i", "photo_type", "target_description", "cues", "queries_tried", "search_pattern", "failure_mode",
                     "severity", "outcome", "confidence", "evidence_quotes"]}
    return {"type": "ARRAY", "items": rec}


def build_prompt(items, tax, error_note=None):
    blocks = []
    for i, it in enumerate(items):
        text = it["text"] if len(it["text"]) <= TEXT_LIMIT else it["text"][:TEXT_LIMIT] + " [...]"
        head = f"### {i} | source: {it['source']} | product: {it.get('product') or '-'} | title: {it.get('title') or '-'}"
        starter = it.get("starter")
        ctx = f"\n[thread starter, context only, never quote: {starter[:STARTER_LIMIT]!r}]" if starter else ""
        blocks.append(f"{head}{ctx}\n{text}")
    defs = {n: "\n".join(f"- {k}: {v}" for k, v in tax[n].items()) for n in ENUMS}
    prompt = (ROOT / "prompts" / "extraction.md").read_text(encoding="utf8")
    for n in ENUMS:
        prompt = prompt.replace("{" + n + "}", defs[n])
    prompt = prompt.replace("{items}", "\n\n".join(blocks))
    if error_note:
        prompt += f"\n\nYour previous answer for this item was rejected: {error_note}\nAnswer again; copy quotes exactly."
    return prompt


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip().casefold()


def validate(rec, text, tax):
    """Deterministic checks; returns a list of error strings (empty means valid)."""
    errs, body = [], norm(text)
    for field in ("photo_type", "search_pattern", "failure_mode", "severity", "outcome", "confidence"):
        if rec.get(field) not in tax[field]:
            errs.append(f"{field}={rec.get(field)!r} is not an allowed value")
    for c in rec.get("cues") or []:
        if c.get("type") not in tax["cue_type"] or c.get("status") not in tax["cue_status"]:
            errs.append(f"cue has an invalid type or status: {c}")
        if not c.get("quote") or norm(c["quote"]) not in body:
            errs.append(f"cue quote is not verbatim in the item text: {c.get('quote')!r}")
    for q in rec.get("evidence_quotes") or []:
        if not q or norm(q) not in body:
            errs.append(f"evidence quote is not verbatim in the item text: {q!r}")
    for q in rec.get("queries_tried") or []:
        if norm(q) not in body:
            errs.append(f"query is not verbatim in the item text: {q!r}")
    return errs


def _batch(items, model, tax, generate):
    answer = generate(model, build_prompt(items, tax), schema(tax), max_output_tokens=16384)
    return {a["i"]: a for a in answer if isinstance(a, dict) and a.get("i") in range(len(items))}


def extract(items, model, batch=5, generate=llm.generate_json, progress=None, on_batch=None):
    """items: dicts with source, product, title, text, starter (optional). Returns (records, review) where records[i] is a
    valid record or None, and review lists (index, reason) for items that never validated."""
    tax = taxonomy()
    records, review = [None] * len(items), []
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        got = _batch(chunk, model, tax, generate)
        for i, it in enumerate(chunk):
            rec = got.get(i)
            errs = validate(rec, it["text"], tax) if rec else ["no answer for this item"]
            if errs:  # one retry, item alone, with the error message
                again = generate(model, build_prompt([it], tax, "; ".join(errs)[:600]), schema(tax), max_output_tokens=16384)
                rec = next((a for a in again if isinstance(a, dict)), None)
                errs = validate(rec, it["text"], tax) if rec else ["no answer for this item"]
            if errs:
                review.append((start + i, "; ".join(errs)[:500]))
            else:
                records[start + i] = rec
        if on_batch:  # lets the caller save finished work before a quota error can lose it
            on_batch(start, records[start:start + len(chunk)], [(i, w) for i, w in review if i >= start])
        if progress:
            progress(min(start + batch, len(items)), len(items))
    return records, review


def with_starters(db, rows):
    """Attach the thread's first post (context only) to replies and comments."""
    out = []
    for r in rows:
        d = dict(r)
        starter = None
        if d.get("thread_id") and d["thread_id"] != d["item_id"]:
            s = db.execute("SELECT text FROM raw_items WHERE item_id=?", (d["thread_id"],)).fetchone()
            starter = s["text"] if s else None
        out.append({**d, "starter": starter})
    return out


def pilot_pool(db, seed=11):
    """All relevant English items plus a fixed sample of other families, to test that non-search items are recognised."""
    rnd = random.Random(seed)
    rel = [r[0] for r in db.execute("SELECT item_id FROM filter_results WHERE relevant=1 AND language='english' ORDER BY item_id")]
    extra = []
    for fam, n in (("deletion_or_corruption", 40), ("backup_or_sync", 20), ("other", 10)):
        ids = [r[0] for r in db.execute("SELECT item_id FROM filter_results WHERE relevant=0 AND language='english' AND "
                                        "problem_family=? ORDER BY item_id", (fam,))]
        rnd.shuffle(ids)
        extra += ids[:n]
    return rel + extra


def new_pool(db):
    """Items the classifier called about retrieval (English) that have no extraction yet."""
    return [r[0] for r in db.execute("SELECT f.item_id FROM filter_results f LEFT JOIN extractions e USING(item_id) "
                                     "WHERE f.relevant=1 AND f.language='english' AND e.item_id IS NULL ORDER BY f.item_id")]


def save(db, item_id, rec, model, run_id, taxonomy_version):
    db.execute("DELETE FROM cue_mentions WHERE item_id=?", (item_id,))
    db.execute("INSERT OR REPLACE INTO extractions(item_id, json, failure_mode, severity, outcome, photo_type, product_mentioned, "
               "confidence, taxonomy_version, model, run_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
               (item_id, json.dumps(rec), rec["failure_mode"], rec["severity"], rec["outcome"], rec["photo_type"],
                rec.get("product_mentioned"), rec["confidence"], taxonomy_version, model, run_id))
    db.executemany("INSERT INTO cue_mentions(item_id, cue_type, cue_value, status, quote) VALUES(?,?,?,?,?)",
                   [(item_id, c["type"], c["value"], c["status"], c["quote"]) for c in rec.get("cues") or []])
