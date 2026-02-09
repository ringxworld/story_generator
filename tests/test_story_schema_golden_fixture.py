from __future__ import annotations

import json
from pathlib import Path

from story_gen.core.story_schema import StoryDocument

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "story_analysis_v1_golden.json"


def test_story_schema_golden_fixture_round_trip_serialization() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    document = StoryDocument.model_validate(payload)
    round_trip = json.loads(document.model_dump_json())

    assert round_trip == payload
