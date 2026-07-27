"""Start vLLM and the Discord bot as one application."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
VLLM_PORT = 8000
MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen3-8B")
SERVED_MODEL_NAME = "Qwen/Qwen3-8B"
STARTUP_TIMEOUT = int(os.getenv("VLLM_STARTUP_TIMEOUT", "600"))


def wait_until_ready(url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"vLLMが準備完了前に終了しました (exit={process.returncode})"
            )
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(1)
    raise TimeoutError(f"vLLMの起動が{STARTUP_TIMEOUT}秒以内に完了しませんでした")


def terminate_all(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 10
    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()


def main() -> None:
    python = sys.executable
    environment = os.environ.copy()
    processes: list[subprocess.Popen[bytes]] = []

    def stop(_signum: int, _frame: object) -> None:
        terminate_all(processes)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    try:
        print(f"[launcher] vLLMを起動しています: {MODEL}", flush=True)
        processes.append(
            subprocess.Popen(
                [
                    python,
                    "-m",
                    "vllm.entrypoints.openai.api_server",
                    "--model",
                    MODEL,
                    "--served-model-name",
                    SERVED_MODEL_NAME,
                    "--host",
                    HOST,
                    "--port",
                    str(VLLM_PORT),
                ],
                cwd=ROOT,
                env=environment,
            )
        )
        wait_until_ready(
            f"http://{HOST}:{VLLM_PORT}/v1/models", processes[0]
        )

        print("[launcher] Discord Botを起動します", flush=True)
        processes.append(
            subprocess.Popen(
                [python, "discordbot/bot.py"],
                cwd=ROOT,
                env=environment,
            )
        )

        while all(process.poll() is None for process in processes):
            time.sleep(1)
        failed = next(process for process in processes if process.poll() is not None)
        raise RuntimeError(
            f"子プロセスが終了しました (exit={failed.returncode})"
        )
    finally:
        terminate_all(processes)


if __name__ == "__main__":
    main()
