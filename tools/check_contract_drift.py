"""Validate contract registry and stage artifact contract drift with clear errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from story_gen.api.contract_registry import build_contract_registry_snapshot

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_DIR = REPO_ROOT / "work" / "contracts"
REGISTRY_PATH = CONTRACTS_DIR / "story_pipeline_contract_registry.v1.json"
STAGE_GLOB = "[A-H]_*.json"
VALID_STAGES = {"A", "B", "C", "D", "E", "F", "G", "H"}


class StageArtifactSpec(BaseModel):
    id: str = Field(min_length=2)
    path_template: str = Field(min_length=3)
    format: Literal["json", "jsonl", "csv", "parquet", "txt"]
    required_fields: list[str] = Field(min_length=1)


class StageContractSpec(BaseModel):
    stage: str = Field(min_length=1, max_length=1)
    name: str = Field(min_length=3)
    version: str = Field(min_length=3)
    artifacts: list[StageArtifactSpec] = Field(min_length=1)
    invariants: list[str] = Field(min_length=1)


StageContractSpec.model_rebuild()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name}: invalid JSON ({exc})") from exc


def _registry_drift_errors(*, repo_root: Path) -> list[str]:
    contracts_dir = repo_root / "work" / "contracts"
    registry_path = contracts_dir / "story_pipeline_contract_registry.v1.json"
    expected = build_contract_registry_snapshot().model_dump(mode="json")
    try:
        actual = _load_json(registry_path)
    except ValueError as exc:
        return [str(exc)]
    if not isinstance(actual, dict):
        return [f"{registry_path.name}: expected JSON object at root."]
    errors: list[str] = []
    expected_schema = {item["contract_id"]: item for item in expected.get("schema_contracts", [])}
    actual_schema = {
        item.get("contract_id"): item
        for item in actual.get("schema_contracts", [])
        if isinstance(item, dict)
    }
    expected_ids = set(expected_schema)
    actual_ids = {str(item_id) for item_id in actual_schema if item_id is not None}
    for missing in sorted(expected_ids - actual_ids):
        errors.append(f"{registry_path.name}: missing schema contract '{missing}'.")
    for unexpected in sorted(actual_ids - expected_ids):
        errors.append(f"{registry_path.name}: unexpected schema contract '{unexpected}'.")
    for contract_id in sorted(expected_ids & actual_ids):
        if actual_schema[contract_id] != expected_schema[contract_id]:
            errors.append(
                f"{registry_path.name}: schema contract '{contract_id}' differs from runtime definition."
            )

    expected_stage = {
        item["stage_id"]: item for item in expected.get("pipeline_stage_contracts", [])
    }
    actual_stage = {
        item.get("stage_id"): item
        for item in actual.get("pipeline_stage_contracts", [])
        if isinstance(item, dict)
    }
    expected_stage_ids = set(expected_stage)
    actual_stage_ids = {str(item_id) for item_id in actual_stage if item_id is not None}
    for missing in sorted(expected_stage_ids - actual_stage_ids):
        errors.append(f"{registry_path.name}: missing pipeline stage contract '{missing}'.")
    for unexpected in sorted(actual_stage_ids - expected_stage_ids):
        errors.append(f"{registry_path.name}: unexpected pipeline stage contract '{unexpected}'.")
    for stage_id in sorted(expected_stage_ids & actual_stage_ids):
        if actual_stage[stage_id] != expected_stage[stage_id]:
            errors.append(
                f"{registry_path.name}: pipeline stage contract '{stage_id}' differs from runtime definition."
            )
    return errors


def _stage_contract_errors(*, repo_root: Path) -> list[str]:
    contracts_dir = repo_root / "work" / "contracts"
    errors: list[str] = []
    seen_stages: set[str] = set()
    for path in sorted(contracts_dir.glob(STAGE_GLOB)):
        try:
            payload = _load_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        try:
            parsed = StageContractSpec.model_validate(payload)
        except ValidationError as exc:
            first = exc.errors()[0]
            location = ".".join(str(part) for part in first.get("loc", ()))
            message = str(first.get("msg", "validation error"))
            errors.append(f"{path.name}: schema validation failed at {location} ({message}).")
            continue
        if parsed.stage not in VALID_STAGES:
            errors.append(f"{path.name}: unsupported stage '{parsed.stage}'.")
            continue
        if not path.name.startswith(f"{parsed.stage}_"):
            errors.append(f"{path.name}: stage '{parsed.stage}' does not match filename prefix.")
        if parsed.stage in seen_stages:
            errors.append(f"{path.name}: duplicate stage '{parsed.stage}' contract file.")
        seen_stages.add(parsed.stage)
        for artifact in parsed.artifacts:
            if len(set(artifact.required_fields)) != len(artifact.required_fields):
                errors.append(
                    f"{path.name}: artifact '{artifact.id}' has duplicate required_fields entries."
                )
    missing_stages = sorted(VALID_STAGES - seen_stages)
    for stage in missing_stages:
        errors.append(f"work/contracts: missing stage contract file for stage '{stage}'.")
    return errors


def run_check(*, repo_root: Path = REPO_ROOT) -> list[str]:
    """Return all contract drift and schema-shape errors."""
    if not (repo_root / "work" / "contracts").exists():
        return ["work/contracts directory is missing."]
    errors: list[str] = []
    errors.extend(_registry_drift_errors(repo_root=repo_root))
    errors.extend(_stage_contract_errors(repo_root=repo_root))
    return errors


def main() -> None:
    errors = run_check(repo_root=REPO_ROOT)
    if errors:
        formatted = "\n".join(f"- {error}" for error in errors)
        raise SystemExit(f"Contract drift check failed:\n{formatted}")
    print("contract drift checks passed")


if __name__ == "__main__":
    main()
