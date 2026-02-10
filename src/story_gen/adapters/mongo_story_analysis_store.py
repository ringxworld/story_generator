"""Prototype document-style analysis store adapter (Mongo-like)."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from story_gen.adapters.story_analysis_store_types import LatestAnalysisPayload, StoredAnalysisRun
from story_gen.core.story_analysis_pipeline import StoryAnalysisResult
from story_gen.core.story_schema import STORY_SCHEMA_VERSION, StoryDocument


class MongoStoryAnalysisStore:
    """Persist full analysis payloads as append-only JSONL documents."""

    def __init__(self, db_path: Path) -> None:
        self._runs_path = db_path.with_name(f"{db_path.stem}.mongo_analysis_runs.jsonl")
        self._meta_path = db_path.with_name(f"{db_path.stem}.mongo_analysis_meta.json")
        self._runs_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema_version()

    def _ensure_schema_version(self) -> None:
        now = datetime.now(UTC).isoformat()
        if not self._meta_path.exists():
            self._meta_path.write_text(
                json.dumps(
                    {
                        "schema_key": "story_analysis_runs",
                        "schema_version": STORY_SCHEMA_VERSION,
                        "updated_at_utc": now,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            return
        payload = json.loads(self._meta_path.read_text(encoding="utf-8"))
        version = str(payload.get("schema_version", ""))
        if version != STORY_SCHEMA_VERSION:
            raise RuntimeError(
                "Analysis schema version mismatch: "
                f"store={version}, expected={STORY_SCHEMA_VERSION}"
            )

    def write_analysis_result(
        self,
        *,
        owner_id: str,
        result: StoryAnalysisResult,
    ) -> StoredAnalysisRun:
        """Persist one analysis run as a Mongo-style document payload."""
        run = StoredAnalysisRun(
            run_id=uuid4().hex,
            story_id=result.document.story_id,
            owner_id=owner_id,
            schema_version=result.document.schema_version,
            analyzed_at_utc=datetime.now(UTC).isoformat(),
        )
        document = {
            "run_id": run.run_id,
            "story_id": run.story_id,
            "owner_id": run.owner_id,
            "schema_version": run.schema_version,
            "analyzed_at_utc": run.analyzed_at_utc,
            "analysis_document": result.document.model_dump(mode="json"),
            "dashboard": asdict(result.dashboard),
            "graph_svg": result.graph_svg,
        }
        with self._runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(document, ensure_ascii=False))
            handle.write("\n")
        return run

    def get_latest_analysis(
        self,
        *,
        owner_id: str,
        story_id: str,
    ) -> LatestAnalysisPayload | None:
        """Load latest analysis by scanning append-only records in reverse order."""
        if not self._runs_path.exists():
            return None
        lines = self._runs_path.read_text(encoding="utf-8").splitlines()
        for raw in reversed(lines):
            if not raw.strip():
                continue
            payload = json.loads(raw)
            if payload.get("owner_id") != owner_id or payload.get("story_id") != story_id:
                continue
            metadata = StoredAnalysisRun(
                run_id=str(payload["run_id"]),
                story_id=str(payload["story_id"]),
                owner_id=str(payload["owner_id"]),
                schema_version=str(payload["schema_version"]),
                analyzed_at_utc=str(payload["analyzed_at_utc"]),
            )
            document = StoryDocument.model_validate(payload["analysis_document"])
            dashboard_payload = payload.get("dashboard")
            if not isinstance(dashboard_payload, dict):
                raise RuntimeError(
                    "Invalid dashboard payload in mongo prototype store: expected object."
                )
            graph_svg = str(payload.get("graph_svg", ""))
            return metadata, document, dict(dashboard_payload), graph_svg
        return None
