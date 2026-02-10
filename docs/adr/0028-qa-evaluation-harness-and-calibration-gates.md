# ADR 0028: QA Evaluation Harness and Calibration Gates

## Status

Accepted

## Problem

Pipeline quality checks lacked a dedicated fixture-driven evaluation harness that
could assert stage-level regressions on realistic narrative inputs. CI also did
not publish a durable QA artifact showing alignment/confidence drift over time.

## Non-goals

- Replacing deterministic rule-based pipeline stages with model-backed systems.
- Introducing external QA services or online benchmarking dependencies.
- Altering API authentication or storage contracts for production story data.

## Public API

New public CLI surface:

- `story-qa-eval`
  - Runs fixture-driven QA evaluation.
  - Supports strict failure mode and JSON summary output path.

Repository-level quality workflow updates:

- CI executes `story-qa-eval --strict`.
- CI uploads `work/qa/evaluation_summary.json` as a build artifact.
- Pre-push checks execute strict QA evaluation gate.

## Invariants

- QA fixtures are versioned and stored in-repo.
- Harness computes and records per-segment translation alignment scores.
- Harness computes and records per-case segment language distributions (counts,
  detected languages, non-target-language share) for multilingual regression
  visibility.
- Strict mode fails when fixture expectations or calibration thresholds fail.
- Fixture corpus always includes:
  - mixed-language/code-switch translation cases
  - at least one adversarial chronology case
  - at least one hard-negative calibration case
- Calibration thresholds are evaluated against explicit positive/negative fixture
  splits and surfaced in summary output.

## Test plan

- Add unit tests for evaluation harness pass/fail behavior and fixture coverage.
- Add regression tests for language-distribution expectation failures.
- Add CLI entrypoint tests for QA evaluation command output.
- Extend project contract tests for:
  - Makefile QA target
  - CI QA harness + artifact upload step
  - QA docs presence
- Run full repository gates:
  - import/contract checks
  - lint/format/type checks
  - pytest
  - strict canary + strict QA evaluation
  - docs build and frontend checks
