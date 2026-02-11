# 0033 Sentence and Dialogue Extraction Details

## Problem

The current story analysis pipeline extracts events and entities, but it does
not expose structured sentence-level dialogue details. That gap makes it hard
to inspect speaker consistency, internal thought signals, and narrative mode
balance across analyzed segments.

## Non-goals

- Replacing the existing event/entity extraction stage.
- Introducing non-deterministic model dependencies.
- Redesigning dashboard architecture or storage adapters.

## Public API

- Dashboard drilldown payload now includes additive extraction detail items:
  - `extraction_detail` for narrative balance summary.
  - `extraction_speaker` for attributed dialogue speaker rollups.
  - `extraction_monologue` for internal monologue signals.
- No existing endpoint is removed or renamed.

## Invariants

- Extraction remains deterministic for identical input text.
- Unknown speaker attribution falls back to `unknown` instead of failing.
- Drilldown entries always include evidence segment identifiers.
- Existing story analysis schema version remains `story_analysis.v1`.

## Test plan

- `uv run pytest tests/test_dialogue_extraction.py`
- `uv run pytest tests/test_story_analysis_pipeline.py`
