"""Central registry for schema and pipeline contract tracking."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, model_validator

from story_gen.api.contracts import ContractModel
from story_gen.core.pipeline_contracts import registered_pipeline_stage_contracts
from story_gen.core.story_schema import STORY_SCHEMA_VERSION

REGISTRY_VERSION: Literal["contract_registry.v1"] = "contract_registry.v1"
STORY_BLUEPRINT_SCHEMA_VERSION: Literal["story_blueprint.v1"] = "story_blueprint.v1"
ESSAY_BLUEPRINT_SCHEMA_VERSION: Literal["essay_blueprint.v1"] = "essay_blueprint.v1"
STORY_ANALYSIS_RUN_SCHEMA_VERSION: Literal["story_analysis_run.v1"] = "story_analysis_run.v1"
DASHBOARD_SCHEMA_VERSION: Literal["dashboard_read_model.v1"] = "dashboard_read_model.v1"


class SchemaContractRecord(ContractModel):
    """One schema contract tracked in the registry."""

    contract_id: str = Field(min_length=3, max_length=140)
    schema_version: str = Field(min_length=3, max_length=120)
    model_path: str = Field(min_length=3, max_length=240)
    category: Literal["schema", "request", "response", "artifact"]
    owner: Literal["api", "pipeline"]
    description: str = Field(min_length=1, max_length=300)


class PipelineStageContractRecord(ContractModel):
    """Stage-level pipeline contract registry entry."""

    stage_id: str = Field(min_length=3, max_length=140)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    validator_functions: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1, max_length=300)


class ContractRegistrySnapshot(ContractModel):
    """Versioned snapshot for all tracked schema and pipeline contracts."""

    registry_version: Literal["contract_registry.v1"] = REGISTRY_VERSION
    schema_contracts: list[SchemaContractRecord] = Field(default_factory=list)
    pipeline_stage_contracts: list[PipelineStageContractRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> ContractRegistrySnapshot:
        schema_ids = [record.contract_id for record in self.schema_contracts]
        if len(schema_ids) != len(set(schema_ids)):
            raise ValueError("Schema contract IDs must be unique.")
        stage_ids = [record.stage_id for record in self.pipeline_stage_contracts]
        if len(stage_ids) != len(set(stage_ids)):
            raise ValueError("Pipeline stage IDs must be unique.")
        return self


def _schema_contracts() -> list[SchemaContractRecord]:
    return [
        SchemaContractRecord(
            contract_id="story.blueprint",
            schema_version=STORY_BLUEPRINT_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.StoryBlueprint",
            category="schema",
            owner="api",
            description="Canonical editable story blueprint contract.",
        ),
        SchemaContractRecord(
            contract_id="essay.blueprint",
            schema_version=ESSAY_BLUEPRINT_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.EssayBlueprint",
            category="schema",
            owner="api",
            description="Canonical editable essay blueprint contract.",
        ),
        SchemaContractRecord(
            contract_id="story.analysis.request",
            schema_version=STORY_ANALYSIS_RUN_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.StoryAnalysisRunRequest",
            category="request",
            owner="api",
            description="Request contract to trigger story analysis pipeline runs.",
        ),
        SchemaContractRecord(
            contract_id="story.analysis.run_summary",
            schema_version=STORY_ANALYSIS_RUN_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.StoryAnalysisRunResponse",
            category="response",
            owner="api",
            description="Run summary response for completed analysis executions.",
        ),
        SchemaContractRecord(
            contract_id="story.ingestion.status",
            schema_version=STORY_ANALYSIS_RUN_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.IngestionStatusResponse",
            category="response",
            owner="api",
            description="Ingestion job status response for polling and retries.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.overview",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardOverviewResponse",
            category="response",
            owner="api",
            description="Dashboard macro overview response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.v1.overview",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardOverviewResponse",
            category="response",
            owner="api",
            description="Versioned dashboard v1 overview response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.timeline_lane",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardTimelineLaneResponse",
            category="response",
            owner="api",
            description="Timeline lane response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.v1.timeline_lane",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardTimelineLaneResponse",
            category="response",
            owner="api",
            description="Versioned dashboard v1 timeline lane response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.theme_heatmap",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardThemeHeatmapCellResponse",
            category="response",
            owner="api",
            description="Theme heatmap response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.v1.theme_heatmap",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardThemeHeatmapCellResponse",
            category="response",
            owner="api",
            description="Versioned dashboard v1 theme heatmap response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.arc_point",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardArcPointResponse",
            category="response",
            owner="api",
            description="Arc chart point response contract.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.graph",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardGraphResponse",
            category="response",
            owner="api",
            description="Graph node/edge response contract for dashboard rendering.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.graph_export",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardGraphExportResponse",
            category="response",
            owner="api",
            description="Graph export contract used for static SVG output.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.graph_export_png",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardGraphPngExportResponse",
            category="response",
            owner="api",
            description="Graph export contract used for deterministic PNG output.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.timeline_export",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardSvgExportResponse",
            category="response",
            owner="api",
            description="Timeline export contract used for static SVG output.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.timeline_export_png",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardPngExportResponse",
            category="response",
            owner="api",
            description="Timeline export contract used for deterministic PNG output.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.theme_heatmap_export",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardSvgExportResponse",
            category="response",
            owner="api",
            description="Theme heatmap export contract used for static SVG output.",
        ),
        SchemaContractRecord(
            contract_id="dashboard.theme_heatmap_export_png",
            schema_version=DASHBOARD_SCHEMA_VERSION,
            model_path="story_gen.api.contracts.DashboardPngExportResponse",
            category="response",
            owner="api",
            description="Theme heatmap export contract used for deterministic PNG output.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.raw_segment",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.RawSegment",
            category="artifact",
            owner="pipeline",
            description="Normalized and optional translated source segment artifact.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.extracted_event",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.ExtractedEvent",
            category="artifact",
            owner="pipeline",
            description="Event extraction artifact with provenance and confidence.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.story_beat",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.StoryBeat",
            category="artifact",
            owner="pipeline",
            description="Narrative beat artifact across setup/escalation/climax/resolution.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.theme_signal",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.ThemeSignal",
            category="artifact",
            owner="pipeline",
            description="Stage-level theme trend artifact with evidence links.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.entity_mention",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.EntityMention",
            category="artifact",
            owner="pipeline",
            description="Entity mention artifact tracked across story segments.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.timeline_point",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.TimelinePoint",
            category="artifact",
            owner="pipeline",
            description="Chronology and narrative-order timeline point artifact.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.insight",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.Insight",
            category="artifact",
            owner="pipeline",
            description="Macro/meso/micro insight artifact with confidence.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.quality_gate",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.QualityGate",
            category="artifact",
            owner="pipeline",
            description="Quality gate artifact used before dashboard display.",
        ),
        SchemaContractRecord(
            contract_id="pipeline.story_document",
            schema_version=STORY_SCHEMA_VERSION,
            model_path="story_gen.core.story_schema.StoryDocument",
            category="artifact",
            owner="pipeline",
            description="Canonical end-to-end story analysis artifact document.",
        ),
    ]


def _pipeline_stage_contracts() -> list[PipelineStageContractRecord]:
    return [
        PipelineStageContractRecord(
            stage_id=stage.stage_id,
            inputs=list(stage.inputs),
            outputs=list(stage.outputs),
            validator_functions=list(stage.validator_functions),
            description=stage.description,
        )
        for stage in registered_pipeline_stage_contracts()
    ]


def build_contract_registry_snapshot() -> ContractRegistrySnapshot:
    """Build the current contract registry snapshot."""
    return ContractRegistrySnapshot(
        schema_contracts=_schema_contracts(),
        pipeline_stage_contracts=_pipeline_stage_contracts(),
    )


def serialize_contract_registry(*, indent: int = 2) -> str:
    """Serialize the registry snapshot as deterministic JSON."""
    snapshot = build_contract_registry_snapshot()
    return json.dumps(snapshot.model_dump(mode="json"), indent=indent, sort_keys=True) + "\n"
