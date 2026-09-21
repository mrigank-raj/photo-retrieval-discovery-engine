# Discovery Engine

Reads public feedback about photo retrieval (finding, searching and getting back photos) across app stores, forums, Q&A sites and video comments, and turns it into ranked problem areas with real user quotes as evidence. It costs nothing to run: every service used has a free tier and no billing is ever enabled.

Start with `docs/report.md` for what it found and how far to trust it. The other files in `docs/` explain the problem, the plan and the design.

## Setup

Needs Python 3.11 or newer.

```
pip install -r requirements-pipeline.txt
playwright install chromium          # only the Google Photos Community collector needs it
cp .env.example .env                 # then fill in the keys below
python -m engine.cli init-db
python -m engine.cli check-keys
```

Run every command from the project folder with `PYTHONPATH=src` set (PowerShell: `$env:PYTHONPATH="src"`).

| Key | Where to get it (free) | Used for |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio, no billing | relevance filter, extraction, cluster names, insight text |
| `YOUTUBE_API_KEY` | Google Cloud, YouTube Data API v3 | YouTube comments |
| `APIFY_TOKEN` | Apify free plan | Reddit only, and only when you ask for it |
| `AUTHOR_HASH_SALT` | any random string, set once | hashing usernames; real usernames are never stored |

Gemini's free tier allows about 500 requests a day on `gemini-3.5-flash-lite` (the model used for bulk work) and resets at midnight Pacific. A run that hits the limit stops cleanly and continues next time.

## Everyday commands

```
python -m engine.cli refresh                 # collect only what is new, classify, extract, place in clusters
python -m engine.cli insights --write-report # rebuild the insight cards and the "Key insights" block of docs/report.md
streamlit run app/explorer.py                # the Explorer; opens on the Insights view
python -m engine.cli regress                 # after changing a prompt, the taxonomy or a model
python -m pytest tests                       # unit tests, no network needed
```

**refresh** reads the newest stored date per source, goes back 3 days, and asks each source only for newer items. Anything already stored is dropped as a duplicate, so running it twice in a row adds nothing. Options: `--sources appstore,play`, `--skip-collect`, `--skip-extract`, `--reddit` (Reddit is off by default because it is the only source that spends Apify credit). It ends with a summary of what was added.

New failures are put in the closest existing cluster by embedding similarity. That is approximate: on the current data, holding out each item in turn puts it back in its own cluster 63% of the time (`cluster-assign --check`). For a real change in themes, rebuild with `cluster-build`, then `cluster-audit` and `cluster-apply-audit`.

**regress** re-runs the relevance classifier and the extractor on the labeled sets and compares with `eval/baseline.json`. It exits with a failure if any metric drops more than 5 points. It uses about 30 free requests. After an intended improvement, run `regress --update-baseline`. Each run also records the prompt and taxonomy versions in the `runs` table, so you can tell which results came from which version.

## The whole pipeline, one stage per command

| Stage | Command | Output |
|---|---|---|
| Collect | `collect play --limit 500` (sources: appstore, play, reddit, youtube, google_community, hackernews, stackexchange) | `data/engine.db` |
| Keyword filter | `prefilter` | pass/fail per item |
| Relevance | `relevance-run` | is it about finding or getting back photos |
| Extract | `extract-run --pool new --save-db` | failure mode, outcome, remembered/forgotten cues, verbatim quotes |
| Cluster | `cluster-build`, `cluster-audit`, `cluster-apply-audit` | named problem clusters |
| Insights and report | `insights`, `report` | `eval/results/insights.md`, `metrics`, `clusters.md` |

`python -m engine.cli --help` lists the rest.

## What to trust

- **Solid:** the counts, the contrasts between groups, and the quotes (every quote is checked to appear word for word in the source).
- **Hypotheses:** the "Interpretation" line on each insight card. It is written by a model and labelled as something to test, not a finding.
- **Not human-checked:** the labeled sets are judgments by Claude, and the prompt was tuned on the same labels, so the quality scores are optimistic. A person should label a fresh sample before any big decision.
- **Not the whole market:** sources skew to people who post complaints; Google Photos is about 60% of the failures found.

## Adding a source

1. Add `src/engine/collectors/<name>.py` with `fetch(cfg, limit, product_keys, since=None)` returning `(items, errors)`. Each item needs `item_id`, `source`, `url`, `created_at`, `text`; `product`, `title`, `rating`, `thread_id`, `parent_id` and `author` are optional. Authors are hashed on insert.
2. Add the source to `config/sources.yaml` with `enabled: true` and its compliance note.
3. Add it to `PLAN` in `src/engine/refresh.py`, then `python -m engine.cli collect <name>`.

## Folder map

```
config/    sources.yaml (what to collect and why it is allowed), llm.yaml (models and free-tier limits), taxonomy.yaml (failure modes)
prompts/   relevance.md, extraction.md (versioned by hash in every run)
src/engine collectors/, store, prefilter, relevance, extract, cluster, findings, insights, refresh, regress, cli
app/       explorer.py (Streamlit)
eval/      labeled sets (labels are Claude judgments), cluster audit, baseline.json, results/
docs/      problem statement, context, plans, architecture, report
data/      the SQLite database and run files (git-ignored, created on first run)
tests/     pytest
```

## Data and rules

Only public posts are read. Usernames are replaced by a salted hash on insert. Reddit goes through Apify, which is against Reddit's own rules; that was a deliberate choice and is disclosed in the report. The Apple Community site is not collected because it blocks automated access and the block is not worked around. `config/sources.yaml` records the reasoning per source.
