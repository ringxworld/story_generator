"""Cross-platform pre-push quality gate runner."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_RUNNER = REPO_ROOT / "tools" / "run_dev_tool.py"


def run(command: list[str]) -> None:
    """Run one command and propagate its exit code on failure."""
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def run_tool(tool: str, *args: str) -> None:
    """Run one development tool through the repository tool wrapper."""
    run([sys.executable, str(TOOL_RUNNER), tool, *args])


def main() -> None:
    """Mirror CI checks locally before code leaves the machine."""
    run_tool("pre-commit", "run", "--all-files")
    uv_executable = shutil.which("uv")
    if uv_executable is None:
        raise SystemExit("uv executable not found in PATH")
    run([uv_executable, "lock", "--check"])
    run([sys.executable, str(REPO_ROOT / "tools" / "check_imports.py")])
    run([sys.executable, str(REPO_ROOT / "tools" / "check_contract_drift.py")])
    run_tool("ruff", "check", ".")
    run_tool("ruff", "format", "--check", ".")
    run_tool("mypy")
    run_tool("pytest")
    run([uv_executable, "run", "story-pipeline-canary", "--strict"])
    run_tool("mkdocs", "build", "--strict")
    web_package = Path("web") / "package.json"
    if web_package.exists():
        run(["npm", "run", "--prefix", "web", "typecheck"])
        run(["npm", "run", "--prefix", "web", "test:coverage"])
        run(["npm", "run", "--prefix", "web", "build"])
    cpp_sources = [str(path) for path in sorted((Path("cpp")).glob("*.cpp"))]
    if cpp_sources:
        run_tool("clang-format", "--dry-run", "--Werror", *cpp_sources)
    docker_executable = shutil.which("docker")
    if docker_executable is None:
        raise SystemExit("docker executable not found in PATH")
    run(
        [
            docker_executable,
            "build",
            "-f",
            "docker/ci.Dockerfile",
            "-t",
            "story-gen-ci-prepush",
            ".",
        ]
    )


if __name__ == "__main__":
    main()
