"""Run API and web dev servers together for local development."""

from __future__ import annotations

import argparse
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class StackConfig:
    """Runtime configuration for local stack launch."""

    api_host: str
    api_port: int
    web_host: str
    web_port: int


def _which(name: str) -> str:
    resolved = shutil.which(name)
    if resolved is None:
        raise SystemExit(f"Executable `{name}` not found on PATH.")
    return resolved


def _spawn(command: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(command)


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_until_exit(processes: list[subprocess.Popen[bytes]]) -> int:
    while True:
        for process in processes:
            code = process.poll()
            if code is not None:
                return code
        time.sleep(0.2)


def run_stack(config: StackConfig) -> int:
    """Launch API + web and keep both alive until interruption/failure."""
    uv = _which("uv")
    npm = _which("npm")
    api_cmd = [
        uv,
        "run",
        "story-api",
        "--host",
        config.api_host,
        "--port",
        str(config.api_port),
        "--reload",
    ]
    web_cmd = [
        npm,
        "run",
        "--prefix",
        "web",
        "dev",
        "--",
        "--host",
        config.web_host,
        "--port",
        str(config.web_port),
    ]

    print("Starting local stack:")
    print(f"  API: http://{config.api_host}:{config.api_port}")
    print(f"  WEB: http://{config.web_host}:{config.web_port}")
    print("Press Ctrl+C to stop both services.")

    api = _spawn(api_cmd)
    web = _spawn(web_cmd)
    processes = [api, web]

    def _handle_signal(_signum: int, _frame: object) -> None:
        for process in processes:
            _terminate(process)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    exit_code = _wait_until_exit(processes)
    for process in processes:
        _terminate(process)
    return exit_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run API + web development stack.")
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=5173)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    config = StackConfig(
        api_host=args.api_host,
        api_port=args.api_port,
        web_host=args.web_host,
        web_port=args.web_port,
    )
    code = run_stack(config)
    raise SystemExit(code)


if __name__ == "__main__":
    main(sys.argv[1:])
