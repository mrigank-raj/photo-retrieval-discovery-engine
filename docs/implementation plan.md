# Implementation Plan (Phase-wise)

Builds the system in `architecture.md`, collecting the data in `retrieval plan.md`, to achieve the goal in `problem statement.txt`.

**Sizing.** Effort is in working days for one person building alongside other commitments, and is a rough estimate to be revised after Phase 1. Every phase ends with a checkable exit criterion; do not start the next phase until it is met.

**Order rationale.** Data access comes first because it is the biggest external risk. Labeling comes before scale so quality is measured before money is spent. Scale comes after the schema stabilizes.

| Phase | Name | Effort | Output |
|---|---|---|---|
| 0 | Setup and gates | 2-3 days | Keys, compliance notes, repo skeleton, taxonomy v0 |
| 1 | Collection pilot | 4-5 days | 4 working collectors (5 if Google Community is enabled), about 1,200 raw items |
| 2 | Relevance filter | 3-4 days | Measured filter, labeled set |
| 3 | Extraction pilot | 5-6 days | Validated extraction on about 250 items, taxonomy v1 |
| 4 | Full run | 5-7 days (free daily quotas) | 2,000 to 4,000 extracted items |
| 5 | Clustering and comparison | 5-6 days | Named, ranked, comparable problem clusters |
| 6 | Explorer and findings report | 4-5 days | Explorer app and `report.md` answering the discovery questions |
| 7 | Hardening (optional) | 2-3 days | Repeatable refresh, docs |

---

## Phase 0: Setup and gates

**Goal:** remove blockers and lock the working vocabulary before writing collectors.

**Tasks**
1. Create free accounts and keys: Apify (Reddit), Gemini API key from Google AI Studio (LLM), Google Cloud project with YouTube Data API v3 enabled, optionally Groq (LLM fallback). No billing on any of them. Store in `.env`; add `.env` and `data/` to `.gitignore`.
2. Check `robots.txt` and terms for Apple Community and Google Photos Help Community. Record result and decision per source in `config/sources.yaml`. If either forbids automated access, drop it and note the substitute (see risks).
3. Pick the Apify Reddit actor using the criteria in `retrieval plan.md` 4.5; run one tiny test query and inspect the output fields.
4. Create the repo skeleton from `architecture.md` section 7 and the SQLite schema from section 6.
5. Turn `context.md` sections 4, 5 and 9 into `config/taxonomy.yaml` (v0).
6. Resolve Play package IDs and App Store IDs for the products in `retrieval plan.md` section 2.

**Deliverables:** working `.env`, `sources.yaml`, `taxonomy.yaml` v0, empty database.

**Exit criteria:** every source is either cleared or explicitly dropped; each key makes one successful test call.

**Risks:** a community site blocks scraping (reduce to Play, App Store, YouTube and Reddit for v1); Apify actor returns no comments (choose another actor).

### Phase 0 status (2026-09-20): done except API keys and one decision

| Task | Result |
|---|---|
| 1. Keys | `.env`, `.env.example`, `.gitignore` created; username-hash salt generated. **You still need to add `GEMINI_API_KEY`, `APIFY_TOKEN` and `YOUTUBE_API_KEY`** (all free; `GROQ_API_KEY` is optional); then run `check-keys`. Not done: I cannot create accounts. **Zero-spend change:** the Anthropic key was dropped; LLM settings are in `config/llm.yaml`. |
| 2. Compliance | Apple Community dropped (bot challenge). Google Photos Community disabled pending your decision. Reddit robots.txt blocks all crawlers; Apify use is your decision, recorded. Details in `retrieval plan.md` 4.3. |
| 3. Apify actor | `automation-lab/reddit-scraper` chosen, `clearpath/reddit-search-scraper` as fallback. Test run deferred until the token exists. |
| 4. Skeleton | Folders, `schema.sql` (8 tables), `cli.py` with `init-db`, `check-config`, `check-keys`; database created. |
| 5. Taxonomy v0 | `config/taxonomy.yaml`: 9 enums, each value defined. |
| 6. IDs | 7 products resolved (iTunes Search API and Play listings). Samsung Gallery is not on Play. Apple Photos does have App Store reviews. |

Tests: `PYTHONPATH=src python -m pytest tests` passes (4 tests, including one that asserts the LLM budget is $0). `check-keys` correctly reports the three missing keys and skips the optional Groq key. When the Gemini key works it also lists the Flash models available, so `config/llm.yaml` can be corrected.

**Open items before Phase 1:** add the three keys; decide on Google Photos Community (enable at low volume, or drop); confirm you are fine with the sample being weaker on detailed repro-style reports without a vendor community.

**Effect on later phases:** Phase 1 has four collectors (Play, App Store, YouTube, Reddit), plus Google Community if you opt in. The Phase 1 target of 300 items per source still applies. Replace "five collectors" and "all five sources" below with these.

---

## Phase 1: Collection pilot

**Goal:** prove each source can be pulled into the unified record.

