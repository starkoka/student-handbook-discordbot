"""Test launcher GPU budgets without requiring CUDA."""

import importlib.util
import json
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "handbook_launcher", Path(__file__).resolve().parents[2] / "run.py"
)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.mark.parametrize(
    ("free", "total", "expected"),
    [(35.52, 47.37, "0.707"), (48, 48, "0.900"), (4, 48, "0.041")],
)
def test_auto_budget(monkeypatch, free, total, expected):
    probe = Mock(return_value=Mock(stdout=json.dumps([free * 1024**3, total * 1024**3])))
    monkeypatch.setattr(launcher.subprocess, "run", probe)
    environment = {"CUDA_VISIBLE_DEVICES": "GPU-example"}
    assert launcher.gpu_memory_utilization(environment) == expected
    assert probe.call_args.kwargs["env"] == environment


def test_manual_budget_skips_probe(monkeypatch):
    probe = Mock()
    monkeypatch.setattr(launcher.subprocess, "run", probe)
    assert launcher.gpu_memory_utilization({"VLLM_GPU_MEMORY_UTILIZATION": "0.7"}) == "0.7"
    probe.assert_not_called()


@pytest.mark.parametrize("value", ["0", "-1", "1.1", "nan", "inf", "wrong"])
def test_invalid_manual_budget(value):
    with pytest.raises(ValueError):
        launcher.gpu_memory_utilization({"VLLM_GPU_MEMORY_UTILIZATION": value})


def test_insufficient_free_memory(monkeypatch):
    monkeypatch.setattr(
        launcher.subprocess, "run",
        Mock(return_value=Mock(stdout=json.dumps([1024**3, 48 * 1024**3]))),
    )
    with pytest.raises(RuntimeError, match="予約分以下"):
        launcher.gpu_memory_utilization({})


def test_probe_failure_does_not_guess_budget(monkeypatch):
    monkeypatch.setattr(
        launcher.subprocess, "run",
        Mock(side_effect=subprocess.CalledProcessError(1, "probe", stderr="CUDA unavailable")),
    )
    with pytest.raises(RuntimeError, match="CUDA unavailable"):
        launcher.gpu_memory_utilization({})


def test_custom_reserve(monkeypatch):
    monkeypatch.setattr(
        launcher.subprocess, "run",
        Mock(return_value=Mock(stdout=json.dumps([36 * 1024**3, 48 * 1024**3]))),
    )
    assert launcher.gpu_memory_utilization({"VLLM_GPU_MEMORY_RESERVE_GIB": "3"}) == "0.687"


def test_main_passes_budget_to_vllm(monkeypatch):
    monkeypatch.setattr(launcher, "gpu_memory_utilization", lambda env: "0.707")
    monkeypatch.setattr(launcher.signal, "signal", Mock())
    process = Mock()
    spawn = Mock(return_value=process)
    monkeypatch.setattr(launcher.subprocess, "Popen", spawn)
    monkeypatch.setattr(launcher, "terminate_all", Mock())
    monkeypatch.setattr(launcher, "wait_until_ready", Mock(side_effect=RuntimeError("stop test")))
    with pytest.raises(RuntimeError, match="stop test"):
        launcher.main()
    command = spawn.call_args.args[0]
    assert command[command.index("--gpu-memory-utilization") + 1] == "0.707"
