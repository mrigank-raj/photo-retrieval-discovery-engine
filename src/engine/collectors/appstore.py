import time

import requests

URL = "https://itunes.apple.com/{cc}/rss/customerreviews/page={n}/id={id}/sortby={sort}/json"
SORTS = ("mostrecent", "mosthelpful")


def fetch(cfg, limit, product_keys, since=None):
    """limit = target items for the whole source, split evenly across products, locales and sort orders."""
    products = {k: cfg["products"][k] for k in product_keys if cfg["products"][k].get("ios_id")}
    locales = cfg["locales"]
    sorts = ("mostrecent",) if since else SORTS  # refresh: newest reviews only, stopping once they are older than `since`
    quota = 50 if since else max(1, limit // (len(products) * len(locales) * len(SORTS)))
    items, errors = [], []
    for key, p in products.items():
        for sort in sorts:
            for cc in locales:
                got = 0
                for page in range(1, 11):
                    if got >= quota:
                        break
                    try:
                        r = requests.get(URL.format(cc=cc, n=page, id=p["ios_id"], sort=sort), timeout=20)
                        r.raise_for_status()
                        entries = r.json()["feed"].get("entry", [])
                    except (requests.RequestException, ValueError, KeyError) as e:
                        errors.append(f"{key}/{cc}/{sort}/p{page}: {e}")
                        break
                    entries = [entries] if isinstance(entries, dict) else entries
                    reviews = [e for e in entries if "im:rating" in e]
                    if not reviews:
                        break
                    for e in reviews[: quota - got]:
                        if since and e["updated"]["label"][:10] < since:
                            got = quota  # newest first, so everything after this one is older
                            break
                        got += 1
                        items.append({
                            "item_id": f"appstore:{cc}:{e['id']['label']}",
                            "source": "appstore", "product": key,
                            "url": (e.get("link") or {}).get("attributes", {}).get("href")
                                   or f"https://apps.apple.com/{cc}/app/id{p['ios_id']}",
                            "created_at": e["updated"]["label"],
                            "title": e["title"]["label"], "text": e["content"]["label"],
                            "rating": int(e["im:rating"]["label"]),
                            "helpful_count": int(e.get("im:voteSum", {}).get("label", 0) or 0),
                            "app_or_os_version": e.get("im:version", {}).get("label"),
                            "locale": cc, "author": (e.get("author") or {}).get("name", {}).get("label"), "raw": e,
                        })
                    time.sleep(0.4)
    return items, errors