**Tasks**
1. Write one collector per source (`retrieval plan.md` section 4), each with a `--limit` flag. Start with the two with least risk: App Store RSS and YouTube.
2. Implement normalize-and-insert with author hashing and de-duplication (`retrieval plan.md` sections 6, 7).
3. Implement the `runs` log: counts, errors, elapsed time, cost.
4. Pull about 300 items per source across at least three products.
5. Produce a coverage report (items by source, product, month) and read 30 random items by eye per source.

**Deliverables:** five collectors, about 1,500 raw items, coverage report.

**Exit criteria:** all five sources yield items in the unified shape with working URLs; duplicates removed; no raw usernames stored; the coverage report shows no source at zero.

**Risks:** Play scraper broken (switch to the Apify Play actor); App Store cap hit (expected; accept 500 per country per sort); community pages JavaScript-rendered (use a headless browser fallback).

### Phase 1 status (2026-09-20): done, exit criteria met

All four keys pass `check-keys`. Google Photos Community was enabled by you after the first four sources were built.

**Correction to Phase 0:** I said the Community pages were fully server-rendered. That was wrong: the thread text is not in the visible HTML, only in JSON embedded in the page, and listing pagination needs a browser click. The collector was rebuilt accordingly (Playwright for listing, plain HTTP plus a JSON parser for threads), and a bug where inline tags split sentences was caught by a test and fixed before any Community data was kept.

| Source | Collected | Notes |
|---|---|---|
| App Store | 210 | 7 products, 5 countries, both sort orders. 84 more fell outside the 36-month window and were dropped. |
| Google Play | 273 | 6 products. |
| YouTube | 300 | 9 videos, 605 of 10,000 daily quota units used. |
| Reddit | 135 (24 posts, 111 comments after filtering) | 12 searches in one Apify run, $0.12 spent. |
| Google Photos Community | 164 | Enabled by you afterwards. 76 threads from the Search and Restore Photos categories; questions and replies as separate items. |
| **Total** | **1,082** | 0 items missing a URL or text; 0 usernames or profile fields in the first 918 rows (scanned; Community rows store no author data). Authors stored only as salted hashes. |

Commands: `PYTHONPATH=src python -m engine.cli collect {appstore|play|youtube|reddit|google_community} --limit N`, then `coverage` and `sample`. Every run is logged in the `runs` table. 9 tests pass.

**What the pilot taught us (all fed back into the code):**
- **Play reviews are not country-specific.** Asking five countries returned the same reviews five times (238 duplicates in the first run). Play is now fetched once per product from the US store; the `locales` setting applies only to the App Store.
- **Google Photos is thin in the store reviews** (21 App Store, 22 Play): most of its reviews are very short or duplicate ("great app"). The full run needs a larger pull for it, and YouTube currently supplies all of the Google Photos volume in the pilot.
- **Volume is mostly noise, as expected.** Average text length is 56 characters on YouTube, 157 on Play, 266 on Reddit, 361 on the App Store. Many rows are praise or off-topic; that is what the Phase 2 filter is for.
- **The language check is weak.** Romanised Hindi and Telugu YouTube comments pass the ASCII test. The Phase 2 relevance step should also return a `language` field.
- **Reddit search returns off-topic posts for generic queries** (for example a macOS bug from "search not working"), and every result costs credit. Queries now always include the word "photos".
- **Reddit cost matches the price list:** $0.003 per run, $0.00115 per post, $0.000575 per comment. Of the $5 monthly credit, about $0.15 is spent.
- Reddit URLs come from the actor's permalinks (comment permalinks include the comment id). App Store, Play and YouTube URLs are built from source ids. None were click-tested; Reddit blocks automated checks.

**Shortfalls against the "about 300 per source" target:** Reddit (135) and App Store (210). Neither blocks Phase 2; the full run will collect more.

---

## Phase 2: Relevance filter

**Goal:** separate retrieval signal from noise, with measured accuracy.

**Tasks**
1. Implement the keyword pre-filter (`retrieval plan.md` section 5).
2. Hand-label 300 random pilot items (relevant / not relevant, plus `problem_family`), including 100 that the pre-filter rejected. Save to `eval/labeled_relevance.csv`.
3. Write `prompts/relevance.md`; implement the small-model classifier with batch calls.
4. Measure precision and recall against the labeled set; adjust term lists and prompt until targets are met (`architecture.md` section 8).
5. Record the share of `problem_family` values. This is the first answer to "how much of it is really search?".

**Deliverables:** filter code, labeled set, evaluation result.

**Exit criteria:** recall of at least 90% and precision of at least 70% on the labeled set, or a written note explaining why the targets were changed.

**Risks:** relevant share too low (shift the mix toward Community and Reddit); labels are subjective (label with a written rubric, re-label 50 items a day later and check agreement).

### Phase 2 status: done (labels by Claude; see result below)

**Who labeled.** You asked me to label the 300-item sample. The labels in `eval/labeled_relevance.csv` were assigned by Claude following `eval/labeling_rubric.md`, before the pre-filter's verdicts were opened. They are **model judgments, not human ground truth**: any accuracy measured against them means "agrees with Claude's reading", and 56 rows (19%) are marked borderline in the `notes` column. A human spot-check of the borderline rows is recommended before results are quoted as accuracy.

**What the labels show (300 items):**

