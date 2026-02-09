# Storage Operations Runbook

Operational runbook for analysis persistence backends used in
https://github.com/ringxworld/story_generator/issues/11.

## Backend Modes

Configured via environment variables:

- `STORY_GEN_ANALYSIS_BACKEND=sqlite` (default)
- `STORY_GEN_ANALYSIS_BACKEND=mongo-prototype` with
  `STORY_GEN_ENABLE_MONGO_ADAPTER=1`
- `STORY_GEN_ANALYSIS_BACKEND=graph-prototype` with
  `STORY_GEN_ENABLE_GRAPH_ADAPTER=1`

Default data roots (derived from `STORY_GEN_DB_PATH`):

- SQLite: `<db_path>`
- Mongo prototype: `<db_stem>.mongo_analysis_runs.jsonl`
- Graph prototype: `<db_stem>.graph_analysis_runs.jsonl`

## Backup Procedures

SQLite:

1. Stop writers (API worker drain or maintenance window).
2. Copy DB file to timestamped backup:
   `cp work/local/story_gen.db backups/story_gen-YYYYMMDDHHMM.db`
3. Restart writers.

Mongo/graph prototype JSONL:

1. Stop writers.
2. Copy `*.jsonl` and `*.meta.json` files to timestamped backup path.
3. Restart writers.

## Restore Procedures

SQLite:

1. Stop API/CLI writers.
2. Replace target DB file with selected backup.
3. Start API and run smoke checks:
   - `GET /healthz`
   - authenticated `GET /api/v1/stories/{story_id}/analysis/latest`

Mongo/graph prototype:

1. Stop API/CLI writers.
2. Replace affected `*.jsonl` and `*.meta.json` files from backup.
3. Start API and run the same smoke checks.

## Retention Policy

- Local/dev minimum:
  - keep daily backups for 14 days
  - keep weekly backups for 8 weeks
- Shared staging:
  - keep daily backups for 30 days
  - keep monthly backups for 6 months
- Prune older snapshots only after confirming a successful newer backup.

## Rollback Policy

Rollback from prototype backends to SQLite:

1. Set `STORY_GEN_ANALYSIS_BACKEND=sqlite`.
2. Remove prototype enable flags.
3. Restart API workers.
4. Run:
   - `uv run python tools/check_contract_drift.py`
   - `uv run pytest tests/test_api_app.py`

## Validation Checklist

After any backend switch, backup restore, or rollback:

1. `uv run python tools/check_contract_drift.py`
2. `uv run pytest tests/test_story_analysis_store_factory.py`
3. `uv run pytest tests/test_api_app.py`
4. `uv run mkdocs build --strict`
