import json
from unittest.mock import Mock

import pytest

from test.tools.ecc.physical_sta_performance import run_sample


def test_sample_consumes_candidates_then_publishes_once(monkeypatch):
    calls = []
    session = Mock()
    generation = 0

    def select(**args):
        calls.append(("select", args["expected_generation"]))
        assert args["max_buffers"] == 1000 - generation
        return json.dumps({"generation": generation, "candidates": []})

    def apply(**args):
        nonlocal generation
        batch = json.loads(args["batch_json"])
        assert batch["expected_generation"] == generation
        generation += 1
        calls.append(("apply", generation))
        return {
            "generation": generation,
            "execution": {
                "executed_backend": "cuda",
                "executed_update_strategy": "incremental",
                "fallback_to_full": False,
                "incremental_batch_executed": True,
            },
        }

    def query():
        calls.append(("query", generation))
        return {"generation": generation, "timing": [1.5], "qor": {}, "paths": []}

    def publish(**args):
        assert args["expected_generation"] == generation
        calls.append(("publish", generation))
        return json.dumps({"generation": generation, "files": {"design.sdf": {}}})

    session.select_physical_buffers.side_effect = select
    session.apply_physical_batch.side_effect = apply
    session.read_physical_result.side_effect = query
    session.publish_physical_artifacts.side_effect = publish
    ticks = iter(range(20))
    monkeypatch.setattr(
        "test.tools.ecc.physical_sta_performance.perf_counter",
        lambda: next(ticks),
    )
    sample = run_sample(
        session,
        {
            "schema_version": "physical-sta-trace/1.0.0",
            "batches": [{"expected_generation": i, "edits": [{"buffer": i}]} for i in range(2)],
        },
        ["BUF"],
        {"backend": "cuda", "update_strategy": "incremental"},
        {"build_config": "Release", "debug_checks_enabled": False},
    )
    assert calls == [
        ("select", 0),
        ("apply", 1),
        ("select", 1),
        ("apply", 2),
        ("query", 2),
        ("publish", 2),
    ]
    assert sample["optimization_end_to_end_ms"] == 9000
    assert sample["final_query_ms"] == sample["final_artifact_ms"] == 1000
    assert sample["correctness_comparison"] == sample["diagnostics"] == "not_run"
    assert [b["explicit_complete_report_request"] for b in sample["batch_timings"]] == [
        "not_run",
        "not_run",
    ]


@pytest.mark.parametrize(
    "build",
    [
        {"build_config": "Release", "debug_checks_enabled": True},
        {"build_config": "Debug", "debug_checks_enabled": False},
    ],
)
def test_sample_rejects_build_before_workload(build):
    session = Mock()
    with pytest.raises(ValueError, match="Release with debug checks OFF"):
        run_sample(session, {}, [], {}, build)
    assert session.mock_calls == []


@pytest.mark.parametrize("failure", ["stale", "fallback", "output"])
def test_sample_never_reports_success_for_incomplete_work(failure):
    session = Mock()
    session.select_physical_buffers.return_value = json.dumps(
        {
            "generation": 3 if failure == "stale" else 0,
            "candidates": [],
        }
    )
    session.apply_physical_batch.return_value = {
        "generation": 1,
        "execution": {
            "executed_backend": "cpu",
            "executed_update_strategy": "full",
            "fallback_to_full": failure == "fallback",
        },
    }
    session.read_physical_result.return_value = {"generation": 1}
    session.publish_physical_artifacts.side_effect = OSError("output unavailable")
    with pytest.raises((RuntimeError, OSError)):
        run_sample(
            session,
            {
                "schema_version": "physical-sta-trace/1.0.0",
                "batches": [{"expected_generation": 0, "edits": [{}]}],
            },
            ["BUF"],
            {"backend": "cpu", "update_strategy": "full"},
            {"build_config": "Release", "debug_checks_enabled": False},
        )
    if failure == "stale":
        session.apply_physical_batch.assert_not_called()
    if failure != "output":
        session.publish_physical_artifacts.assert_not_called()


