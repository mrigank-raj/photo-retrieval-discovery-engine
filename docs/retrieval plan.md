# Retrieval Plan (Data Collection)

How the discovery engine gets raw user conversation into the system. Read alongside `problem statement.txt` and `context.md` (all in `docs/`). Machine-readable settings live in `../config/sources.yaml`.

**Scope decision.** Tier-1 channels plus Reddit via Apify. In Phase 4, Stack Exchange and Hacker News were added as a narrative-source test (see 4.6). Other Tier-2 sources (GitHub, Bluesky/Mastodon, genealogy forums, tech-press comments) remain deferred.

**Labels.** **[Sourced]** = supported by the research in `context.md`. **[Verify]** = from memory or assumption; confirm at build time. Numbers marked *planning assumption* are targets to adjust after the pilot, not facts.

---

## 1. Sources in scope

| # | Source | Method | Why it is in |
|---|---|---|---|
| 1 | Google Play reviews | Python/npm scraper or Apify actor | Volume; version-specific regressions |
| 2 | Apple App Store reviews | Official RSS feed | Same third-party apps on iOS |
| 3 | Google Photos Help Community | Browser clicks "View more" on listings; threads fetched over plain HTTP | Detailed failure reports with repro steps. **Enabled by you on 2026-09-20** (see 4.3). |
| 4 | YouTube comments | Official YouTube Data API v3 | Reactions to launches and how-to videos |
| 5 | Reddit | Apify actor | Long-form narratives, workarounds, migration stories |
| ~~6~~ | ~~Apple Community~~ | ~~n/a~~ | **Dropped in Phase 0**: it serves a bot-verification challenge (see 4.3). |

**Phase 0 update.** Apple Photos does have App Store reviews: its listing (id 1584215428) returned live reviews from the RSS feed, so it is covered directly and also through Reddit and YouTube. Samsung Gallery is not listed on Google Play (HTTP 404), so it is covered only through Reddit and YouTube.

## 2. Products and apps to cover

Cover more than Google Photos so findings describe photo retrieval, not one app **[Sourced: over-fitting risk in `context.md` section 11]**.

| Product | Google Play | App Store | Community / Reddit / YouTube |
|---|---|---|---|
| Google Photos | yes | yes | yes |
| Apple Photos | n/a | yes | Reddit, YouTube |
| Amazon Photos | yes | yes | Reddit, YouTube |
| Microsoft OneDrive (photos) | yes | yes | Reddit, YouTube |
| Samsung Gallery | not on Play | n/a | Reddit, YouTube |
| Dropbox (camera upload) | yes | yes | Reddit |
| Self-hosted (Immich, Ente) | yes | yes | Reddit only |

**Identifiers are verified and stored in `config/sources.yaml`.** App Store IDs came from the iTunes Search API; Play package IDs were confirmed by an HTTP 200 from each store listing (2026-09-20).

**Sampling target *(planning assumption)*:** at least 50% of collected items from Google Photos and Apple Photos, at least 25% from other products, so no single product exceeds about 60% of the corpus.

## 3. Time window and language

- **Window:** last 36 months for everything, so the Ask Photos period (2024 to 2026) and pre-LLM baseline are both covered. YouTube tutorials and Reddit threads older than this can be included if they rank in searches for old-photo problems.
- **Language:** English only for v1. Play and App Store: locales `us, gb, in, au, ca`. This leaves out non-English markets, which is a known limitation.

## 4. Per-source retrieval spec

### 4.1 Google Play reviews

- **Approach:** pull reviews per app, sorted newest first, then filter locally. Play has no keyword search, so the keyword pre-filter (section 5) does the narrowing.
- **Tool:** Python `google-play-scraper` (v1.2.7, last released 2024-06-07, so not recent), with an Apify Play Store actor as fallback if it breaks in Phase 1.
- **Pull plan per app:** newest 10,000 reviews or 36 months, whichever comes first, across `us, gb, in, au, ca`. For Google Photos, additionally pull ratings 1-3 stars separately to guard against the sample being all 5-star noise. *(planning assumption)*
- **Keep:** review text, rating, thumbs-up count, app version, date, developer reply if present.

