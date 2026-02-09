from __future__ import annotations

import subprocess
import sys
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
    monkeypatch.setattr(
        "story_gen.pre_push_checks.shutil.which",
        lambda tool: "uv" if tool == "uv" else "docker",
    )
    pre_push_checks.main()

    assert executed[0][:4] == [
        sys.executable,
        str(pre_push_checks.TOOL_RUNNER),
        "pre-commit",
        "run",
    ]
    assert executed[0][-1] == "--all-files"
    assert executed[1][-2:] == ["lock", "--check"]
    assert executed[2][0] == sys.executable
    assert executed[2][-1].endswith("check_imports.py")
    assert executed[3][0] == sys.executable
    assert executed[3][-1].endswith("check_contract_drift.py")
    assert executed[4][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "ruff"]
    assert executed[4][-2:] == ["check", "."]
    assert executed[5][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "ruff"]
    assert executed[5][-3:] == ["format", "--check", "."]
    assert executed[6][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "mypy"]
    assert executed[7][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "pytest"]
    assert executed[8][:3] == ["uv", "run", "story-pipeline-canary"]
    assert executed[8][-1] == "--strict"
    assert executed[9][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "mkdocs"]
    assert executed[9][-2:] == ["build", "--strict"]
    assert ["npm", "run", "--prefix", "web", "typecheck"] in executed
    assert ["npm", "run", "--prefix", "web", "test:coverage"] in executed
    assert ["npm", "run", "--prefix", "web", "build"] in executed
    clang_commands = [
        command
        for command in executed
        if command[:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "clang-format"]
    ]
    assert len(clang_commands) == 1
    assert clang_commands[0][3:5] == ["--dry-run", "--Werror"]
    assert any("chapter_metrics.cpp" in part for part in clang_commands[0])
    assert [
        "docker",
        "build",
        "-f",
        "docker/ci.Dockerfile",
        "-t",
        "story-gen-ci-prepush",
        ".",
    ] in executed


def test_pre_push_checks_stops_on_command_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        executed.append(command)
        is_ruff_check = command[:3] == [
            sys.executable,
            str(pre_push_checks.TOOL_RUNNER),
            "ruff",
        ] and command[-2:] == ["check", "."]
        return subprocess.CompletedProcess(
            args=command,
            returncode=1 if is_ruff_check else 0,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        "story_gen.pre_push_checks.shutil.which",
        lambda tool: "uv" if tool == "uv" else "docker",
    )

    with pytest.raises(SystemExit) as raised:
        pre_push_checks.main()

    assert raised.value.code == 1
    assert executed[0][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "pre-commit"]
    assert executed[1][-2:] == ["lock", "--check"]
    assert executed[2][0] == sys.executable
    assert executed[3][0] == sys.executable
    assert executed[3][-1].endswith("check_contract_drift.py")
    assert executed[4][:3] == [sys.executable, str(pre_push_checks.TOOL_RUNNER), "ruff"]


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
    monkeypatch.setattr(
        "story_gen.pre_push_checks.shutil.which",
        lambda tool: "uv" if tool == "uv" else "docker",
    )

    pre_push_checks.main()

    assert all("clang-format" not in command for command in executed)


def test_pre_push_checks_skips_web_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        executed.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        if str(path).replace("\\", "/").endswith("web/package.json"):
            return False
        return original_exists(path)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(
        "story_gen.pre_push_checks.shutil.which",
        lambda tool: "uv" if tool == "uv" else "docker",
    )
    pre_push_checks.main()
    assert all(command[:3] != ["npm", "run", "--prefix"] for command in executed)


def test_pre_push_checks_requires_uv_for_lock_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, check: subprocess.CompletedProcess(args=command, returncode=0),
    )
    monkeypatch.setattr("story_gen.pre_push_checks.shutil.which", lambda _: None)

    with pytest.raises(SystemExit, match="uv executable not found in PATH"):
        pre_push_checks.main()


def test_pre_push_checks_requires_docker_for_ci_image_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, check: subprocess.CompletedProcess(args=command, returncode=0),
    )
    monkeypatch.setattr(
        "story_gen.pre_push_checks.shutil.which",
        lambda tool: "uv" if tool == "uv" else None,
    )

    with pytest.raises(SystemExit, match="docker executable not found in PATH"):
        pre_push_checks.main()
