"""CLI runner for pre-push quality checks."""

from __future__ import annotations

from story_gen.pre_push_checks import main as run_checks


def main() -> None:
    run_checks()


if __name__ == "__main__":
    main()
