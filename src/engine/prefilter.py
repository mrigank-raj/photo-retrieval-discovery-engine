"""Cheap, recall-oriented keyword filter that runs before any LLM call (retrieval plan, section 5)."""
import re

VERBS = re.compile(
    r"\b(find|finding|found|search\w*|look(?:ing)? for|locat\w+|retriev\w+|recover\w*|show(?:s|ing)? up|appear\w*|"
    r"missing|gone|lost|disappear\w*|can'?t see|cannot see|can'?t remember|hard to find|not showing)\b", re.I)
OBJECTS = re.compile(
    r"\b(photos?|pictures?|pics?|images?|screenshots?|videos?|albums?|memor(?:y|ies)|librar(?:y|ies)|timeline|people|faces?|gallery)\b",
    re.I)
FORUM_SOURCES = {"google_community", "reddit", "stackexchange", "hackernews"}


def passes(source, title, text):
    blob = f"{title or ''}\n{text or ''}"
    if source in FORUM_SOURCES:  # replies often say "search" without naming photos ("Why does GP search suck")
        return bool(OBJECTS.search(blob) or VERBS.search(blob))
    return bool(VERBS.search(blob) and OBJECTS.search(blob))
