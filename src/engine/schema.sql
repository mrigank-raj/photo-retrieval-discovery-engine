CREATE TABLE IF NOT EXISTS raw_items (
  item_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  product TEXT,
  url TEXT NOT NULL,
  thread_id TEXT,
  parent_id TEXT,
  author_hash TEXT,
  created_at TEXT,
  fetched_at TEXT NOT NULL,
  title TEXT,
  text TEXT NOT NULL,
  rating INTEGER,
  helpful_count INTEGER,
  app_or_os_version TEXT,
  locale TEXT,
  content_hash TEXT NOT NULL,
  raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_raw_source_product ON raw_items(source, product);
CREATE INDEX IF NOT EXISTS idx_raw_content_hash ON raw_items(content_hash);

CREATE TABLE IF NOT EXISTS filter_results (
  item_id TEXT PRIMARY KEY REFERENCES raw_items(item_id),
  prefilter_pass INTEGER,
  relevant INTEGER,
  problem_family TEXT,
  language TEXT,
  confidence TEXT,
  model TEXT,
  run_id TEXT
);

CREATE TABLE IF NOT EXISTS extractions (
  item_id TEXT PRIMARY KEY REFERENCES raw_items(item_id),
  json TEXT NOT NULL,
  failure_mode TEXT,
  severity TEXT,
  outcome TEXT,
  photo_type TEXT,
  product_mentioned TEXT,
  confidence TEXT,
  taxonomy_version TEXT,
  model TEXT,
  run_id TEXT
);

CREATE TABLE IF NOT EXISTS cue_mentions (
  item_id TEXT NOT NULL REFERENCES raw_items(item_id),
  cue_type TEXT NOT NULL,
  cue_value TEXT,
  status TEXT NOT NULL,
  quote TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cue_type_status ON cue_mentions(cue_type, status);

CREATE TABLE IF NOT EXISTS clusters (
  cluster_id INTEGER PRIMARY KEY,
  name TEXT,
  definition TEXT,
  taxonomy_version TEXT,
  run_id TEXT,
  grp TEXT
);

CREATE TABLE IF NOT EXISTS cluster_items (
  cluster_id INTEGER NOT NULL REFERENCES clusters(cluster_id),
  item_id TEXT NOT NULL REFERENCES raw_items(item_id),
  PRIMARY KEY (cluster_id, item_id)
);

CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  stage TEXT NOT NULL,
  source TEXT,
  params_json TEXT,
  started_at TEXT,
  counts_json TEXT,
  cost_estimate REAL,
  errors_json TEXT
);

CREATE TABLE IF NOT EXISTS needs_review (
  item_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  payload_json TEXT
);