| Family | Count |
|---|---|
| other | 144 |
| not_english | 46 |
| search_or_retrieval | 45 (15%) |
| deletion_or_corruption | 33 (11%) |
| backup_or_sync | 18 |
| billing_or_storage | 8 |
| quality_or_editing | 5 |
| account_or_access_loss | 1 |

By source, relevant items: Reddit 17 of 64, App Store 11 of 60, Google Community 9 of 50, Play 8 of 54, **YouTube 0 of 72**. YouTube is weak for this question: the discovery queries surfaced deleted-photo recovery videos (deletion, not search) and an unrelated Chrome-cookies video, and 46 of the 72 comments are Romanised Hindi or Telugu. The YouTube queries need rework before the full run.

**Keyword pre-filter** (`src/engine/prefilter.py`, 11 tests pass). First version: estimated recall 78% (below the 90% target), because Reddit replies about "search" often never say "photo". Forum sources now pass on a photo word or a retrieval word. Estimated recall is now about 96%, weighted for the sample's 2:1 over-sampling of passed items. **This is optimistic**: the rule was tuned on the same labels it is measured on, and only 45 relevant items exist in the sample. Precision is about 20%, as expected for a cheap first pass. Pass rates now: Google Community 96%, Reddit 92%, YouTube 72%, App Store 18%, Play 10%.

**Also noted:** the estimate that only about 15% of items are retrieval-related matches the plan's 10% assumption. Deletion and recovery complaints (11%) are nearly as common as search complaints, which supports keeping "not a search problem" as a separate family.

### Phase 2 result: relevance classifier built and measured

Built: `src/engine/llm.py` (paced Gemini client that stops on a daily-quota error and never bills), `src/engine/relevance.py` (batches of 20, JSON-schema output, returns `language` and `problem_family`), `src/engine/evaluate.py`, `prompts/relevance.md` (definitions are injected from `config/taxonomy.yaml`). Commands: `relevance-eval` (score against the labels) and `relevance-run` (classify everything that passed the keyword filter; saves every 100 items and stops cleanly if the daily quota runs out).

Measured on all 300 labeled items (`eval/results/`, prompt versions kept):

| Run | Model | Precision | Recall | 8-way agreement |
|---|---|---|---|---|
| v1 prompt | gemini-3.5-flash-lite | 62% | 96% | 75% |
| **v2 prompt (chosen)** | **gemini-3.5-flash-lite** | **72%** | **96%** | **80%** |
| v2 prompt | gemini-3.5-flash | 84% | 84% | 89% |

Targets were recall of at least 90% and precision of at least 70%; the chosen setup meets both. `flash-lite` is used for the relevance step because it favours recall, and every kept item is re-judged by the extraction step later. `flash` is reserved for extraction. The v2 prompt was written after reading the v1 errors on the same labels, so **these figures are optimistic**; the real test is a fresh, unseen sample (label about 100 new items from the full run, ideally by a human, before quoting accuracy). What the model still gets "wrong" is mostly borderline cases where my labels are debatable: layout complaints, praise that mentions search, and replies in Messages threads.

Free-tier usage: about 70 requests in one session on `flash-lite` and 15 on `flash`, no rate or daily-quota error. The real daily limit is still unmeasured.

**YouTube rework (done).** The first pull ranked videos by comment count and surfaced deletion-recovery and browser-settings clickbait (0 of 72 sampled comments about finding photos). The collector now takes videos in search-relevance order, requires a photo word and a retrieval topic word in the title, excludes recovery/cookie/Shorts titles, skips non-English videos, and needs only 5 comments per video. Result: 14 on-topic videos (Ask Photos, Takeout metadata, digitizing old photos, iPhone Visual Lookup), 247 new comments, 18 classified relevant (7%) versus 0% before, and Romanised-Hindi comments fell from 35 in the old pull to 2. The supply is small: only about 14 qualifying videos exist for these queries, so YouTube will stay a minor source.

**Whole corpus through the pipeline (1,101 items):** 493 passed the keyword filter and were classified. English results: 120 search_or_retrieval, 90 deletion_or_corruption, 26 backup_or_sync, 13 billing_or_storage, 9 quality_or_editing, 3 account_or_access_loss, 189 other. Relevant by source: Google Community 41, Reddit 38, YouTube 19, App Store 12, Play 10.

**Next: Phase 3, the extraction pilot.** Design the JSON schema, run about 200 of the 120+ relevant items (plus deletion and backup items for the "not a search problem" comparison) through `gemini-3.5-flash`, validate quotes verbatim, and hand-check.

---

## Phase 3: Extraction pilot

**Goal:** get a stable, trustworthy extraction schema and taxonomy on a small set before scaling.

**Tasks**
1. Write `prompts/extraction.md` and the JSON schema (`architecture.md` section 5); implement the extractor with structured output.
2. Implement the validator (verbatim quote check, enum check, required fields), retry, and `needs_review`.
3. Run on about 250 relevant items. Hand-label 100 of them (`failure_mode`, `outcome`, `photo_type`, and cues) into `eval/labeled_extraction.jsonl`.
4. Compare model vs. human; list disagreements; update taxonomy and prompt. Bump to `taxonomy_version: v1`.
5. Re-run the same 100 items twice to measure stability.
6. Review where `failure_mode` is `not_a_search_problem` or `cue_mismatch`; decide whether either needs splitting.

