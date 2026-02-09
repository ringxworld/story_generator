from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "label_taxonomy_audit",
    Path(__file__).resolve().parents[1] / "tools" / "label_taxonomy_audit.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Unable to load tools/label_taxonomy_audit.py")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
LabelTaxonomy = _MODULE.LabelTaxonomy
evaluate_label_taxonomy = _MODULE.evaluate_label_taxonomy
_load_taxonomy = _MODULE._load_taxonomy


def test_evaluate_label_taxonomy_reports_missing_required_and_deprecated() -> None:
    taxonomy = LabelTaxonomy(
        required_labels={"Roadmap", "CI"},
        expected_labels={"Roadmap", "CI", "dependencies"},
        deprecated_aliases={"ci/cd"},
    )
    result = evaluate_label_taxonomy(
        taxonomy=taxonomy,
        actual_labels={"Roadmap", "ci/cd"},
    )

    assert "Missing required label: CI" in result.errors
    assert any("Expected label missing" in warning for warning in result.warnings)
    assert any("Deprecated/legacy label detected: ci/cd" in warning for warning in result.warnings)


def test_evaluate_label_taxonomy_passes_when_expected_labels_present() -> None:
    taxonomy = LabelTaxonomy(
        required_labels={"Roadmap", "CI"},
        expected_labels={"Roadmap", "CI", "dependencies"},
        deprecated_aliases={"ci/cd"},
    )
    result = evaluate_label_taxonomy(
        taxonomy=taxonomy,
        actual_labels={"Roadmap", "CI", "dependencies"},
    )

    assert result.errors == []
    assert result.warnings == []


def test_load_taxonomy_reads_json_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "taxonomy.json"
    config_path.write_text(
        json.dumps(
            {
                "required_labels": ["Roadmap"],
                "expected_labels": ["Roadmap", "CI"],
                "deprecated_aliases": ["ci/cd"],
            }
        ),
        encoding="utf-8",
    )

    taxonomy = _load_taxonomy(config_path)
    assert taxonomy.required_labels == {"Roadmap"}
    assert taxonomy.expected_labels == {"Roadmap", "CI"}
    assert taxonomy.deprecated_aliases == {"ci/cd"}