### 4.2 Apple App Store reviews

- **Approach:** the public customer-reviews RSS feed, per app, per country, per sort order (`mostrecent`, `mosthelpful`). URL pattern verified: `https://itunes.apple.com/{cc}/rss/customerreviews/page={n}/id={ios_id}/sortby=mostrecent/json` returned 50 reviews per page for Google Photos and Apple Photos.
- **Hard limit [Sourced]:** 500 reviews per app per country per sort order, max 10 pages, no developer replies. So 5 countries x 2 sorts x 500 = up to 5,000 reviews per app.
- **Keep:** title, body, rating, version, date, country.

### 4.3 Google Photos Help Community (Apple Community dropped)

**Phase 0 findings (2026-09-20):**

| Site | Technical access | robots.txt | Terms | Decision |
|---|---|---|---|---|
| Google Photos Help Community | **Corrected:** the visible HTML holds no thread text (my first check matched only the page title). The text is in JSON embedded in the page (`var thread_view='...'`), and listing pagination is client-side | Disallows only `/*/search`, `/*/api`, attachments; threads allowed | Google's general terms are reported to restrict automated access without permission; the Help Community's own terms were not verified | **Enabled by you**, low volume |
| Apple Community | Returns a "Security Verification" bot challenge; sitemap returns HTTP 500 | Threads allowed; `/profile`, `/tags`, feeds disallowed | The Community use agreement has no scraping clause; Apple's general site terms prohibit robots and page-scraping | **Dropped for v1**: getting past the challenge means circumventing an access control |

- **Approach (built and tested):** a headless browser (Playwright) opens the category listing and clicks "View more" (20 threads per click), then each thread page is fetched over plain HTTP about once every 2 seconds and its embedded JSON is parsed. The collector never uses the `/search` path. Question and each reply become separate items linked by `thread_id`.
- **Categories:** `photos_searching` (Search) and `photos_restore` (Restore Photos), alternated. The Community also has Backup, Editing, Storage, Creations and other categories, which are not used.
- **Pilot result:** 76 threads, 164 items after cleaning. Listings are sorted by recent activity, so early pages are short, recent posts; going deeper with more "View more" clicks reaches older, longer threads.
- **Fragility:** the parser depends on undocumented page internals, so it can break without warning. A test covers the parser; a run that parses zero threads logs the failure.
- **Text note:** replies sometimes greet the poster by first name ("Hello ..."). No author fields are read or stored.
- **Not used:** discovery by search query, because `/*/search` is disallowed by `robots.txt`.
- **Keep:** thread title, question body, replies (with an `is_accepted_answer` flag if shown), platform/OS version if stated, date, reply count, thread URL.
- **Apple Photos substitute:** App Store reviews for Apple Photos, Reddit (`r/iphone`, `r/apple`, `r/ios`, `r/AppleHelp`) and YouTube.
- **What this costs us:** detailed, repro-style failure reports (for example the iOS 18 caption-search threads) are the richest source for the memory-cue analysis. Without either community, cue-level depth will come mostly from Reddit.

### 4.4 YouTube comments

- **Approach:** YouTube Data API v3 only. Two steps: find videos, then pull comment threads.
- **Quota math [Sourced + known]:** default 10,000 units/day; `commentThreads.list` = 1 unit per call (up to 100 comments); `search.list` = 100 units per call **[Verify at first run]**. So a search-heavy discovery step is the expensive part.
- **Video discovery queries** (the 10 below, expanded to about 30 variants, roughly 3,000 units): `google photos search not working`, `find old photos google photos`, `Ask Photos`, `google photos vs apple photos search`, `iphone photos search not working`, `find deleted photos`, `google takeout photos metadata fix`, `organize thousands of photos`, `scan old photos organize`, `photos wrong date fix`.
- **Video filter:** at least 50 comments, published in the last 36 months, exclude channels that are pure ads.
- **Comment pull:** top-level threads plus replies for the top 100 videos, relevance order. *(planning assumption)*
- **Keep:** comment text, like count, video id/title/channel, date, parent id. Comments are short, so context (video title) must travel with each comment.

