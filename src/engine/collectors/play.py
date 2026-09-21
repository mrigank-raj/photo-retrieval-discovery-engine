import time

from google_play_scraper import Sort, reviews

# Any-rating newest plus 1-3 star newest, so the sample is not dominated by 5-star noise.
SLICES = [(None, 0.5), (1, 1 / 6), (2, 1 / 6), (3, 1 / 6)]


def fetch(cfg, limit, product_keys, since=None):
    """limit = target items for the whole source, split across products.

    Play reviews are not country-specific (asking for five countries returned the same reviews five times),
    so each product is fetched once, in English, from the US store.
    """
    products = {k: cfg["products"][k] for k in product_keys if cfg["products"][k].get("play_id")}
    per_product = max(6, limit // len(products))
    slices = [(None, 1.0)] if since else SLICES  # refresh: only the newest reviews, any rating
    per_product = min(100, per_product) if since else per_product
    items, errors = [], []
    for key, p in products.items():
        for score, share in slices:
            try:
                batch, _ = reviews(p["play_id"], lang="en", country="us", sort=Sort.NEWEST,
                                   count=max(1, int(per_product * share)), filter_score_with=score)
            except Exception as e:  # scraper raises assorted errors; record and move on
                errors.append(f"{key}/score={score}: {type(e).__name__}: {e}")
                continue
            for r in batch:
                items.append({
                    "item_id": f"play:{r['reviewId']}", "source": "play", "product": key,
                    "url": f"https://play.google.com/store/apps/details?id={p['play_id']}&reviewId={r['reviewId']}",
                    "created_at": r["at"].isoformat() if r.get("at") else None,
                    "text": r.get("content"), "rating": r.get("score"), "helpful_count": r.get("thumbsUpCount"),
                    "app_or_os_version": r.get("reviewCreatedVersion") or r.get("appVersion"),
                    "locale": "us", "author": r.get("userName"), "raw": r,
                })
            time.sleep(0.5)
    return items, errors
