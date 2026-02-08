from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _load_checker_module() -> ModuleType:
    module_path = ROOT / "tools" / "check_imports.py"
    spec = importlib.util.spec_from_file_location("check_imports_tool", module_path)
    assert spec is not None
    loader = spec.loader
    assert loader is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_check_file_allows_core_internal_import(tmp_path: Path) -> None:
    checker = _load_checker_module()
    source_root = tmp_path / "src" / "story_gen"
    core_file = source_root / "core" / "planner.py"
    _write(core_file, "from story_gen.core import model\n")
    violations = checker.check_file(core_file, source_root)
    assert violations == []


def test_check_file_rejects_core_importing_adapters(tmp_path: Path) -> None:
    checker = _load_checker_module()
    source_root = tmp_path / "src" / "story_gen"
    core_file = source_root / "core" / "planner.py"
    _write(core_file, "from story_gen.adapters import fs\n")
    violations = checker.check_file(core_file, source_root)
    assert len(violations) == 1
    assert "core must not import story_gen.adapters" in violations[0]
