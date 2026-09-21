import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine.prefilter import passes  # noqa: E402


def test_store_reviews_need_a_retrieval_verb_and_a_photo_word():
    assert passes("play", None, "I can't find my old photos anymore")
    assert not passes("play", None, "Great app, love it")
    assert not passes("play", None, "Photos are beautiful")          # object word only
    assert not passes("appstore", None, "I lost my password again")  # verb only


def test_forum_sources_need_only_a_photo_word_or_a_retrieval_word():
    assert passes("reddit", "Album question", "how do I share one?")
    assert passes("reddit", "Why does GP search suck so bad?", "Agreed, it is a crapshoot now")
    assert not passes("reddit", "macOS Finder bug", "The UI feels sloppy")
