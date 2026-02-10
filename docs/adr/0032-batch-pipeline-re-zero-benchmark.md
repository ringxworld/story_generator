# 0032 Batch Pipeline and Re:Zero Benchmark

## Problem

We need a reliable, apples-to-apples benchmark for end-to-end pipeline runs
across large chapter sets. The existing canary is valuable but does not capture
translation reliability, batch throughput, or chapter-by-chapter failure modes.

## Non-goals

- Shipping or committing third-party full text into the repository.
- Changing the core pipeline architecture or schema versions.
- Adding online translation dependencies as required defaults.

## Public API

- New CLI: `story-pipeline-batch`
- Batch outputs written to `work/pipeline_runs/<run-id>/` with:
  - `summary.json` (overall timings and counts)
  - `chapters/*.json` (per-chapter analysis summaries)
  - `translated_en/*.txt` (optional translated chapter text)

## Invariants

- Batch pipeline never commits source text into the repo.
- Offline translation paths are supported via optional dependencies.
- Timing metrics are always emitted for batch runs.
- Failure in one chapter does not halt the batch unless `--strict` is set.

## Test plan

- `uv run pytest tests/test_pipeline_batch.py`
- `uv run pytest tests/test_cli_entrypoints.py -k pipeline_batch`
