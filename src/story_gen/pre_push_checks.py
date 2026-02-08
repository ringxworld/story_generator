"""Cross-platform pre-push quality gate runner."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(command: list[str]) -> None:
    """Run one command and propagate its exit code on failure."""
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    """Mirror CI checks locally before code leaves the machine."""
    run(["uv", "run", "pre-commit", "run", "--all-files"])
    run(["uv", "lock", "--check"])
    run(["uv", "run", "python", "tools/check_imports.py"])
    run(["uv", "run", "ruff", "check", "."])
    run(["uv", "run", "ruff", "format", "--check", "."])
    run(["uv", "run", "mypy"])
    run(["uv", "run", "pytest"])
    run(["uv", "run", "mkdocs", "build", "--strict"])
    web_package = Path("web") / "package.json"
    if web_package.exists():
        run(["npm", "run", "--prefix", "web", "typecheck"])
        run(["npm", "run", "--prefix", "web", "test:coverage"])
        run(["npm", "run", "--prefix", "web", "build"])
    cpp_sources = [str(path) for path in sorted((Path("cpp")).glob("*.cpp"))]
    if cpp_sources:
        run(["uv", "run", "clang-format", "--dry-run", "--Werror", *cpp_sources])


if __name__ == "__main__":
    main()
