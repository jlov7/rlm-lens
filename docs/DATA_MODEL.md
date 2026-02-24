# Data Model — RLM-Lens (SQLite)

This document describes the persistent model used by the backend.

## 1. Guiding principles
- Keep core tables simple and queryable.
- Store trace events in an append-only manner.
- Prefer content hashes for reproducibility.

## 2. Entities

### 2.1 Corpus
Represents a root folder and its indexing configuration.

Fields:
- `id` (cor_*)
- `name`
- `root_path`
- `created_at`
- `updated_at`
- `index_config_json`
- `last_index_job_id` (nullable)
- `last_indexed_at` (nullable)
- `last_snapshot_hash` (nullable)

### 2.2 File
One row per indexed file (latest version).

Fields:
- `corpus_id`
- `path` (relative, normalized)
- `sha256`
- `bytes`
- `mtime`
- `is_binary`
- `indexed_at`
- `language_hint` (optional)

### 2.3 File FTS
FTS5 virtual table:
- `path`
- `content`

Notes:
- store path in FTS to allow filtering / ranking adjustments
- keep `content` text only

### 2.4 IndexJob
Fields:
- `id` (job_*)
- `corpus_id`
- `status` (queued/running/succeeded/failed)
- `started_at`, `finished_at`
- `progress_json` (optional)
- `error_json` (optional)

### 2.5 Run
Fields:
- `id` (run_*)
- `corpus_id`
- `snapshot_hash` (hash of corpus manifest used)
- `status` (running/succeeded/failed/partial_budget_exceeded)
- `created_at`, `started_at`, `finished_at`
- `runtime_config_json`
- `final_answer_md` (nullable)
- `usage_json` (tokens/cost)
- `error_json` (nullable)

### 2.6 Message
Fields:
- `run_id`
- `role` (system/user/assistant)
- `content`
- `created_at`

### 2.7 Citation
Fields:
- `id` (cit_*)
- `run_id`
- `path`
- `start_line`, `end_line`
- `snippet`
- `content_hash` (hash of snippet for later resolution)

### 2.8 TraceEvent (append-only)
Fields:
- `id` (auto)
- `run_id`
- `seq` (monotonic)
- `ts`
- `type`
- `payload_json`

This is intentionally generic to allow evolving trace shapes while keeping core query ability.

### 2.9 Export
Fields:
- `id` (exp_*)
- `run_id`
- `created_at`
- `zip_path`
- `manifest_json`

## 3. Snapshot hash strategy
A snapshot hash should be computed from:
- corpus root path
- index config
- sorted list of file records: (path, sha256, bytes, mtime)

This allows replay to detect “same corpus content”.

## 4. Invariants
- A run’s citations must refer to files within its corpus root.
- A run’s snapshot hash should remain stable for that run.
- Trace event sequence numbers must be strictly increasing per run.

