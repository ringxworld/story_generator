# QA Evaluation Harness

The repository ships a fixture-driven quality harness for story pipeline QA.

It also ships a variant-matrix canary that runs end-to-end pipeline stages
across multilingual and multi-source inputs.

Run the canary matrix locally:

```bash
uv run story-pipeline-canary \
  --strict \
  --run-all-variants \
  --variants-file tests/fixtures/pipeline_canary_variants.v1.json \
  --matrix-output work/qa/pipeline_canary_summary.json
```

Run it locally:

```bash
uv run story-qa-eval --strict --output work/qa/evaluation_summary.json
```

`--strict` exits non-zero when any regression gate fails.

## Purpose

- Guard extraction, beat, theme/arc, timeline, and insight behavior against regressions.
- Compute and persist per-segment translation alignment scores.
- Calibrate theme and arc confidence thresholds against held-out fixtures.
- Produce one machine-readable evaluation summary artifact for CI.

## Fixture Source Of Truth

- File: `tests/fixtures/story_pipeline_eval_fixtures.v1.json`
- Version key: `fixture_version: story_pipeline_eval.v1`

The fixture corpus includes:

- Stage-coverage gold case for setup/escalation/climax/resolution beat mapping.
- Mixed-language and code-switching translation cases.
- Adversarial chronology/conflicting-entity case.
- Hard-negative theme calibration case.

## Fixture Format

Top-level fields:

- `fixture_version`: stable fixture schema/version key.
- `cases`: list of fixture cases.
- `calibration`: held-out split tags and calibration thresholds.

Each case includes:

- `case_id`: stable identifier.
- `description`: human-readable intent.
- `source_type`: `text | document | transcript`.
- `source_text`: fallback raw source input.
- `segments`: optional explicit segments for deterministic stage regression tests.
- `target_language`: translation target.
- `tags`: classification tags (for example `calibration-positive`, `hard-negative`).
- `expectations`: threshold/assertion map.

Supported `expectations` keys:

- Minimum checks:
  - `min_alignment_mean`
  - `min_alignment_min`
  - `min_event_count`
  - `min_beat_count`
  - `min_insight_count`
  - `min_translation_quality`
  - `min_timeline_consistency`
  - `min_non_story_theme_confidence`
  - `min_arc_confidence`
- Maximum checks:
  - `max_hallucination_risk`
  - `max_timeline_conflicts`
  - `max_timeline_consistency`
  - `max_non_story_theme_strength`
- Set/sequence checks:
  - `expected_beat_stage_sequence`
  - `required_beat_stages`
  - `required_theme_labels`
  - `forbidden_theme_labels`
  - `required_timeline_conflict_codes`
  - `required_insight_granularities`

## Calibration Method

Calibration uses case tags:

- Positive split: tags listed in `calibration.positive_tags`
- Negative split: tags listed in `calibration.negative_tags`

Observed metrics:

- Theme confidence floor: minimum non-story theme confidence across positive split.
- Arc confidence floor: minimum arc confidence across positive split.
- Non-story strength ceiling: maximum non-story theme strength across negative split.

Gates compare observed metrics against configured thresholds in:

- `calibration.thresholds.theme_confidence_floor`
- `calibration.thresholds.arc_confidence_floor`
- `calibration.thresholds.non_story_strength_ceiling`

## CI Artifact

CI runs the harness in strict mode and uploads:

- `work/qa/evaluation_summary.json`
- `work/qa/pipeline_canary_summary.json`

The summary includes:

- Per-case pass/fail and failure reasons.
- Per-segment alignment scores (segment id + quality score + method).
- Confidence distributions to track threshold drift over time.

## Fixture Update Process

1. Update fixture cases in `tests/fixtures/story_pipeline_eval_fixtures.v1.json`.
2. Keep at least one adversarial and one hard-negative case.
3. Run:
   - `uv run story-qa-eval --strict --output work/qa/evaluation_summary.json`
   - `uv run pytest tests/test_pipeline_evaluation_harness.py tests/test_project_contracts.py`
4. If thresholds change, document the rationale in PR notes and keep calibration tags unchanged unless the split design changes.
