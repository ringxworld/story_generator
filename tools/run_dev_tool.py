"""Run development tools from the repository virtual environment when available."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _venv_python() -> Path | None:
    candidates = [
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
        REPO_ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _venv_executable(name: str) -> Path | None:
    suffix = ".exe" if sys.platform.startswith("win") else ""
    candidates = [
        REPO_ROOT / ".venv" / "Scripts" / f"{name}{suffix}",
        REPO_ROOT / ".venv" / "bin" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _command(tool: str, args: list[str]) -> list[str]:
    module_tools = {
        "ruff": "ruff",
        "mypy": "mypy",
        "pytest": "pytest",
        "mkdocs": "mkdocs",
        "pre-commit": "pre_commit",
    }
    if tool in module_tools:
        python = _venv_python() or Path(sys.executable)
        return [str(python), "-m", module_tools[tool], *args]

    if tool == "clang-format":
        executable = _venv_executable("clang-format")
        if executable is not None:
            return [str(executable), *args]

    resolved = shutil.which(tool)
    if resolved is None:
        raise SystemExit(f"Executable `{tool}` not found")
    return [resolved, *args]


def main(argv: list[str] | None = None) -> None:
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        raise SystemExit("Usage: python tools/run_dev_tool.py <tool> [args...]")
    tool, *tool_args = raw
    command = _command(tool, tool_args)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
