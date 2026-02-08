"""Validate Python layer import boundaries for story_gen."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "src" / "story_gen"
KNOWN_LAYERS = {
    "api",
    "core",
    "adapters",
    "native",
    "cli",
    "application",
    "domain",
    "pipelines",
}
RULES: dict[str, set[str]] = {
    "core": {"api", "adapters", "native"},
}


def _layer_for_path(path: Path, source_root: Path) -> str | None:
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        return None
    if not relative.parts:
        return None
    return relative.parts[0]


def _layer_from_absolute_module(module_name: str) -> str | None:
    if not module_name:
        return None
    if module_name == "story_gen":
        return None
    if not module_name.startswith("story_gen."):
        return None
    parts = module_name.split(".")
    if len(parts) < 2:
        return None
    candidate = parts[1]
    return candidate if candidate in KNOWN_LAYERS else None


def _resolve_relative_base(path: Path, source_root: Path, level: int) -> list[str]:
    relative = path.relative_to(source_root)
    module_parts = ["story_gen", *relative.with_suffix("").parts]
    package_parts = module_parts[:-1]
    if level <= 0:
        return package_parts
    if level > len(package_parts):
        return []
    return package_parts[: len(package_parts) - level]


def _imported_layers_from_node(
    node: ast.Import | ast.ImportFrom,
    path: Path,
    source_root: Path,
) -> set[str]:
    imported_layers: set[str] = set()

    if isinstance(node, ast.Import):
        for alias in node.names:
            layer = _layer_from_absolute_module(alias.name)
            if layer is not None:
                imported_layers.add(layer)
        return imported_layers

    if node.level == 0:
        if node.module is None:
            return imported_layers
        direct_layer = _layer_from_absolute_module(node.module)
        if direct_layer is not None:
            imported_layers.add(direct_layer)
            return imported_layers
        if node.module == "story_gen":
            for alias in node.names:
                if alias.name in KNOWN_LAYERS:
                    imported_layers.add(alias.name)
        return imported_layers

    base_parts = _resolve_relative_base(path, source_root, node.level)
    if not base_parts:
        return imported_layers
    if node.module:
        absolute_parts = [*base_parts, *node.module.split(".")]
    else:
        absolute_parts = base_parts
    if not absolute_parts:
        return imported_layers
    absolute_module = ".".join(absolute_parts)
    direct_layer = _layer_from_absolute_module(absolute_module)
    if direct_layer is not None:
        imported_layers.add(direct_layer)
        return imported_layers
    if absolute_module == "story_gen":
        for alias in node.names:
            if alias.name in KNOWN_LAYERS:
                imported_layers.add(alias.name)
    return imported_layers


def check_file(path: Path, source_root: Path = DEFAULT_SOURCE_ROOT) -> list[str]:
    layer = _layer_for_path(path, source_root)
    if layer is None:
        return []
    banned_layers = RULES.get(layer, set())
    if not banned_layers:
        return []

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        imported_layers = _imported_layers_from_node(node, path, source_root)
        for imported_layer in sorted(imported_layers):
            if imported_layer in banned_layers:
                violations.append(f"{path}: {layer} must not import story_gen.{imported_layer}")
    return violations


def check_import_boundaries(source_root: Path = DEFAULT_SOURCE_ROOT) -> list[str]:
    violations: list[str] = []
    for path in sorted(source_root.rglob("*.py")):
        violations.extend(check_file(path, source_root))
    return violations


def main() -> None:
    violations = check_import_boundaries()
    if violations:
        raise SystemExit("\n".join(violations))
    print("import boundary checks passed")


if __name__ == "__main__":
    main()
