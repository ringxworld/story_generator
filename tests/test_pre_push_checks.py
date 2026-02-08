from __future__ import annotations

import subprocess

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

    assert executed == [
        ["uv", "lock", "--check"],
        ["uv", "run", "mypy"],
        ["uv", "run", "pytest"],
    ]


def test_pre_push_checks_stops_on_command_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        executed.append(command)
        return subprocess.CompletedProcess(
            args=command,
            returncode=1 if command == ["uv", "run", "mypy"] else 0,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as raised:
        pre_push_checks.main()

    assert raised.value.code == 1
    assert executed == [
        ["uv", "lock", "--check"],
        ["uv", "run", "mypy"],
    ]
