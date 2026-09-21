import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import cluster, refresh, regress, store  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTHOR_HASH_SALT", "test-salt")
    return store.connect(store.init_db(tmp_path / "t.db"))


def test_since_for_steps_back_from_the_newest_item(db):
    assert refresh.since_for(db, "play") is None
    store.insert_items(db, [{"item_id": "play:1", "source": "play", "url": "u", "created_at": "2026-05-10T12:00:00",
                             "text": "I cannot find my old photos anymore", "raw": {}}], since_date="2020-01-01")
    assert refresh.since_for(db, "play") == "2026-05-07"
    assert refresh.since_for(db, "play", overlap_days=0) == "2026-05-10"
    assert refresh.since_for(db, "reddit") is None


def test_compare_flags_only_drops_beyond_tolerance():
    rows = {r[0]: r for r in regress.compare({"relevance_recall": 0.80, "relevance_precision": 0.95},
                                             {"relevance_recall": 0.90, "relevance_precision": 0.93}, 0.05)}
    assert rows["relevance_recall"][4] is False          # fell 10 points
    assert rows["relevance_precision"][4] is True        # rose
    assert rows["extraction_outcome"][4] is True         # absent from both: not a regression
    assert {r[0]: r for r in regress.compare({"relevance_recall": 0.86}, {"relevance_recall": 0.90}, 0.05)}["relevance_recall"][4] is True


def test_assign_new_joins_nearest_cluster_and_leaves_far_items_alone(db, monkeypatch):
    vec = {"a1": [1, 0], "a2": [0.9, 0.1], "b1": [0, 1], "res": [0.7, 0.7], "near_a": [0.95, 0.05], "near_b": [0.05, 0.95], "far": [-1, -0.2]}
    items = [{"item_id": k, "signature": k} for k in vec]
    monkeypatch.setattr(cluster, "load", lambda _db: items)
    embed = lambda texts: np.array([np.array(vec[t], float) / np.linalg.norm(vec[t]) for t in texts])  # noqa: E731
    for cid, name in [(1, "A"), (2, "B"), (3, "[residual] junk")]:
        db.execute("INSERT INTO clusters(cluster_id, name, definition, taxonomy_version) VALUES(?,?,?,?)", (cid, name, "", "v1"))
    db.executemany("INSERT INTO cluster_items VALUES(?,?)", [(1, "a1"), (1, "a2"), (2, "b1"), (3, "res")])
    out = cluster.assign_new(db, embed_fn=embed, min_sim=0.5)
    assert out == {"new": 3, "assigned": 2}
    placed = dict(db.execute("SELECT item_id, cluster_id FROM cluster_items").fetchall())
    assert placed["near_a"] == 1 and placed["near_b"] == 2 and "far" not in placed
    assert cluster.assign_new(db, embed_fn=embed, min_sim=0.5) == {"new": 1, "assigned": 0}  # rerun changes nothing
