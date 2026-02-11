# 0034 Narrative Essence Extraction Profiles

## Problem

Narrative extraction currently captures events, beats, themes, and dialogue
signals, but it does not provide structured essence profiles for:

- short fragment/scene analysis,
- character-level essence traits and consistency constraints,
- world-level essence vectors and stage-by-stage evolution.

Without these profiles, Literary DNA roadmap features around character/world
essence and generation guidance cannot be grounded in deterministic pipeline
artifacts.

## Non-goals

- Replacing existing event/entity/beat/theme extraction stages.
- Introducing non-deterministic external model providers.
- Shipping a full chapter-generation engine in this change.

## Public API

- Dashboard drilldown receives additive essence item types:
  - `essence_fragment`
  - `essence_guidance`
  - `essence_world`
  - `essence_world_stage`
  - `essence_character`
  - `essence_constraint`
  - `essence_world_alignment`
- New core extraction module:
  - `story_gen.core.essence_extraction`
  - `extract_essence_from_fragment(...)`
  - `extract_essence_from_segments(...)`

## Invariants

- Essence extraction must be deterministic for identical input text.
- Character constraints are explicit mathematical-style expressions.
- World essence includes magic/tech/culture/mystery dimensions.
- World evolution is emitted across setup/escalation/climax/resolution bins.
- Drilldown essence items always reference evidence segment identifiers.

## Test plan

- `uv run pytest tests/test_essence_extraction.py`
- `uv run pytest tests/test_story_analysis_pipeline.py`
