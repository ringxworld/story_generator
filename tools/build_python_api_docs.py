#!/usr/bin/env python3
"""Build static Python API reference pages with pdoc."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _discover_modules(src_root: Path) -> list[str]:
    modules: list[str] = [src_root.name]
    for path in sorted(src_root.rglob("*.py")):
        relative = path.relative_to(src_root.parent)
        module_parts = list(relative.with_suffix("").parts)
        if module_parts[-1] in {"__init__", "__main__"}:
            continue
        modules.append(".".join(module_parts))
    deduped = list(dict.fromkeys(modules))
    if not deduped:
        raise RuntimeError("No Python modules discovered for pdoc generation.")
    return deduped


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pdoc pages for story_gen modules.")
    parser.add_argument(
        "--src-root",
        type=Path,
        default=Path("src/story_gen"),
        help="Path to package source root.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pydoc_site"),
        help="Directory to write generated HTML docs.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    src_root = args.src_root.resolve()
    output_dir = args.output_dir.resolve()
    repo_root = src_root.parents[1]

    modules = _discover_modules(src_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = (
        src_path if not env.get("PYTHONPATH") else f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
    )

    command = [sys.executable, "-m", "pdoc", "-o", str(output_dir), *modules]
    subprocess.run(command, check=True, cwd=repo_root, env=env)

    index_path = output_dir / "index.html"
    root_page = output_dir / "story_gen.html"
    if not index_path.exists() and root_page.exists():
        index_path.write_text(root_page.read_text(encoding="utf-8"), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
