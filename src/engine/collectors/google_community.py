"""Google Photos Help Community.

Listing pages paginate with a "View more" button, so a headless browser clicks it like a visitor would.
Each thread page is then fetched over plain HTTP and parsed from the JSON the page embeds in `var thread_view='...'`.
Low volume by design: one thread request every DELAY seconds; the site's /search paths (disallowed by robots.txt) are never used.
"""
import json
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (research project; polite low-volume crawler)"
LIST_URL = "https://support.google.com/photos/threads?hl=en&thread_filter=(category:{cat})"
THREAD_URL = "https://support.google.com/photos/thread/{tid}?hl=en"
CATEGORIES = ["photos_searching", "photos_restore"]
DELAY = 2.0
_ESC = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}


def _js_unescape(s):
    def rep(m):
        g = m.group(1)
        return chr(int(g[1:], 16)) if g[0] in "xu" and len(g) > 1 else _ESC.get(g, g)
    return re.sub(r"\\(x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|.)", rep, s, flags=re.S)


def _fill_empty_slots(s):
    """The page uses arrays with elided slots like [a,,b]; make them valid JSON."""
    out, in_str, esc, prev = [], False, False, ""
    for c in s:
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif (c == "," and prev in ",[") or (c == "]" and prev == ","):
            out.append("null")
        out.append(c)
        if not c.isspace():
            prev = c
    return "".join(out)


def _walk(o):
    if isinstance(o, list):
        yield o
        for v in o:
            yield from _walk(v)


def _iso(micros):
    return datetime.fromtimestamp(micros / 1e6, tz=timezone.utc).isoformat(timespec="seconds") if micros else None


def _text(html):
    """HTML to text, breaking lines only at <br> and block tags so inline tags (<b>, <a>) do not split sentences."""
    soup = BeautifulSoup(html, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["div", "p", "li", "ul", "ol", "h1", "h2", "h3", "h4", "blockquote"]):
        block.append("\n")
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+\n", "\n", soup.get_text())).strip()


def parse_thread(page_html, tid):
    """Return {title, body, created_at, category, platform, replies:[{id, text, created_at}]} or None."""
    m = re.search(r"var thread_view='(.*?)';", page_html, re.S)
    if not m:
        return None
    data = json.loads(_fill_empty_slots(_js_unescape(m.group(1))))
    tid_int, thread, replies = int(tid), None, {}
    for node in _walk(data):
        head = node[0] if node and isinstance(node[0], list) else None
        if not head or len(head) < 3:
            continue
        if head[0] == tid_int and len(node) > 21 and isinstance(node[8], str) and isinstance(node[12], str):
            thread = thread or node
        elif head[2] == tid_int and len(node) > 16 and isinstance(node[3], str):
            replies.setdefault(head[0], node)
    if not thread:
        return None
    platform = next((v for k, v in (thread[15] or []) if k == "platform"), None) if len(thread) > 15 else None
    return {
        "title": thread[8], "body": _text(thread[12]),
        "created_at": _iso(thread[38] if len(thread) > 38 and isinstance(thread[38], int) else thread[16]),
        "category": thread[21], "platform": platform,
        "replies": [{"id": mid, "text": _text(n[3]), "created_at": _iso(n[16] if isinstance(n[16], int) else None)}
                    for mid, n in sorted(replies.items())],
    }


def thread_ids(category, want, max_clicks=40):
    from playwright.sync_api import sync_playwright
    ids = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        page.goto(LIST_URL.format(cat=category), wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)
        for _ in range(max_clicks + 1):
            hrefs = page.eval_on_selector_all("a[href*='/photos/thread/']", "els=>els.map(e=>e.getAttribute('href'))")
            ids = list(dict.fromkeys(re.findall(r"/photos/thread/(\d+)", " ".join(hrefs))))
            more = page.get_by_text("View more", exact=True)
            if len(ids) >= want or more.count() == 0:
                break
            more.first.click()
            page.wait_for_timeout(int(DELAY * 1000))
        browser.close()
    return ids[:want]


def fetch(cfg, limit, product_keys, since=None):
    """limit = target items (questions plus replies). Threads average about 4 items."""
    threads_needed = max(2, limit // 4)
    per_cat = -(-threads_needed // len(CATEGORIES))
    queue = [tid for pair in zip(*[thread_ids(c, per_cat) for c in CATEGORIES]) for tid in pair]
    session, items, errors, used = requests.Session(), [], [], 0
    session.headers["User-Agent"] = UA
    for tid in queue:
        if len(items) >= limit:
            break
        time.sleep(DELAY)
        try:
            r = session.get(THREAD_URL.format(tid=tid), timeout=30)
            r.raise_for_status()
            t = parse_thread(r.text, tid)
        except (requests.RequestException, ValueError) as e:
            errors.append(f"thread {tid}: {type(e).__name__}: {e}")
            continue
        if not t:
            errors.append(f"thread {tid}: no embedded data found")
            continue
        used += 1
        url = f"https://support.google.com/photos/thread/{tid}"
        base = {"source": "google_community", "product": "google_photos", "title": t["title"], "thread_id": f"gcomm:{tid}"}
        items.append({**base, "item_id": f"gcomm:{tid}", "url": url, "created_at": t["created_at"],
                      "text": f"{t['title']}\n\n{t['body']}",
                      "raw": {"kind": "question", "category": t["category"], "platform": t["platform"]}})
        for r_ in t["replies"]:
            items.append({**base, "item_id": f"gcomm:{tid}:{r_['id']}", "url": url, "parent_id": f"gcomm:{tid}",
                          "created_at": r_["created_at"], "text": r_["text"],
                          "raw": {"kind": "reply", "category": t["category"]}})
    errors.append(f"threads_parsed={used} of {len(queue)} listed; delay={DELAY}s")
    return items[:limit], errors
