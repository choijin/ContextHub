"""Start the ContextHub API and Streamlit client as one local application."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_BASE_URL_ENV = "CONTEXTHUB_API_BASE_URL"


class ManagedProcess(Protocol):
    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def kill(self) -> None: ...


def build_api_command(host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "contexthub.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]


def build_streamlit_command(host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(PROJECT_ROOT / "frontend" / "streamlit_app.py"),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]


def api_is_healthy(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=1.0)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def wait_for_api(
    process: ManagedProcess,
    health_url: str,
    timeout_seconds: float,
    probe: Callable[[str], bool] = api_is_healthy,
    poll_interval_seconds: float = 0.2,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(f"FastAPI exited during startup with code {exit_code}.")
        if probe(health_url):
            return
        time.sleep(poll_interval_seconds)
    raise RuntimeError(f"FastAPI did not become healthy within {timeout_seconds:g} seconds.")


def stop_process(process: ManagedProcess | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)


def monitor_processes(api_process: ManagedProcess, streamlit_process: ManagedProcess) -> int:
    while True:
        api_exit_code = api_process.poll()
        if api_exit_code is not None:
            return api_exit_code
        streamlit_exit_code = streamlit_process.poll()
        if streamlit_exit_code is not None:
            return streamlit_exit_code
        time.sleep(0.5)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-host", default="127.0.0.1")
    parser.add_argument("--ui-port", type=int, default=8501)
    parser.add_argument("--startup-timeout", type=float, default=120.0)
    args = parser.parse_args(argv)
    if not 1 <= args.api_port <= 65535 or not 1 <= args.ui_port <= 65535:
        parser.error("ports must be between 1 and 65535")
    if args.startup_timeout <= 0:
        parser.error("startup timeout must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    api_base_url = f"http://127.0.0.1:{args.api_port}"
    child_environment = os.environ.copy()
    child_environment.setdefault(API_BASE_URL_ENV, api_base_url)

    api_process: subprocess.Popen[bytes] | None = None
    streamlit_process: subprocess.Popen[bytes] | None = None
    try:
        api_process = subprocess.Popen(
            build_api_command(args.api_host, args.api_port),
            cwd=PROJECT_ROOT,
            env=child_environment,
        )
        wait_for_api(
            api_process,
            f"{api_base_url}/health",
            timeout_seconds=args.startup_timeout,
        )
        streamlit_process = subprocess.Popen(
            build_streamlit_command(args.ui_host, args.ui_port),
            cwd=PROJECT_ROOT,
            env=child_environment,
        )
        print(f"ContextHub is available at http://127.0.0.1:{args.ui_port}")
        return monitor_processes(api_process, streamlit_process)
    except KeyboardInterrupt:
        return 0
    except RuntimeError as exc:
        print(f"ContextHub startup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        stop_process(streamlit_process)
        stop_process(api_process)


if __name__ == "__main__":
    raise SystemExit(main())
