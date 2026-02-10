from __future__ import annotations

import json
from pathlib import Path

import importlib.util
import sys

_SPEC = importlib.util.spec_from_file_location(
    "bug_prevention_log",
    Path(__file__).resolve().parents[1] / "tools" / "bug_prevention_log.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load tools/bug_prevention_log.py")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
log_prevention = _MODULE.log_prevention
build_parser = _MODULE.build_parser


def test_bug_prevention_log_writes_json_and_markdown(tmp_path: Path) -> None:
    json_path = tmp_path / "bug_prevention.json"
    md_path = tmp_path / "bug_prevention.md"
    parser = build_parser()
    args = parser.parse_args(
        [
            "--title",
            "Prevented regression in pipeline timing",
            "--tests",
            "tests/test_story_analysis_pipeline.py::test_pipeline_reports_stage_timings",
            "--issue-url",
            "https://github.com/ringxworld/story_generator/issues/128",
            "--prevented-count",
            "2",
            "--json-path",
            str(json_path),
            "--md-path",
            str(md_path),
        ]
    )

    log_prevention(args)

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["total_prevented"] == 2
    assert payload["entries"]
    assert md_path.read_text(encoding="utf-8").startswith("# Bug Prevention Log")
