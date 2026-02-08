# Story Feature Pipeline

This pipeline starts from a saved story blueprint and extracts deterministic
chapter-level metrics that can later feed evaluators, drift checks, and
generation controls.

## Flow

1. Load story blueprint from storage.
2. Convert chapters to extraction inputs.
3. Extract feature rows with a versioned schema (`story_features.v1`).
4. Persist run metadata and rows to SQLite tables.
5. Query latest run for analysis or downstream generation setup.

## Current extracted features

- source length (chars)
- sentence count
- token count
- average sentence length
- dialogue line ratio
- top keywords

## Table schema (SQLite)

- `feature_schema_versions`
  - records expected schema version for feature tables
- `story_feature_runs`
  - one row per extraction run (`run_id`, `story_id`, `owner_id`, version, timestamp)
- `story_feature_rows`
  - one row per chapter within a run

## Schema enforcement best practices implemented

- strict pydantic models (`extra="forbid"`) on contracts
- explicit schema version constant (`story_features.v1`)
- startup version check against `feature_schema_versions`
- fail-fast behavior on schema mismatch
- stable field naming and typed serialization (`top_keywords_json`)
- owner-scoped read/write paths in API

## Next hardening steps

- add migration scripts for version upgrades (`v2`, `v3`, ...)
- add per-field table CHECK constraints where useful
- add semantic drift baselines keyed by schema version
