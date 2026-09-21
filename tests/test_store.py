import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import store  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHOR_HASH_SALT", "test-salt")
    path = store.init_db(tmp_path / "t.db")
    return store.connect(path)


def item(i="a", **kw):
    base = {"item_id": f"play:{i}", "source": "play", "product": "google_photos", "url": "https://x/1",
            "created_at": "2026-01-01T00:00:00", "text": "I cannot find my old photos anymore", "author": "Jane Doe",
            "raw": {"userName": "Jane Doe", "nested": {"author": {"name": "Jane"}, "keep": 1}}}
    return {**base, **kw}


def test_insert_dedupes_filters_and_never_stores_the_username(db):
    counts = store.insert_items(db, [
        item("a"),
        item("a"),                                                    # same id
        item("b"),                                                    # same text, same source and product
        item("c", text="short"),
        item("d", text="Не могу найти свои старые фотографии нигде"),
        item("e", text="A perfectly fine long enough review", created_at="2019-01-01T00:00:00"),
        item("f", text="A different review about search failing", product="apple_photos"),
    ], since_date="2023-09-20")
    assert counts == dict(seen=7, inserted=2, duplicate=2, too_short=1, non_english=1, out_of_window=1)
    row = db.execute("SELECT author_hash, raw_json FROM raw_items WHERE item_id='play:a'").fetchone()
    assert row["author_hash"] and "Jane" not in row["author_hash"]
    raw = json.loads(row["raw_json"])
    assert "userName" not in raw and "author" not in raw["nested"] and raw["nested"]["keep"] == 1
    assert "Jane" not in json.dumps([tuple(r) for r in db.execute("SELECT * FROM raw_items")])


def test_author_hash_is_stable_and_salted(monkeypatch):
    monkeypatch.setenv("AUTHOR_HASH_SALT", "s1")
    a = store.author_hash("bob")
    assert a == store.author_hash("bob")
    monkeypatch.setenv("AUTHOR_HASH_SALT", "s2")
    assert a != store.author_hash("bob")


def test_infer_product():
    assert store.infer_product("Google Photos search broken") == "google_photos"
    assert store.infer_product("iPhone photos not found") == "apple_photos"
    assert store.infer_product("cats") is None