**Deliverables:** extractor, validator, evaluated pilot, taxonomy v1.

**Exit criteria:** at least 85% agreement on the three key fields; 100% verbatim quotes; at least 90% stability on re-run; taxonomy has no category with fewer than 3 items or "other" above 15% of items.

**Risks:** short reviews yield sparse cues (expected; report cue coverage honestly, and rely on Community/Reddit for cue analysis); schema too complex (drop fields with under 20% fill rate before scaling).

### Phase 3 status: built and measured; exit criteria only partly met

**Built:** `prompts/extraction.md`, `src/engine/extract.py` (JSON-schema output, batches, a validator that rejects any quote that is not verbatim in the item's own text, one retry with the error fed back, then `needs_review`), `src/engine/pilot.py` (pool, sample, run, evaluate). Runs are resumable: results are saved after every batch and a re-run continues where a free-tier quota stopped it. Commands: `extract-sample`, `extract-run [--pool sample|pilot] [--model] [--batch] [--save-db] [--out]`, `extract-eval`. 21 tests pass.

**Gold set.** I labeled 100 items (`eval/labeled_extraction.jsonl`; originals kept in `..._original.jsonl`) **before** running any model, so the labels are single-rater model judgments, not human ground truth. Two outcome labels were changed afterwards by an explicit rule ("the person says they cannot find what they want" is `not_found`), documented in each row's notes. Taxonomy went to **v1**: a new failure mode `unspecified` (a difficulty finding photos with no cause given), because many posts fit nothing else, plus sharper definitions for `regression`, `not_found` and `time_loss`.

**Model choice was forced by the free tier.** `gemini-3.5-flash` and `gemini-2.5-flash` each allow only **20 requests per day** (measured; sources had said 250 or more), which cannot cover thousands of items. The newest models (3.6, 3.8) returned "high demand" errors and `3-flash-preview` truncated its output. So extraction uses `gemini-3.5-flash-lite`, the only reliable free option with real quota (over 135 requests in one day, limit not reached).

**Results on the 100-item gold set** (three prompt versions, same model; the last version's prompt was tuned after reading earlier errors on the same labels, so scores are optimistic):

| Measure | v1 prompt | v2 | **v3 (final)** | Target |
|---|---|---|---|---|
| failure_mode agreement | 68% | 73% | **77%** | 85% |
| outcome agreement | 80% | 82% | **85%** | 85% |
| photo_type agreement | 88% | 86% | **86%** | 85% |
| severity agreement | 60% | 58% | 67% | (not gated) |

Extra measures for v3: "is this a retrieval failure at all" (failure_mode is not `not_a_search_problem`) agreement 83%, precision 79%, recall 73% on 37 gold positives; among items both call a retrieval failure the exact failure_mode matches 21 of 27 (78%); photo_type where the gold is not `unknown` matches 15 of 22 (68%; 78% of gold items are `unknown`, so the headline figure is mostly easy cases); cues as (type, status) pairs: precision 62%, recall 71%, but on only 7 gold cues. Stability across three identical runs: failure_mode 89%, outcome 92%, photo_type 94 to 96%.

**Exit criteria**

| Criterion | Result |
|---|---|
| At least 85% agreement on failure_mode | **Not met** (77%) |
| At least 85% on outcome | Met, barely (85%) |
| At least 85% on photo_type | Met, but see the caveat above |
| 100% of stored quotes verbatim | **Met** (enforced; 2 of 190 pilot items never validated and went to `needs_review`) |
| At least 90% stability | failure_mode **89%** (just short), outcome and photo_type met |
| No taxonomy category under 3 items, `other` under 15% | **Not met** (see below) |

**The pilot pool (190 items, 188 stored).** failure_mode: not_a_search_problem 129, unspecified 22, regression 13, identity_failure 13, missing_wrong_metadata 4, vocabulary_mismatch 3, not_indexed 2, ranking_failure 1, cue_mismatch 1; content_type_gap and scale_or_speed 0. outcome: unclear 153, not_found 33, found 1, switched_product 1. photo_type: unknown 140. So 5 of 11 failure modes have fewer than 3 items, which is too little data to support that many categories; the fine categories should be grouped at analysis time until the full run shows more.

**Important finding: people almost never say what they remember or forgot.** The extractor produced only **16 cue mentions from 188 items** (appearance 8, when 7, where 1) and **zero "forgotten" cues**; there were no who, event or provenance cues at all. A direct text scan of the 120 relevant items confirms it is not an extractor miss: only 3 mention not remembering something and only 2 mention a remembered detail or year. Reviews, forum posts and replies describe the symptom ("search doesn't work") and rarely the memory behind it. This bears directly on the project's core questions about what people remember, forget and how they search with incomplete memory. See the decision below.

**Decision needed before Phase 4:** (a) run the full extraction as is, and report the memory-cue findings as sparse and mostly qualitative; (b) add narrative-rich sources aimed at those questions (for example genealogy and old-photo communities, long Reddit posts), which needs Tier-2 access and Apify budget; (c) a mix. My recommendation is (c): run Phase 4 now on the current corpus, and separately test one or two narrative-rich sources on a small sample to see whether they contain memory cues.

---

## Phase 4: Full run

**Goal:** collect and extract at the scale needed for comparison.

**Tasks**
1. Run all collectors at full volume per `retrieval plan.md` sections 4 and 8, in order of cost and risk (App Store, Play, YouTube, communities, Reddit). Check each source's coverage report as it lands.
2. Run pre-filter and relevance classifier over everything; keep counts by `problem_family`.
3. Run extraction in batches of about 5 items per request through the free-tier rate limiter; record requests used per day in `runs`. Expect this to take 3 to 5 days because of daily quotas; the job stops when the quota is used and resumes the next day.
4. Spot-audit 50 random extractions across sources; fix systematic issues and re-extract only the affected rows.
5. Balance check: confirm no single product exceeds about 60% of the corpus; collect more from underrepresented products if needed.

**Deliverables:** populated database with 2,000 to 4,000 validated extractions and `cue_mentions`.

**Exit criteria:** target volume reached or shortfall explained; validator failures below 5% of items; audit agreement at least the Phase 3 level.

**Risks:** free-tier quota smaller than expected (shrink volume, add Groq for the relevance step, never pay); Apify credit exhausted (collect the rest next billing month); Reddit or Apify throttling (spread the run over several days).

### Phase 4 status (2026-09-21): run done except 18 items; volume target missed by supply, not budget

**The funnel.**

| Stage | Count |
|---|---|
| Raw items collected (7 sources) | 5,640 |
| Passed the keyword filter and classified by Gemini | 1,951 |
| Classified as search_or_retrieval | 740 |
| Extracted (all relevant items plus 70 comparison items) | 872 |
| Extracted items that are real retrieval failures (failure_mode not `not_a_search_problem`) | **287** |

Per source (raw, relevant, extracted, retrieval failures): Google Community 726, 204, 273, 102; Reddit 903, 193, 222, 65; Play 2,300, 58, 61, 41; App Store 633, 44, 47, 32; Hacker News 456, 155, 165, 27; Stack Exchange 158, 66, 71, 15; YouTube 464, 20, 33, 5.

**Volume target (2,000 to 4,000 extracted) was not met, and more spend would not fix it.** Play and App Store are about 90% praise or generic noise; YouTube has only about 20 qualifying videos; Reddit's search returned few posts (43 posts from 48 searches even with a higher per-search cap). Apify shows about $0.9 of the $5 credit used, so budget is not the limit. Supply of on-topic public posts is. The 287 real retrieval failures are the analysable core.

**Things changed in this phase**
- **Reddit:** searches yield little. The collector now also supports "listing mode" (top posts of the year per subreddit, filtered by keywords in the actor), which returned 542 items for about $0.35 against 106 for the search route. Both are in `reddit.py` (`--listing`, `--skip`).
- **Two narrative-source tests** (as agreed, option c): Stack Exchange (official API; 158 questions across photo, apple, webapps, superuser, android, genealogy; 10-year window because most matching questions are old) and Hacker News (Algolia API; 456 comments). Result below.
- **Extraction prompt v4** added two rules: hypothetical or example searches are not cues, and praise is never `found`. On the gold set: failure_mode 75% (v3: 77%), outcome 83% (85%), photo_type 87% (86%), cue precision 83% (62%). Score changes are within run-to-run noise (stability 89 to 92%); cue precision improved clearly. The whole corpus was re-extracted with v4 so the database uses one prompt version; 18 items in the pool are still v3 and finish when the quota resets (re-run `extract-run --pool full --save-db --out eval/results/extract_v4_full.json`), and 58 older items outside the current pool keep their v3 records.
- **Free-tier quotas measured:** `gemini-3.5-flash-lite` allows **500 requests per day** (hit it after about 115 extraction requests on top of about 385 earlier the same day); `gemini-3.5-flash` and `gemini-2.5-flash` allow 20 per day. Google resets quotas at midnight Pacific, roughly 12:30 pm IST. The Gemini client now also retries dropped connections.

**Spot-audit (50 random extractions, read by Claude, not a human).** failure_mode correct in about 47 (94%), outcome about 45 (90%). The errors: a Chrome keyboard-shortcut question labeled a photo problem, `found` given to praise, and junk cues extracted from off-topic Hacker News comments (the reason for the v4 rules). Failures of the relevance step are caught downstream: off-topic items that the classifier marked relevant (for example a comment about NPU chips) come out of extraction as `not_a_search_problem`, which is why "retrieval failure" is defined from the extraction, not the classifier.

**Balance check.** Google Photos is 57% of classifier-relevant items with a known product (51% of the 287 retrieval failures), just under the 60% guideline. Apple Photos 15%, Amazon Photos 7%, OneDrive, Ente and Immich a few each; Dropbox and Samsung Gallery almost nothing. Non-Google findings rest on small numbers. `product_mentioned` is free text ("Google Photos" and "google_photos" both appear), so it must be normalised in Phase 5.

**Answer to the narrative-source test (memory cues per extracted item):** Hacker News 0.44, Stack Exchange 0.17, Google Community 0.11, App Store 0.13, Reddit 0.09, Play 0.02, YouTube 0.00. The Hacker News figure is misleading: a read of sampled cues shows most are hypothetical examples of what one could search for ("cat on a red car", "brown dog"), not memories about a specific photo. Stack Exchange cues are more real but many are just photo metadata being described (a date taken, a file name). Overall there are 141 cue mentions across 872 items and **only 3 "forgotten" cues, all "when" and all from Hacker News** ("I can't always remember when we went somewhere"). Three anecdotes fit the hypothesis that people recall what and who but not when, but they are far too few to call a finding.

**Conclusion for the discovery questions:** the public corpus can describe what kinds of retrieval failures exist (287 items, fairly well), but it cannot say what people remember or forget with any confidence. Narrative sources do not fix this. Answering "what have they forgotten" needs primary research (a short survey or interviews asking people to describe a photo they could not find), which the engine can then help analyse with the same schema.

**Exit criteria:** validator failures 6 of about 880 (0.7%, target under 5%) met; audit agreement at least Phase 3 level, met on my read; volume target not met (supply-limited, explained above); balance guideline met narrowly.

Next was Phase 5, clustering and comparison on the 287 retrieval failures, grouping the 11 failure modes into fewer categories because several have fewer than 10 items.

### Phase 5 status (2026-09-21): done; results in `eval/results/clusters.md` and `clusters.json`

**Method.** The 287 retrieval failures were first grouped by failure mode into six groups (regression, identity, metadata, search quality, unspecified, scale and content), because several of the ten modes have under 10 items. Inside each group, a "problem signature" (thread title plus the extractor's one-line description) was embedded locally with `all-MiniLM-L6-v2` and clustered with Ward agglomerative clustering (about one cluster per 18 items). Gemini `flash-lite` then named and defined each cluster. Average linkage was tried first and collapsed into one giant cluster per group, so Ward replaced it. Commands: `cluster-build`, `cluster-audit`, `cluster-apply-audit`, `cluster-report`. Code: `src/engine/cluster.py`.

**Human check (single model rater, 10 random items per cluster, pass at 8 of 10).** Of 15 first-pass clusters, 7 passed. Two had coherent items but wrong or too narrow names (renamed); four were near-duplicates or mixed and were merged into a sibling; two were too mixed to rank and are kept as "[residual]" clusters. The actions are recorded in `eval/cluster_audit.json` and applied by `cluster-apply-audit`. A fresh re-check of the four changed clusters gave 10/10, 10/10, 8/10 and **7/10 for cluster 5 ("Update removed or rearranged browsing features")**, a borderline fail: two of its ten items are off-topic Hacker News and Stack Exchange comments that the extractor should have set aside. It stays ranked, flagged. Of the nine ranked clusters, eight pass and one is borderline.

**The nine ranked clusters (score is a judgment-based weighted sum; see the rule below).**

| # | Score | Cluster | Items | Threads | Sources | Not found | Workaround |
|---|---|---|---|---|---|---|---|
| 8 | 0.82 | Search returns nothing, wrong or irrelevant results | 59 | 53 | 6 | 73% | 14% |
| 5 | 0.48 | Update removed or rearranged browsing features (borderline) | 39 | 32 | 7 | 49% | 8% |
| 14 | 0.43 | General difficulty locating media | 14 | 14 | 3 | 86% | 0% |
| 3 | 0.42 | Finding and ordering photos by metadata | 25 | 24 | 7 | 56% | 8% |
| 12 | 0.39 | Broken search and error messages | 27 | 23 | 6 | 48% | 0% |
| 1 | 0.35 | People and face recognition, grouping and naming problems | 40 | 29 | 4 | 30% | 10% |
| 11 | 0.29 | Missing old photos and screenshots | 20 | 17 | 3 | 70% | 0% |
| 6 | 0.22 | Broken keyword and image search | 13 | 12 | 4 | 46% | 0% |
| 4 | 0.16 | AI (Gemini) search replaced or worsened classic search | 23 | 15 | 4 | 35% | 9% |

260 of 287 failures (91%) sit in a ranked cluster; 27 are in the two residual clusters. Every ranked cluster has a definition and at least 3 quotes from at least 2 sources (checked in code).

**Ranking rule.** Five measures scaled 0 to 1 across the ranked clusters, weighted: frequency (distinct threads) 35%, spread (number of sources) 15%, severity 20%, underserved (share not found times share with no workaround) 20%, recency (share from the last six months) 10%. The weights are a judgment. **Sensitivity:** cluster 8 ranks first under three of four weightings (default, equal, frequency only) and second under "underserved and severity only", where cluster 14 is first; clusters 5, 14 and 3 fill the next places. The top of the list is stable; the middle order is not.

**What the data says about your questions (with the caveats that the sample is public reviews and forum posts, skewed to Google Photos, and counts are mentions, not prevalence):**
- **What kinds of old photos?** The data can barely answer. Of the 287 failures, only 98 (34%) state a photo type and only 18 (6%) state a photo age. Photo types stated: people or pets 53, screenshots 17, migrated libraries 12, early digital 8, received or forwarded 7, scanned prints 1. Old and scanned photos are too rare here to characterise.
- **What do people remember?** 85 remembered-cue mentions among the failures (an earlier draft of this line said 87), mostly appearance (31, largely example searches), where (16), when (12), who (10). See caveats in Phase 4.
- **What have they forgotten?** One cue in total (a "when"). Not answerable from this corpus.
- **How do they search with incomplete memory?** Search pattern is stated in only 70 of 287 failures: descriptive 38, time anchor 12, broad-then-browse 7, vocabulary mismatch 6. Only 34 quote a query they typed. Workarounds appear in 21 (7%), so almost nobody reports a fix.
- **Which problems dominate?** Search that returns nothing or the wrong thing (clusters 8, 12, 6, 4 together are 122 items, 43%), followed by features removed or rearranged in updates and metadata problems. Face and people features are the most recent (95% of items from the last six months).

**Caveats to carry into the report:** the failure-mode groups inherit the extractor's roughly 75% agreement with my labels; "unspecified" clusters may hide regressions; a popular thread inflates an item count, which is why threads are shown; and non-Google products rest on very few threads. Exit criteria are met, with the cluster-5 flag.

**Correction found in Phase 6.** The three "forgotten" cues were described above as anecdotes that fit the when-is-forgotten hypothesis. On reading the source comments, one is a hypothetical example query in a discussion of AI search ("Which Christmas, hell I don't know"), one is indirect, and only one is a clear first-person statement. The evidence is therefore one clear case, not three. Also, with products normalised, Google Photos is 171 of the 287 failures (60%), not the 51% quoted above.

### Phase 6 status (2026-09-21): done

**Built.** `app/explorer.py` (Streamlit): Overview (funnel and sortable ranking with the score rule and its sensitivity), Problem clusters (definition, metrics, source and product mix, linked quotes, member items), Remember and forget (cue table, the three forgotten cues, search patterns, queries typed), Compare (cluster by product or source heatmap), Hypotheses (verdict and live numbers for all seven), and Items (filters, text search, drill-down to the original post and the extraction record). `src/engine/findings.py` computes the hypothesis evidence so the app and the report share one source. The findings report is `docs/report.md`.

**Tested in a real browser** (headless Chromium driven by Playwright, screenshots read): every view loads with no exceptions or console errors. Two real bugs were found and fixed this way: typing in the Items filter jumped back to the first tab (Streamlit tabs reset on rerun; replaced with a persistent view selector), and the heatmap dropped labels (flipped so long cluster names read horizontally). Run it with `PYTHONPATH=src streamlit run app/explorer.py` from the project root.

**Report checks.** All 32 quotes in the report were verified programmatically to appear word for word in the linked post. Every number was recomputed from the database; five errors in the first draft were caught and fixed (85 remembered cues among failures, not 87; 138 across all extractions; Apify spend about $0.80, not $0.90; Google Photos is 60% of failures, not about half; a false statement that nobody reports a working fix).

**Exit criteria.** Each of the four discovery questions has an answer backed by counts and at least three linked quotes; all seven hypotheses have a verdict (1 tentatively supported, 2, 4 and 6 not supported, 3 and 5 inconclusive, 7 strongly supported); the report states its limitations before its findings. Met.

**What the project can and cannot answer (details in the report).** It characterises the kinds of retrieval failure and ranks them: search that returns nothing or the wrong thing leads, followed by updates that remove or rearrange browsing, and two thirds of "can't find my photos" complaints are not search problems at all. It cannot answer what people remember or forget (one clear "forgotten" statement in the whole corpus) or say much about old photos as such (6% of failures state an age). Those two need primary research.

**Insight layer (added after Phase 6, on the user's feedback that the Explorer felt like a data dump).** `src/engine/insights.py` finds contrasts in the data with code (a cluster that differs sharply from the rest on a source, an outcome, a cue or a change-of-behaviour signal), attaches the numbers and verbatim quotes, and sets a confidence level from sample size and effect size. A model only writes the wording; its text is rejected if it contains a number not in the facts or wording that overclaims, and a second pass checks it against the facts. Weak signals are shown as plain notes with no model text. The Explorer opens on these cards, and the same 7 key and 3 weaker insights are inserted at the top of `docs/report.md`. Limit: the "Interpretation" line on each card is a model's guess at why, labelled as a hypothesis to test; only the counts, contrasts and quotes are findings.

### Phase 7 status (2026-09-21): done

**Built.** `engine refresh` (`src/engine/refresh.py`) collects only what is new (each source is asked for items newer than its newest stored item minus 3 days; YouTube also reads the newest comments of videos already known), then runs the keyword filter, relevance classifier and extraction on only the new items, places new failures in the closest existing cluster, records the run, and prints what was added. Every stage skips work already done, so it can be repeated or resumed after a quota stop. Reddit is off unless `--reddit` is given, because it is the only source that uses Apify credit. `engine regress` (`src/engine/regress.py`) re-runs the relevance classifier and the extractor on the labeled sets and compares with `eval/baseline.json`, failing if any metric drops more than 5 points (about 30 free requests). Every relevance, extraction and cluster run now stores the taxonomy version and the prompt hashes (`store.versions()`). `README.md` covers setup, keys, commands, the free-tier limits and how to add a source.

**Tested.** 28 unit tests pass. On the real database a refresh added 115 items, of which 79 needed classifying, 5 were relevant, 3 were failures and all 3 were placed in clusters; an immediate second refresh found nothing new to extract. In a fresh copy of the project (no `data/`, only the `.env` keys) `refresh --sources appstore,hackernews` built the database and ran the whole pipeline (498 items, 143 relevant, 30 failures); a second refresh added only 4 comments not already stored. The fresh copy used the same Python environment, not a new virtual environment, so `requirements.txt` itself was not installed from scratch.

**Known limits.**
- Placing a new failure in a cluster is approximate: holding out each existing item in turn puts it back in its own cluster 63% of the time, and the similarity cut-off barely changes that. Rebuild and re-audit the clusters when the themes may have changed.
- A `since` refresh only sees what the source's list returns for that window. Sources that rank by relevance (YouTube search, Hacker News) can surface older items that were missed before, so a refresh can add a few items dated before the last run.
- The regression baseline is scored against Claude-made labels on which the prompt was tuned, so it catches breakage, not true accuracy.
- `docs/report.md` is a snapshot from the first full run; the Explorer shows the live database, which now has a few more items.

---

## Phase 5: Clustering and comparison

**Goal:** turn extractions into named problems that can be compared on shared dimensions.

**Tasks**
1. Structured grouping on `failure_mode` x `photo_type` x cue-mismatch (`architecture.md` 3.8).
2. Generate a problem signature per item; embed locally; sub-cluster with HDBSCAN.
3. Name and define each cluster with the model; require cited member ids and 3 to 5 representative quotes.
4. Compute the metrics in `architecture.md` 3.9 with SQL.
5. Human-check 10 random items per cluster; merge, split, or drop clusters that fail (8 of 10 rule).
6. Build the remember-vs-forget tables (cue type x status) overall and by photo type.
7. Rank opportunity areas using frequency, severity, spread, and underserved score; document the ranking rule so it can be criticized.

**Deliverables:** cluster tables, metrics, remember-vs-forget tables, ranked opportunity list.

**Exit criteria:** every cluster has a name, a definition, at least 3 quotes from at least 2 sources; at least 80% of relevant items belong to a cluster; ranking rule written down.

**Risks:** clusters dominated by one product (compare per-product cluster mix; report as a finding, not a defect); too many tiny clusters (raise the minimum cluster size).

---

## Phase 6: Explorer and findings report

**Goal:** make the results explorable and answer the questions in the problem statement.

**Tasks**
1. Build the Streamlit Explorer: cluster list with sortable metrics; cluster detail with quotes and links; remember-vs-forget view; product/source comparison; item drill-down.
2. Write `report.md` answering, with linked quotes:
   - What kinds of old photos do users struggle to retrieve? (photo-type distribution and clusters)
   - What information do people remember? (remembered cue frequencies)
   - What information have they forgotten? (forgotten cue frequencies)
   - How do users formulate searches with incomplete memory? (search pattern and workaround distribution)
   - Which problems and opportunity areas rank highest, and how do they compare?
3. Re-test the hypotheses in `context.md` section 10; mark each as supported, contradicted, or inconclusive with the evidence.
4. State limitations up front: selection bias, platform skew, sample sizes, taxonomy version.

**Deliverables:** Explorer app, `report.md`.

**Exit criteria:** each of the four discovery questions has an answer backed by counts and at least 3 linked quotes; every hypothesis has a verdict; the report states its limitations.

**Risks:** findings look obvious (report what is surprising or contradicted, not just confirmation); overclaiming prevalence (use "mentions in sample" wording).

---

## Phase 7: Hardening (done; see status above)

**Goal:** make the engine re-runnable, so it counts as a discovery *system* and not a one-off analysis.

**Tasks**
1. Add incremental collection (only new items since the last run) and a single `engine refresh` command.
2. Record every stage's inputs, model, prompt and `taxonomy_version` per run.
3. Write a short README: setup, keys, commands, cost expectations, how to add a source.
4. Keep the `eval/` set and add a regression check that runs on prompt or taxonomy changes.

**Exit criteria:** a fresh clone plus keys can reproduce a small run end to end; a refresh run adds only new items.

---

## Cross-phase rules

- **Compliance is checked before each new source, not after.**
- **Spend is $0.** Billing is never enabled on any provider. Requests used per day are logged per run; when a free quota is exhausted, the job stops and resumes later, or the volume is reduced.
- **Every taxonomy or prompt change bumps the version** and triggers re-extraction only for the affected rows.
- **Definition of done for any insight:** it names a cluster, cites its item count and source spread, and links at least 3 verbatim quotes.

## Assumptions and open decisions

- One person builds this; if two, Phases 1 and 2 can run in parallel.
- Budget is fixed at $0, so volumes are set by free-tier limits (see `retrieval plan.md` section 8). The free-tier numbers are unverified and will be checked in Phases 1 and 2.
- Not decided yet: whether to publish the Explorer (currently local-only), and whether findings will be shared beyond the graduation project, which affects Reddit and Apify compliance.