def _measurement(mode: str, version: int = 3) -> dict:
    backend, strategy = mode.split("/")
    return {
        "schema_version": f"physical-sta-sample/{version}.0.0",
        "build": {"build_config": "Release", "debug_checks_enabled": False},
        "debug_checks_enabled": False,
        "correctness_comparison": "not_run",
        "diagnostics": "not_run",
        "lifecycle_cleanup_completed": True,
        "threads_requested": 8,
        "cpu_affinity": [0, 1],
        "thread_activity": "external_profile",
        "requested": {"backend": backend, "update_strategy": strategy, "fallback_policy": "error"},
        "workload": "fixed_trace_consumption",
        "placement_cost": "positions_frozen_before_sampling",
        "stop_reason": "trace_completed",
        "result_requirements": {
            "per_round": "candidate_inputs",
            "candidate_cells": ["BUF"],
            "top_k": 100,
            "max_buffers": 1000,
            "final": "timing_qor_paths_power_sdf_def_netlist",
            "max_paths": 20,
            "nworst": 20,
        },
        "batch_timings": [
            {
                "generation": 1,
                "execution": {
                    "executed_backend": backend,
                    "executed_update_strategy": strategy,
                    "fallback_to_full": False,
                    "incremental_batch_executed": strategy == "incremental",
                },
                "buffer_count": 1,
                "candidate_count": 1,
                "explicit_complete_report_request": "not_run",
                "candidate_read_ms": 1,
                "commit_ms": 1,
                "step_ms": 2,
            }
        ],
        "final_query_ms": 1,
        "final_artifact_ms": 1,
        "optimization_end_to_end_ms": 5,
        "result": {"generation": 1},
        "artifacts": {
            "schema_version": "physical-sta-artifacts/1.0.0",
            "generation": 1,
            "report_request": {"max_paths": 20, "nworst": 20},
        },
        "load_ms": 1,
        "initialize_baseline_ms": 1,
        "cleanup_ms": 1,
        "session_end_to_end_ms": 8,
        "binding": {"path": "ecc_py.so", "sha256": "binary"},
        "inputs": {"def": {"sha256": "input"}},
        "trace": {"sha256": "trace"},
    }


@pytest.fixture
def sample_validator(monkeypatch):
    from importlib import import_module
    from pathlib import Path

    schema = (
        Path(__file__).resolve().parents[3]
        / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema"
    )
    monkeypatch.syspath_prepend(str(schema))
    return import_module("validate_physical_sta_samples")


@pytest.mark.parametrize(
    "fault",
    [
        None,
        "missing",
        "reordered",
        "generation",
        "final_time",
        "inputs",
        "diagnostics",
        "threads",
        "binding",
        "statistics",
        "bootstrap",
        "classification",
        "acceptance",
    ],
)
@pytest.mark.parametrize("version", [2, 3])
def test_physical_statistics_reject_mispaired_or_incomplete_loops(sample_validator, fault, version):
    modes = sample_validator.MODES if version == 2 else sample_validator.TIMING_MODES
    pairs = (
        (("cpu/full", "cuda/full"), ("cuda/full", "cuda/incremental"))
        if version == 2
        else (("cpu/full", "cuda/incremental"),)
    )
    rows: list[dict] = [
        {
            "warmup": False,
            "repetition": 1,
            "mode": mode,
            "process_wall_ms": 10,
            "measurement": _measurement(mode, version),
        }
        for mode in modes
    ]
    document: dict = {
        "schema_version": f"physical-sta-samples/{version}.0.0",
        "protocol": {
            "warmups": 0,
            "repetitions": 1,
            "mode_order": list(modes),
            "bootstrap_seed": sample_validator.BOOTSTRAP_SEED,
            "bootstrap_resamples": sample_validator.BOOTSTRAP_RESAMPLES,
            "pairing_unit": "fresh_process_complete_physical_loop",
        },
        "sampling_kind": "short_smoke",
        "stage15_acceptance": "not_run",
        "samples": rows,
    }
    stats = [
        {"mode": row["mode"], "warmup": False, "optimization_end_to_end_ms": 5} for row in rows
    ]
    document["summaries"], document["comparisons"] = sample_validator.consumer_statistics(
        stats,
        metric="optimization_end_to_end_ms",
        modes=modes,
        pairs=pairs,
    )
    changed = rows[-1]["measurement"]
    if fault == "missing":
        rows.pop()
    elif fault == "reordered":
        rows.reverse()
    elif fault == "generation":
        changed["artifacts"]["generation"] = 0
    elif fault == "final_time":
        changed["optimization_end_to_end_ms"] = 3
    elif fault == "inputs":
        changed["trace"] = {"sha256": "different"}
    elif fault == "diagnostics":
        changed["diagnostics"] = "passed"
    elif fault == "threads":
        changed["threads_requested"] = 1
    elif fault == "binding":
        changed["binding"] = {"path": "ecc_py.so", "sha256": "different"}
    elif fault == "statistics":
        document["comparisons"][f"{pairs[0][1]}_vs_{pairs[0][0]}"]["ci95"] = [2, 3]
    elif fault == "bootstrap":
        document["protocol"]["bootstrap_resamples"] = 10
    elif fault == "classification":
        document["sampling_kind"] = "engineering"
    elif fault == "acceptance":
        document["stage15_acceptance"] = "passed"
    if fault:
        with pytest.raises(ValueError):
            sample_validator.validate_document(document)
    else:
        summaries, comparisons = sample_validator.validate_document(document)
        assert all(summary["median_ms"] == 5 for summary in summaries.values())
        assert all(comparison["ci95"] == [1, 1] for comparison in comparisons.values())


