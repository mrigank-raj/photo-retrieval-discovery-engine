"""Hacker News comments via the public Algolia search API (free, no key)."""
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

API = "https://hn.algolia.com/api/v1/search"
QUERIES = ["google photos search", "apple photos search", "finding old photos", "photo library search", "immich",
           "google photos takeout", "ente photos", "google photos ask photos"]


def fetch(cfg, limit, product_keys, per_query=60, since=None):
    from engine.store import infer_product
    after = int((datetime.now(timezone.utc) - timedelta(days=30 * cfg["window_months"])).timestamp())
    if since:
        after = int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp())
    items, errors = [], []
    for q in QUERIES:
        try:
            r = requests.get(API, params={"query": q, "tags": "comment", "hitsPerPage": per_query,
                                          "numericFilters": f"created_at_i>{after}"}, timeout=30)
            r.raise_for_status()
            hits = r.json().get("hits", [])
        except (requests.RequestException, ValueError) as e:
            errors.append(f"{q}: {e}")
            continue
        for h in hits:
            text = BeautifulSoup(h.get("comment_text") or "", "lxml").get_text("\n").strip()
            items.append({"item_id": f"hackernews:{h['objectID']}", "source": "hackernews",
                          "product": infer_product(h.get("story_title"), text),
                          "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
                          "thread_id": f"hackernews:{h.get('story_id')}", "parent_id": f"hackernews:{h['parent_id']}"
                          if h.get("parent_id") else None, "created_at": h.get("created_at"), "title": h.get("story_title"),
                          "text": text, "author": h.get("author"), "raw": {"query": q}})
        time.sleep(0.3)
    return items, errors
