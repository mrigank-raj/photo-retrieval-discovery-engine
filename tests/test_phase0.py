import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine import cli  # noqa: E402


def test_schema_creates_all_tables(tmp_path):
    db_file = cli.init_db(tmp_path / "t.db")
    names = {r[0] for r in sqlite3.connect(db_file).execute("select name from sqlite_master where type='table'")}
    assert {"raw_items", "filter_results", "extractions", "cue_mentions",
            "clusters", "cluster_items", "runs", "needs_review"} <= names


def test_taxonomy_every_value_has_a_definition():
    tax = cli.load_yaml("taxonomy.yaml")
    assert tax["version"] == "v1"
    for enum, values in tax.items():
        if enum != "version":
            assert values and all(isinstance(d, str) and d for d in values.values()), enum


def test_llm_config_is_zero_spend_with_a_primary_provider():
    cfg = cli.load_yaml("llm.yaml")
    assert cfg["budget_usd"] == 0
    assert cfg["providers"]["gemini"]["role"] == "primary"
    assert "anthropic" not in cfg["providers"]


def test_disabled_sources_say_why_and_ids_are_present():
    cfg = cli.load_yaml("sources.yaml")
    for name, s in cfg["sources"].items():
        assert "enabled" in s, name
        if not s["enabled"]:
            assert s.get("reason") or s.get("requires_user_decision"), name
    assert cfg["products"]["google_photos"]["ios_id"] and cfg["products"]["apple_photos"]["ios_id"]
