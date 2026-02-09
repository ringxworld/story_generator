# Observability

The runtime now uses two bounded observability channels:

- Rotating process logs (`work/logs/story_gen.log` by default)
- SQLite anomaly breadcrumbs (`anomaly_events` table in the API DB)

This keeps enough signal for debugging while preventing unbounded log growth.

## Runtime logging

`story-api` configures logging once per process via
`src/story_gen/adapters/observability.py`.

Environment controls:

- `STORY_GEN_LOG_LEVEL` (default `INFO`)
- `STORY_GEN_LOG_PATH` (default `work/logs/story_gen.log`)
- `STORY_GEN_LOG_MAX_BYTES` (default `5242880`)
- `STORY_GEN_LOG_BACKUP_COUNT` (default `10`)
- `STORY_GEN_ACCESS_LOG_LEVEL` (default `WARNING`)

## Anomaly store

The API persists warning/error breadcrumbs into SQLite through
`src/story_gen/adapters/sqlite_anomaly_store.py`.

Current anomaly writes include:

- analysis quality-gate failures
- malformed dashboard payload shapes

Retention controls:

- `STORY_GEN_ANOMALY_RETENTION_DAYS` (default `30`)
- `STORY_GEN_ANOMALY_MAX_ROWS` (default `10000`)

Pruning runs on API startup so stale/overflow rows are removed automatically.
