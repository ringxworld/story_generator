from __future__ import annotations

import json
from pathlib import Path

from story_gen.api.contract_registry import (
    REGISTRY_VERSION,
    build_contract_registry_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "work" / "contracts" / "story_pipeline_contract_registry.v1.json"


def test_contract_registry_snapshot_has_required_core_entries() -> None:
    snapshot = build_contract_registry_snapshot()
    assert snapshot.registry_version == REGISTRY_VERSION

    schema_ids = {record.contract_id for record in snapshot.schema_contracts}
    assert "story.blueprint" in schema_ids
    assert "essay.blueprint" in schema_ids
    assert "story.analysis.request" in schema_ids
    assert "story.analysis.run_summary" in schema_ids
    assert "dashboard.v1.overview" in schema_ids
    assert "dashboard.v1.timeline_lane" in schema_ids
    assert "dashboard.v1.theme_heatmap" in schema_ids
    assert "pipeline.story_document" in schema_ids
    assert "pipeline.timeline_point" in schema_ids
    assert "pipeline.insight" in schema_ids

    stage_ids = {record.stage_id for record in snapshot.pipeline_stage_contracts}
    assert "ingestion.translation" in stage_ids
    assert "extraction.events_entities" in stage_ids
    assert "narrative.beat_detection" in stage_ids
    assert "themes.arcs_conflicts" in stage_ids
    assert "timeline.compose" in stage_ids
    assert "insights.generate" in stage_ids


def test_exported_contract_registry_matches_runtime_snapshot() -> None:
    assert REGISTRY_PATH.exists()
    expected = build_contract_registry_snapshot().model_dump(mode="json")
    exported = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert exported == expected
