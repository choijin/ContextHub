from collections.abc import Iterator

import pytest

from scripts.run_local import (
    build_api_command,
    build_streamlit_command,
    parse_args,
    wait_for_api,
)


class FakeProcess:
    def __init__(self, poll_results: Iterator[int | None]) -> None:
        self._poll_results = poll_results

    def poll(self) -> int | None:
        return next(self._poll_results)

    def terminate(self) -> None:
        pass

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        pass


def test_local_commands_start_uvicorn_and_streamlit() -> None:
    api_command = build_api_command("127.0.0.1", 8000)
    streamlit_command = build_streamlit_command("127.0.0.1", 8501)

    assert api_command[-4:] == ["--host", "127.0.0.1", "--port", "8000"]
    assert "contexthub.main:app" in api_command
    assert streamlit_command[-6:] == [
        "--server.address",
        "127.0.0.1",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]
    assert streamlit_command[2:4] == ["streamlit", "run"]


def test_wait_for_api_returns_after_successful_health_probe() -> None:
    attempts: list[str] = []

    def probe(url: str) -> bool:
        attempts.append(url)
        return len(attempts) == 2

    wait_for_api(
        FakeProcess(iter([None, None])),
        "http://127.0.0.1:8000/health",
        timeout_seconds=1.0,
        probe=probe,
        poll_interval_seconds=0.0,
    )

    assert attempts == ["http://127.0.0.1:8000/health"] * 2


def test_wait_for_api_reports_early_process_exit() -> None:
    with pytest.raises(RuntimeError, match="exited during startup with code 3"):
        wait_for_api(
            FakeProcess(iter([3])),
            "http://127.0.0.1:8000/health",
            timeout_seconds=1.0,
            probe=lambda _: False,
            poll_interval_seconds=0.0,
        )


def test_parse_args_rejects_invalid_ports() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--api-port", "0"])
