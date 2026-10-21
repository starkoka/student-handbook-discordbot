"""Start vLLM and the Discord bot as one application."""

from __future__ import annotations

import json
import math
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


def gpu_memory_utilization(environment: dict[str, str]) -> str:
    """Budget logical cuda:0, probing in a child to release its CUDA context."""
    setting = environment.get("VLLM_GPU_MEMORY_UTILIZATION", "auto").strip()
    if setting != "auto":
        try:
            value = float(setting)
        except ValueError as exc:
            raise ValueError("VLLM_GPU_MEMORY_UTILIZATIONはautoまたは0より大きく1以下の数値です") from exc
        if not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError("VLLM_GPU_MEMORY_UTILIZATIONはautoまたは0より大きく1以下の数値です")
        return str(value)

    reserve_gib = float(environment.get("VLLM_GPU_MEMORY_RESERVE_GIB", "2"))
    if not math.isfinite(reserve_gib) or reserve_gib < 0:
        raise ValueError("VLLM_GPU_MEMORY_RESERVE_GIBには0以上の有限の数値を指定してください")
    try:
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import json, torch; print(json.dumps(torch.cuda.mem_get_info(0)))",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        free, total = json.loads(result.stdout)
        if not 0 <= free <= total or total <= 0:
            raise ValueError("Invalid GPU memory information")
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
        raise RuntimeError(
            "GPU空きメモリを取得できませんでした。CUDA環境を確認するか、"
            "VLLM_GPU_MEMORY_UTILIZATIONに利用率を明示してください。"
            f" 詳細: {getattr(exc, 'stderr', None) or exc}"
        ) from exc

    # Round down so formatting cannot raise the budget above available memory.
    value = math.floor(min(0.90, (free - reserve_gib * 1024**3) / total) * 1000) / 1000
    if value <= 0:
        raise RuntimeError("GPU空きメモリが予約分以下です。GPUの使用状況を確認してください。")
    print(
        f"[launcher] cuda:0 空き={free / 1024**3:.2f} GiB / "
        f"全体={total / 1024**3:.2f} GiB、余裕={reserve_gib:.2f} GiB、"
        f"gpu-memory-utilization={value:.3f}",
        flush=True,
    )
    return f"{value:.3f}"


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
        utilization = gpu_memory_utilization(environment)
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
                    "--gpu-memory-utilization",
                    utilization,
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