### 4.5 Reddit (via Apify)

- **Actor chosen in Phase 0:** `automation-lab/reddit-scraper` (posts and comments, configurable comment depth and per-post limit, subreddit and search-query input, 4.8/5 rating, about 4,000 users, $0.60 per 1,000 posts at the free tier). **Fallback:** `clearpath/reddit-search-scraper` (posts and comments in one run, about $0.99 per 1,000 results, global searches without a subreddit capped near 300 results).
- **Known caveats:** comment extraction is documented as best-effort (deep threads and "more comments" are not guaranteed), vote counts can be 0, and the comment price was not stated. Phase 1 runs a tiny test and checks the bill before scaling. The actors that looked usable were listed on 2026-09-20; check again if a run fails.
- **Candidate subreddits [Verify each exists and is active in the Phase 1 test run]:** `r/GooglePhotos`, `r/iphone`, `r/apple`, `r/ios`, `r/AppleHelp`, `r/photography`, `r/DataHoarder`, `r/selfhosted`, `r/immich`, `r/Android`, `r/androidapps`, `r/GooglePixel`, `r/OneDrive`, `r/genealogy`, `r/photorestoration`.
- **Search queries per subreddit:** the same discovery queries as 4.3 plus `find old photo`, `photo search`, `lost my photos`, `can't remember when`, `switched from google photos`, `takeout`.
- **Pull plan:** last 36 months, posts plus comments (depth 2), top posts by relevance and by recency per query. **Capped by the Apify free plan** ($5/month hard stop, no billing): expect about 1,500 posts plus their comments, to be measured in the Phase 1 test run. Prioritise `r/GooglePhotos`, `r/iphone`, `r/DataHoarder` and `r/genealogy` first.
- **Compliance note:** Reddit's `robots.txt` disallows all crawlers (verified 2026-09-20), it prohibits scraping outside its API terms, and it has sued large-scale scrapers **[Sourced]**. We are using Apify knowingly, at small non-commercial scale. Disclose the method in the final write-up and keep collection minimal (section 9).

### 4.6 Narrative-source test (Phase 4): Stack Exchange and Hacker News

Added to test whether sources with longer, problem-statement-style text contain more memory cues. Both use official or public APIs and need no scraping. Stack Exchange: API v2.3 `search/advanced` over the photo, apple, webapps, superuser, android and genealogy sites (content is CC BY-SA, so every item keeps its link; attribute contributors in the write-up); 10-year window because most matching questions are older than three years. Hacker News: Algolia search API, comments only. Result: neither source yields reliable "remembered or forgotten" evidence (see `implementation plan.md`, Phase 4 status). Both stay in the corpus as ordinary sources. Reddit listing mode (`--listing`) was also added because search URLs return few posts.

## 5. Keyword pre-filter (cheap, recall-oriented)

Runs before any LLM call to cut cost. It must err toward including items.

- **Retrieval verbs:** `find, finding, found, search, searching, look for, looking for, locate, retrieve, recover, show up, appear, missing, gone, lost, can't see, can't remember, hard to find`
- **Object terms:** `photo, photos, picture, pictures, image, screenshot, video, album, memory, memories, library, timeline, people, faces`
- **Age terms:** `old, older, years ago, from 20xx, scanned, prints, childhood, archive, migrated, transferred, takeout`
- **Rule:** keep an item if it contains at least one retrieval verb *and* one object term. Keep all of Community and Reddit posts in target subreddits that contain any object term.
- **Validation (required):** hand-label a random sample of 300 items that the pre-filter *rejected*. If more than 10% are actually retrieval-related, widen the term lists. *(planning assumption)*

