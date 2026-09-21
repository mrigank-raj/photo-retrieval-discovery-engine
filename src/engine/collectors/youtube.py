import os
import re
import time
from datetime import datetime, timedelta, timezone
from itertools import zip_longest

import requests

API = "https://www.googleapis.com/youtube/v3"
QUOTA = {"search": 100, "videos": 1, "commentThreads": 1}


def _get(path, units, **params):
    r = requests.get(f"{API}/{path}", params={**params, "key": os.environ["YOUTUBE_API_KEY"]}, timeout=30)
    r.raise_for_status()
    units[0] += QUOTA[path]
    return r.json()


PHOTO = re.compile(r"\b(photos?|pictures?|gallery|images?|pics?)\b", re.I)
TOPIC = re.compile(r"search|find|finding|missing|old|organi[sz]|ask photos|gemini|takeout|date|metadata|scan|digiti[sz]|"
                   r"face|people|\bvs\b|compar|review|tips", re.I)
# Deletion-recovery, browser-settings and Shorts clickbait dominated the first pull (0 of 72 sampled comments were about finding photos).
EXCLUDE = re.compile(r"delet|recover|restore|cookie|password|hack|unlock|#shorts", re.I)


def title_ok(title):
    return bool(PHOTO.search(title) and TOPIC.search(title) and not EXCLUDE.search(title))


def _comment_item(t, vid, title, query):
    from engine.store import infer_product
    c = t["snippet"]["topLevelComment"]
    sn = c["snippet"]
    return {"item_id": f"youtube:{c['id']}", "source": "youtube", "product": infer_product(title, query),
            "url": f"https://www.youtube.com/watch?v={vid}&lc={c['id']}", "thread_id": f"youtube:{vid}",
            "created_at": sn["publishedAt"], "title": title, "text": sn["textDisplay"], "helpful_count": sn.get("likeCount"),
            "author": sn.get("authorChannelId", {}).get("value") or sn.get("authorDisplayName"), "raw": t}


def fetch(cfg, limit, product_keys, queries=12, videos_per_query=12, min_comments=5, max_videos=70, since=None, known_videos=None):
    """limit = total comments to collect. Quota use is recorded in the returned errors list as 'quota_units=N'.

    Videos are taken in search-relevance order (round robin across queries), never ranked by comment count, because that
    favoured viral clickbait. With `since` (refresh), only videos published after that date are searched, and the newest
    comments of `known_videos` ({video id: title}) are read too, at 1 quota unit each.
    """
    units, errors, items, newest = [0], [], [], []
    after = (datetime.now(timezone.utc) - timedelta(days=30 * cfg["window_months"])).strftime("%Y-%m-%dT00:00:00Z")
    if since:
        after = f"{since}T00:00:00Z"
    for vid, title in (known_videos or {}).items():
        try:
            page = _get("commentThreads", units, part="snippet", videoId=vid, order="time", maxResults=100, textFormat="plainText")
            newest += [_comment_item(t, vid, title, "") for t in page["items"]
                       if t["snippet"]["topLevelComment"]["snippet"]["publishedAt"] >= after]
        except requests.RequestException as e:
            errors.append(f"newest comments {vid}: {e}")
    videos, per_query = {}, []
    for q in cfg["queries"]["youtube_video_discovery"][:queries]:
        try:
            hits = _get("search", units, part="snippet", q=q, type="video", order="relevance", maxResults=videos_per_query,
                        relevanceLanguage="en", publishedAfter=after)["items"]
        except requests.RequestException as e:
            errors.append(f"search '{q}': {e}")
            continue
        ranked = []
        for h in hits:
            vid, title = h["id"]["videoId"], h["snippet"]["title"]
            if title_ok(title) and vid not in videos and vid not in (known_videos or {}):
                videos[vid] = {"title": title, "query": q}
                ranked.append(vid)
        per_query.append(ranked)
    ids = [v for group in zip_longest(*per_query) for v in group if v]
    for i in range(0, len(ids), 50):
        for v in _get("videos", units, part="snippet,statistics", id=",".join(ids[i:i + 50]))["items"]:
            lang = v["snippet"].get("defaultAudioLanguage") or v["snippet"].get("defaultLanguage") or "en"
            videos[v["id"]]["comments"] = int(v["statistics"].get("commentCount", 0)) if lang.lower().startswith("en") else 0
    chosen = [v for v in ids if videos[v].get("comments", 0) >= min_comments][:max_videos]
    per_video = min(100, max(15, limit // max(1, len(chosen))))
    for vid in chosen:
        if len(items) >= limit:
            break
        title, token, got = videos[vid]["title"], None, 0
        while got < per_video:
            try:
                page = _get("commentThreads", units, part="snippet", videoId=vid, order="relevance", maxResults=100,
                            textFormat="plainText", **({"pageToken": token} if token else {}))
            except requests.RequestException as e:
                errors.append(f"comments {vid}: {e}")
                break
            got += len(page["items"])
            items += [_comment_item(t, vid, title, videos[vid]["query"]) for t in page["items"]]
            token = page.get("nextPageToken")
            if not token:
                break
            time.sleep(0.2)
    errors.append(f"quota_units={units[0]} videos_considered={len(ids)} videos_used={len(chosen)} known_videos={len(known_videos or {})}")
    return newest + items[:limit], errors
