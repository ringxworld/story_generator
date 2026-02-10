from __future__ import annotations

import json
from pathlib import Path

from story_gen.cli.pipeline_batch import build_arg_parser, run_pipeline_batch


def _write_chapter(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_pipeline_batch_analyzes_chapters_and_writes_summary(tmp_path: Path) -> None:
    source_dir = tmp_path / "chapters"
    source_dir.mkdir()
    _write_chapter(source_dir / "0001.txt", "Rhea found the ledger and confronted the council.")
    _write_chapter(source_dir / "0002.txt", "The city accepted the truth and began to heal.")

    output_dir = tmp_path / "runs"
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--source-dir",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "test-run",
            "--translate-provider",
            "none",
            "--mode",
            "analyze",
        ]
    )

    summary = run_pipeline_batch(args)
    assert summary.processed_chapters == 2
    assert summary.failed_chapters == 0
    assert summary.elapsed_seconds > 0
    assert summary.timing_totals

    summary_path = output_dir / "test-run" / "summary.json"
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert payload["processed_chapters"] == 2
    assert payload["failed_chapters"] == 0
    assert payload["timing_totals"]

    chapter_summary = output_dir / "test-run" / "chapters" / "0001.json"
    assert chapter_summary.exists()
