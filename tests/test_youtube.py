import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from engine.collectors.youtube import title_ok  # noqa: E402


def test_title_filter_keeps_search_videos_and_drops_recovery_and_clickbait():
    assert title_ok("Google Photos search not working? Fix it")
    assert title_ok("How to find old photos in Google Photos")
    assert title_ok("Ask Photos vs classic search: Google Photos Gemini review")
    assert not title_ok("Recover deleted photos even after long time #googlephotos")
    assert not title_ok("Set This Settings For Cookies In GoogleChrome Browser #shorts")
    assert not title_ok("My favourite pizza places")           # no photo word
    assert not title_ok("Best photos of 2026 vacation")        # no retrieval topic word
