# ADR 0029: NLP Provider Resilience and Insight Calibration

## Status

Accepted

## Problem

Area:NLP critical issues required a stronger contract for translation resilience,
extraction fallback behavior, beat-stage quality, and insight grounding. The
previous deterministic pipeline lacked explicit provider diagnostics, actionable
degradation anomalies, and a hard rejection path for weak evidence alignment.

## Non-goals

- Introducing external hosted NLP dependencies as mandatory runtime
  requirements.
- Changing the public story analysis schema version or breaking dashboard/API
  response payload compatibility.
- Replacing deterministic fallback behavior with non-deterministic model-only
  execution.

## Public API

NLP pipeline behavior now includes:

- Configurable translation provider controls via environment:
  - `STORY_GEN_TRANSLATION_PROVIDER`
  - `STORY_GEN_LANG_ID_PROVIDER`
  - `STORY_GEN_TRANSLATION_RETRY_COUNT`
  - `STORY_GEN_TRANSLATION_TIMEOUT_MS`
  - `STORY_GEN_TRANSLATION_CIRCUIT_FAILURES`
  - `STORY_GEN_TRANSLATION_CIRCUIT_RESET_SECONDS`
- Configurable extraction provider controls via environment:
  - `STORY_GEN_EXTRACTION_PROVIDER`
  - `STORY_GEN_EXTRACTION_FORCE_FAIL`
- Optional insight style template control:
  - `STORY_GEN_INSIGHT_STYLE_TEMPLATE`

Pipeline and API diagnostics:

- Translation and extraction stages emit diagnostics with provider, fallback, and
  issue metadata.
- API anomaly sink records actionable degradation events:
  - `translation_degraded`
  - `extraction_degraded`
  - `insight_consistency_failed`

Quality gate behavior:

- Adds evidence consistency rejection reason:
  - `insight_evidence_inconsistent`

## Invariants

- Translation failures degrade gracefully through deterministic fallback and do
  not crash pipeline execution.
- Extraction provider failures degrade to deterministic fallback with confidence
  downgrade.
- Every beat retains explicit evidence segment references.
- Macro/meso/micro insight payload schema remains unchanged.
- Quality gate fails when insight evidence consistency drops below calibrated
  floor.
- NLP regression tests measure:
  - non-English translation determinism
  - extraction precision/recall and beat-stage agreement on gold inputs
  - adversarial insight consistency rejection path

## Test plan

- Add translation resilience tests with deterministic non-English corpus and
  provider-failure fallback assertions.
- Add extraction/beat gold-metric tests asserting precision, recall, and stage
  agreement thresholds.
- Add insight consistency quality-gate tests for both reject and pass paths.
- Add API-level anomaly tests verifying actionable metadata for translation and
  insight rejection degradations.
- Run full repository gates:
  - `uv lock --check`
  - `uv run python tools/check_imports.py`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy`
  - `uv run pytest`
  - `uv run mkdocs build --strict`
