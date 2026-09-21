"""Write a slim copy of the database for hosting the Explorer (demo/engine.db).

Keeps everything the Explorer shows. Post text is kept only for items that were extracted; raw scraper payloads,
author hashes and run logs are dropped.
"""
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_DB = ROOT / "demo" / "engine.db"


def export(src, dest=DEMO_DB):
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    a, b = sqlite3.connect(src), sqlite3.connect(dest)
    a.backup(b)
    a.close()
    b.execute("UPDATE raw_items SET text='', title=NULL WHERE item_id NOT IN (SELECT item_id FROM extractions)")
    b.execute("UPDATE raw_items SET raw_json='{}', author_hash=NULL")
    b.execute("DELETE FROM runs")
    b.commit()
    b.execute("VACUUM")
    kept = b.execute("SELECT COUNT(*) FROM raw_items WHERE text != ''").fetchone()[0]
    total = b.execute("SELECT COUNT(*) FROM raw_items").fetchone()[0]
    b.close()
    print(f"wrote {dest} ({dest.stat().st_size / 1e6:.1f} MB): {total} items, text kept for {kept}")
