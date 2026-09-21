import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

MIN_LEN = 15
# Keys that identify a person. Removed from every stored payload; usernames are stored only as a salted hash.
PII_KEYS = {"userName", "userImage", "author", "authorDisplayName", "authorProfileImageUrl", "authorChannelUrl",
            "authorChannelId", "author_fullname", "authorId", "username", "user", "avatar", "profileUrl"}

PRODUCT_WORDS = [
    ("google_photos", r"google ?photos?|gphotos"),
    ("apple_photos", r"apple photos|iphone|icloud|\bios\b|ipad"),
    ("amazon_photos", r"amazon photos"),
    ("onedrive", r"onedrive"),
    ("dropbox", r"dropbox"),
    ("immich", r"immich"),
    ("ente", r"\bente\b"),
    ("samsung_gallery", r"samsung gallery|samsung photos"),
]


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def author_hash(name):
    if not name:
        return None
    return hashlib.sha256((os.environ["AUTHOR_HASH_SALT"] + str(name)).encode()).hexdigest()[:16]


def content_hash(text):
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().lower().encode()).hexdigest()[:32]


def scrub(obj):
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items() if k not in PII_KEYS}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


def looks_english(text):
    letters = [c for c in text if c.isalpha()]
    return not letters or sum(c.isascii() for c in letters) / len(letters) >= 0.85


def infer_product(*texts):
    blob = " ".join(t for t in texts if t).lower()
    for key, pattern in PRODUCT_WORDS:
        if re.search(pattern, blob):
            return key
    return None


def insert_items(db, items, since_date):
    """Insert normalized items; returns counts. `author` (raw) is hashed and never stored."""
    s = dict(seen=0, inserted=0, duplicate=0, too_short=0, non_english=0, out_of_window=0)
    for it in items:
        s["seen"] += 1
        text = (it.get("text") or "").strip()
        if len(text) < MIN_LEN:
            s["too_short"] += 1
        elif not looks_english(text):
            s["non_english"] += 1
        elif it.get("created_at") and it["created_at"][:10] < since_date:
            s["out_of_window"] += 1
        else:
            ch = content_hash(text)
            dup = db.execute(
                "SELECT 1 FROM raw_items WHERE item_id=? OR (content_hash=? AND source=? AND IFNULL(product,'')=IFNULL(?,''))",
                (it["item_id"], ch, it["source"], it.get("product"))).fetchone()
            if dup:
                s["duplicate"] += 1
                continue
            db.execute(
                """INSERT INTO raw_items(item_id, source, product, url, thread_id, parent_id, author_hash, created_at,
                   fetched_at, title, text, rating, helpful_count, app_or_os_version, locale, content_hash, raw_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (it["item_id"], it["source"], it.get("product"), it["url"], it.get("thread_id"), it.get("parent_id"),
                 author_hash(it.get("author")), it.get("created_at"), now(), it.get("title"), text, it.get("rating"),
                 it.get("helpful_count"), it.get("app_or_os_version"), it.get("locale"), ch,
                 json.dumps(scrub(it.get("raw") or {}), default=str)))
            s["inserted"] += 1
    db.commit()
    return s


def versions():
    """Taxonomy version and short hashes of the prompt and taxonomy files, recorded on every model-backed run."""
    import yaml
    root = Path(__file__).resolve().parents[2]

    def sha(rel):
        return hashlib.sha256((root / rel).read_bytes()).hexdigest()[:8]

    return {"taxonomy": yaml.safe_load((root / "config" / "taxonomy.yaml").read_text(encoding="utf8"))["version"],
            "taxonomy_sha": sha("config/taxonomy.yaml"), "prompt_relevance_sha": sha("prompts/relevance.md"),
            "prompt_extraction_sha": sha("prompts/extraction.md")}


def log_run(db, stage, source, params, counts, errors, started, cost=None):
    run_id = uuid.uuid4().hex[:8]
    db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?)",
               (run_id, stage, source, json.dumps(params, default=str), started, json.dumps(counts, default=str),
                cost, json.dumps(errors[:20], default=str)))
    db.commit()
    return run_id


def init_db(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf8"))
        have = {r[1] for r in db.execute("PRAGMA table_info(filter_results)")}
        for col in ("language", "confidence"):  # databases created before these columns existed
            if col not in have:
                db.execute(f"ALTER TABLE filter_results ADD COLUMN {col} TEXT")
        if "grp" not in {r[1] for r in db.execute("PRAGMA table_info(clusters)")}:
            db.execute("ALTER TABLE clusters ADD COLUMN grp TEXT")
    return path
