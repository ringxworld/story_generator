from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from story_gen.cli.qa_evaluation import run_evaluation
from story_gen.core.pipeline_evaluation import load_fixture_suite

FIXTURE_PATH = Path("tests/fixtures/story_pipeline_eval_fixtures.v1.json")


def test_fixture_suite_includes_required_coverage_cases() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["fixture_version"] == "story_pipeline_eval.v1"
    cases = payload["cases"]
    assert any("mixed-language" in case["tags"] for case in cases)
    assert any("code-switch" in case["tags"] for case in cases)
    assert any("adversarial" in case["tags"] for case in cases)
    assert any("hard-negative" in case["tags"] for case in cases)
    beat_case = next(case for case in cases if case["case_id"] == "beat_gold_stage_coverage_v1")
    assert beat_case["expectations"]["expected_beat_stage_sequence"] == [
        "setup",
        "escalation",
        "climax",
        "resolution",
    ]


def test_qa_evaluation_harness_passes_default_fixture(tmp_path: Path) -> None:
    output = tmp_path / "evaluation-summary.json"
    summary = run_evaluation(fixtures_path=FIXTURE_PATH, output_path=output, strict=True)
    assert summary["status"] == "passed"
    assert output.exists()
    cases = cast(list[dict[str, Any]], summary["cases"])
    assert cases
    assert all("alignment_scores" in case for case in cases)
    assert all(case["alignment_scores"] for case in cases)


def test_qa_evaluation_harness_fails_on_alignment_regression(tmp_path: Path) -> None:
    mutated = tmp_path / "fixtures.json"
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload["cases"][0]["expectations"]["min_alignment_mean"] = 1.01
    mutated.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    output = tmp_path / "evaluation-summary.json"
    summary = run_evaluation(fixtures_path=mutated, output_path=output, strict=False)
    assert summary["status"] == "failed"
    with pytest.raises(SystemExit):
        run_evaluation(fixtures_path=mutated, output_path=output, strict=True)


def test_fixture_loader_rejects_missing_cases(tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text(
        '{"fixture_version":"story_pipeline_eval.v1","cases":[],"calibration":{}}', encoding="utf-8"
    )
    with pytest.raises(ValueError):
        load_fixture_suite(broken)