@pytest.mark.parametrize("failure", [False, True, "timeout"])
def test_benchmark_retains_raw_results_and_stops_on_child_failure(
    tmp_path, monkeypatch, sample_validator, failure
):
    import subprocess
    import sys
    from pathlib import Path

    from test.tools.ecc import physical_sta_benchmark as benchmark

    source = tmp_path / "input"
    source.write_text("input")
    binding = tmp_path / "isolated" / "ecc_tools_bin"
    binding.mkdir(parents=True)
    (binding / "__init__.py").write_text("")
    output = tmp_path / "run"
    arguments = ["benchmark", "--output", str(output), "--warmup-runs", "0", "--samples", "1"]
    for option in ("workspace", "binding-dir", "def-file", "verilog-file", "sdc", "physical-trace"):
        arguments += [f"--{option}", str(binding if option == "binding-dir" else source)]
    monkeypatch.setattr(sys, "argv", arguments)
    ticks = iter(range(0, 100, 10))
    monkeypatch.setattr(benchmark, "perf_counter", lambda: next(ticks))
    modes = []
    actual_run = subprocess.run

    def run(command, **kwargs):
        imported = actual_run(
            [sys.executable, "-c", "import ecc_tools_bin; print(ecc_tools_bin.__file__)"],
            cwd=kwargs["cwd"],
            env=kwargs["env"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert Path(imported.stdout.strip()) == binding / "__init__.py"
        mode = (
            f"{command[command.index('--backend') + 1]}/{command[command.index('--strategy') + 1]}"
        )
        modes.append(mode)
        assert command[command.index("--mode") + 1] == "OFF" and "--benchmark" in command
        directory = Path(command[command.index("--output") + 1])
        directory.mkdir()
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 1)
        if not failure:
            (directory / "sample.json").write_text(json.dumps(_measurement(mode)))
        return subprocess.CompletedProcess(command, 7 if failure else 0)

    monkeypatch.setattr(benchmark.subprocess, "run", run)
    if failure:
        error = subprocess.TimeoutExpired if failure == "timeout" else subprocess.CalledProcessError
        with pytest.raises(error):
            benchmark.main()
        assert modes == ["cpu/full"]
        assert not (output / "incremental_sta_samples.json").exists()
        assert (output / "sample-1/cpu-full.exit").read_text().strip() == (
            "124" if failure == "timeout" else "7"
        )
    else:
        benchmark.main()
        assert modes == list(sample_validator.TIMING_MODES)
        document = json.loads((output / "incremental_sta_samples.json").read_text())
        assert document["sampling_kind"] == "short_smoke"
        assert document["stage15_acceptance"] == "not_run"
        sample_validator.validate_document(document)


@pytest.mark.parametrize(
    ("backend", "strategy"),
    [("cpu", "full"), ("cuda", "incremental")],
)
def test_closed_loop_cli_reaches_production_request(tmp_path, monkeypatch, backend, strategy):
    import importlib
    from pathlib import Path

    from chipcompiler.data import Workspace
    from chipcompiler.tools.ecc.sta_mode import request_from_mapping

    monkeypatch.syspath_prepend(str(Path(__file__).parent))
    probe = importlib.import_module("physical_sta_probe")
    source = tmp_path / "checkpoint"
    source.write_text("fixture")
    routing = tmp_path / "routing.json"
    routing.write_text(
        json.dumps({"RT": {"-bottom_routing_layer": "M1", "-top_routing_layer": "M5"}})
    )
    workspace = Workspace(directory=tmp_path)
    workspace.pdk.tech = source
    workspace.pdk.lefs = [source]
    workspace.pdk.libs = [source]
    workspace.config.update({"route": routing, "flow": source, "db": source})
    monkeypatch.setattr(probe, "load_workspace", lambda _: workspace)
    module = Mock()
    module.ecc.__file__ = str(tmp_path / "ecc_py.so")
    module.ecc.incregpusta_debug_checks_enabled = False
    module.ecc.incregpusta_cuda_enabled = True
    monkeypatch.setattr(probe, "ECCToolsModule", lambda: module)
    observed = []

    def run(actual_workspace, step, actual_module):
        request = request_from_mapping(actual_workspace.parameters.data)
        observed.append(
            (request.backend.value, request.update_strategy.value, request.fallback_policy.value)
        )
        assert actual_module is module
        return True

    monkeypatch.setattr("chipcompiler.tools.ecc.physical_runner.run_physical_timing_opt", run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "physical_sta_probe",
            "--workspace",
            str(tmp_path),
            "--binding-dir",
            str(tmp_path),
            "--def-file",
            str(source),
            "--verilog-file",
            str(source),
            "--sdc",
            str(source),
            "--mode",
            "OFF",
            "--backend",
            backend,
            "--strategy",
            strategy,
            "--output",
            str(tmp_path / "output"),
            "--closed-loop",
        ],
    )
    probe.main()
    assert observed == [(backend, strategy, "error")]
    module.close.assert_called_once()
