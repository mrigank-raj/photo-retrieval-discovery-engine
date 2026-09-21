import os
import time
from urllib.parse import quote

import requests

ACTOR = "automation-lab~reddit-scraper"
API = "https://api.apify.com/v2"
RESERVE_USD = 0.25  # always leave this much of the free monthly credit unspent


def _remaining_usd(token):
    d = requests.get(f"{API}/users/me/limits", params={"token": token}, timeout=30).json()["data"]
    return d["limits"]["maxMonthlyUsageUsd"] - d["current"]["monthlyUsageUsd"]


KEYWORDS = ["find", "found", "search", "missing", "lost", "old photos", "wrong date", "date", "metadata", "takeout", "album",
            "face", "people", "memories", "scan", "organize", "recover", "can't", "cannot"]


def fetch(cfg, limit, product_keys, queries=3, subs=4, posts_per_url=5, comments_per_post=10, max_usd=0.5, listing=False, skip=0, since=None):
    """One Apify run with many search URLs (one start fee). Spend is hard-capped by max_usd and the free monthly credit.

    limit is not used directly; volume is subs x queries x posts_per_url posts plus up to comments_per_post comments each.
    """
    from engine.store import infer_product
    token = os.environ["APIFY_TOKEN"]
    remaining = _remaining_usd(token)
    cap = min(max_usd, remaining - RESERVE_USD)
    if cap <= 0.02:
        raise SystemExit(f"Apify free credit nearly used (remaining ${remaining:.2f}); stopping to avoid a hard stop.")
    reddit = cfg["sources"]["reddit"]
    # Generic queries ("search not working") pull in unrelated posts in broad subreddits and every result costs credit.
    qs = [q if "photo" in q.lower() else f"{q} photos" for q in cfg["queries"]["community_and_reddit"][:queries]]
    urls = [f"https://www.reddit.com/r/{s}/search/?q={quote(q)}&restrict_sr=1&sort=relevance&t=all"
            for s in reddit["subreddits"][:subs] for q in qs]
    run_input = {"urls": urls, "maxPostsPerSource": posts_per_url, "includeComments": True,
                 "maxCommentsPerPost": comments_per_post, "commentDepth": 2}
    if listing or since:  # search URLs return few posts; listings filtered by keyword reach many more. Refresh reads the newest posts.
        path = "new/" if since else "top/?t=year"
        run_input["urls"] = urls = [f"https://www.reddit.com/r/{s}/{path}" for s in reddit["subreddits"][skip:subs]]
        run_input["filterKeywords"] = KEYWORDS
    run = requests.post(f"{API}/acts/{ACTOR}/runs", params={"token": token, "maxTotalChargeUsd": round(cap, 3)},
                        json=run_input, timeout=60).json()["data"]
    while True:
        time.sleep(5)
        run = requests.get(f"{API}/actor-runs/{run['id']}", params={"token": token}, timeout=30).json()["data"]
        if run["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break
    rows = requests.get(f"{API}/datasets/{run['defaultDatasetId']}/items", params={"token": token, "format": "json"},
                        timeout=120).json()
    items = []
    for r in rows:
        if r.get("type") == "post":
            text = f"{r.get('title', '')}\n\n{r.get('selfText', '')}".strip()
            items.append({"item_id": f"reddit:{r['id']}", "source": "reddit",
                          "product": infer_product(r.get("subreddit"), r.get("title"), r.get("selfText")),
                          "url": r.get("permalink"), "thread_id": f"reddit:{r['id']}", "created_at": r.get("createdAt"),
                          "title": r.get("title"), "text": text, "helpful_count": _int(r.get("score")),
                          "author": r.get("author"), "raw": r})
        elif r.get("type") == "comment":
            items.append({"item_id": f"reddit:{r['id']}", "source": "reddit",
                          "product": infer_product(r.get("postTitle"), r.get("body")),
                          "url": r.get("permalink"), "thread_id": f"reddit:{r.get('postId')}",
                          "parent_id": f"reddit:{r['parentId']}" if r.get("parentId") else None,
                          "created_at": r.get("createdAt"), "title": r.get("postTitle"), "text": r.get("body"),
                          "helpful_count": _int(r.get("score")), "author": r.get("author"), "raw": r})
    note = (f"apify status={run['status']} usd={run.get('usageTotalUsd')} charged={run.get('chargedEventCounts')} "
            f"urls={len(urls)} cap_usd={cap:.2f} remaining_before_usd={remaining:.2f}")
    return items, [note]


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
