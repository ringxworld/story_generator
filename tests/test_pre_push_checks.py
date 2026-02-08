from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from story_gen import pre_push_checks


def test_pre_push_checks_runs_expected_commands_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        executed.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    pre_push_checks.main()

    assert executed[:6] == [
        ["uv", "lock", "--check"],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "ruff", "format", "--check", "."],
        ["uv", "run", "mypy"],
        ["uv", "run", "pytest"],
        ["uv", "run", "mkdocs", "build", "--strict"],
    ]
    assert executed[6][:5] == ["uv", "run", "clang-format", "--dry-run", "--Werror"]
    assert any("chapter_metrics.cpp" in part for part in executed[6])


def test_pre_push_checks_stops_on_command_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        executed.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=1 if command == ["uv", "run", "ruff", "check", "."] else 0,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as raised:
        pre_push_checks.main()

    assert raised.value.code == 1
    assert executed == [
        ["uv", "lock", "--check"],
        ["uv", "run", "ruff", "check", "."],
    ]


def test_pre_push_checks_skips_clang_when_no_cpp_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        executed.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "glob", lambda self, pattern: iter(()))

    pre_push_checks.main()

    assert all("clang-format" not in command for command in executed)
