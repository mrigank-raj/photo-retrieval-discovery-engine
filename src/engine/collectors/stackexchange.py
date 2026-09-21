"""Stack Exchange questions via the official API (free, no key needed at this volume). Content is CC BY-SA; every item keeps its link."""
import html
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

API = "https://api.stackexchange.com/2.3/search/advanced"
SITES = ["photo", "apple", "webapps", "superuser", "android", "genealogy"]
QUERIES = ["find old photos", "photos search not working", "google photos can't find", "photos wrong date",
           "lost photos after migration", "search for a specific photo"]


def fetch(cfg, limit, product_keys, per_query=15, since=None):
    from engine.store import infer_product
    items, errors = [], []
    from_epoch = int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp()) if since else None
    for site in SITES:
        for q in QUERIES:
            try:
                r = requests.get(API, params={"q": q, "site": site, "pagesize": per_query, "order": "desc", "sort": "relevance",
                                              "filter": "withbody",
                                              **({"fromdate": from_epoch} if since else {})}, timeout=30)
                r.raise_for_status()
                j = r.json()
            except (requests.RequestException, ValueError) as e:
                errors.append(f"{site}/{q}: {e}")
                continue
            for it in j.get("items", []):
                title = html.unescape(it["title"])
                body = BeautifulSoup(it.get("body", ""), "lxml").get_text("\n")
                items.append({"item_id": f"stackexchange:{site}:{it['question_id']}", "source": "stackexchange",
                              "product": infer_product(title, body, " ".join(it.get("tags", []))), "url": it["link"],
                              "thread_id": f"stackexchange:{site}:{it['question_id']}", "created_at":
                              __import__("datetime").datetime.fromtimestamp(it["creation_date"], __import__("datetime").timezone.utc)
                              .isoformat(timespec="seconds"), "title": title, "text": f"{title}\n\n{body}".strip(),
                              "helpful_count": it.get("score"), "author": (it.get("owner") or {}).get("display_name"),
                              "raw": {"site": site, "tags": it.get("tags"), "answered": it.get("is_answered")}})
            time.sleep(max(0.3, j.get("backoff", 0)))
    errors.append(f"quota_remaining={j.get('quota_remaining') if items else 'n/a'}")
    return items[:limit * 10], errors