## 6. Unified raw record

All collectors write the same shape. Anything source-specific goes in `raw_json`.

| Field | Notes |
|---|---|
| `item_id` | `{source}:{native_id}`, primary key |
| `source` | `play`, `appstore`, `apple_community`, `google_community`, `youtube`, `reddit` |
| `product` | Google Photos, Apple Photos, Amazon Photos, and so on |
| `url` | Permalink, mandatory (evidence must be traceable) |
| `thread_id`, `parent_id` | For conversations |
| `author_hash` | Salted hash; never store the raw username |
| `created_at`, `fetched_at` | UTC |
| `title`, `text` | Text is stored verbatim |
| `rating`, `helpful_count` | If the source has them |
| `app_or_os_version` | If present |
| `locale` | Country or language |
| `content_hash` | Hash of normalized text, for de-duplication |
| `raw_json` | Untouched source payload |

## 7. Quality controls

- **De-duplicate** by `item_id` and by `content_hash` (reviews are often copy-pasted across countries).
- **Drop** items under 15 characters, non-English text, and obvious spam/promotion.
- **Store the full thread** for Community and Reddit so a reply can be read with its question.
- **Log every run:** source, query, counts fetched, counts kept, errors, elapsed time, cost. Failed pages are retried, then recorded, never silently skipped.
- **Coverage report** after each run: items by source, product, month. This is how we spot platform skew and release-date spikes early.

## 8. Volume and free-tier limits *(planning assumptions)*

**Budget: $0.** Every tool is on a free tier and billing is never enabled. Volumes are sized to fit these limits:

| Resource | Free limit (as reported; verify) | Consequence |
|---|---|---|
| Apify | $5 platform credit per month; the free plan stops rather than bills | Reddit is capped at what $5 buys (about 1,500 posts plus comments, to be measured in Phase 1); spread across billing months if needed |
| YouTube Data API | 10,000 units/day | Enough; spread the video-search step across two days |
| Gemini free tier | Flash-Lite about 1,000 requests/day, Flash about 250/day (sources disagree) | Batch 20 items per relevance request and 5 per extraction request |
| App Store RSS, Play scraper | Free | No cap beyond the RSS limits |

| Stage | Pilot | Full run |
|---|---|---|
| Raw items collected | about 1,200 (about 300 per source) | 20,000 to 35,000 |
| After pre-filter | about 400 | 7,000 to 10,000 |
| After LLM relevance filter | about 200 | 2,000 to 4,000 |
| Sent to full extraction | about 200 | 2,000 to 4,000 |
| Model requests for the full run | about 30 | about 350 relevance + 400 to 800 extraction, over 3 to 5 days |

Adjust after the pilot; if the retrieval-relevant share is much lower than 10%, collect more from Reddit and less from Play (within the Apify cap).

## 9. Ethics, privacy, legal guardrails

- Public content only; no login-gated pages, no private groups.
- Respect `robots.txt`, rate limits and site terms; record the decision per source in `config/sources.yaml`.
- Hash usernames; do not collect or store emails, names in profiles, or other personal data.
- Quote sparingly in outputs, always with the source URL; do not republish datasets.
- Non-commercial, academic-style use. If the project later becomes commercial, revisit Reddit and Apify usage and each site's terms.
- I am not a lawyer; the terms of each source should be checked before the full run.

## 10. What is out of this plan

- Tier-2 sources (GitHub issues, Hacker News, Bluesky/Mastodon, genealogy forums, tech-press comments).
- X/Twitter, Facebook, Instagram, TikTok, Trustpilot, G2, Quora.
- Non-English collection.
- Real-time monitoring; v1 is batch collection with periodic refresh.
