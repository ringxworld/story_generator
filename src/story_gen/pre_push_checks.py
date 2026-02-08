"""Cross-platform pre-push quality gate runner."""

from __future__ import annotations

import subprocess


def run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    run(["uv", "lock", "--check"])
    run(["uv", "run", "mypy"])
    run(["uv", "run", "pytest"])


if __name__ == "__main__":
    main()
