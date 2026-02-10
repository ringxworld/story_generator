from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK_PATH = ROOT / "tools" / "check_contract_drift.py"
SPEC = importlib.util.spec_from_file_location("check_contract_drift", CHECK_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
run_check = MODULE.run_check


def test_contract_drift_check_passes_for_repository_snapshot() -> None:
    assert run_check(repo_root=ROOT) == []


def test_contract_drift_check_reports_artifact_name_and_schema_detail(tmp_path: Path) -> None:
    target_root = tmp_path / "repo"
    contracts_dir = target_root / "work" / "contracts"
    contracts_dir.mkdir(parents=True)
    for contract_path in (ROOT / "work" / "contracts").glob("*.json"):
        shutil.copy2(contract_path, contracts_dir / contract_path.name)
    bad_path = contracts_dir / "A_corpus_hygiene.json"
    payload = json.loads(bad_path.read_text(encoding="utf-8"))
    del payload["artifacts"][0]["required_fields"]
    bad_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    errors = run_check(repo_root=target_root)

    joined = "\n".join(errors)
    assert "A_corpus_hygiene.json" in joined
    assert "required_fields" in joined
