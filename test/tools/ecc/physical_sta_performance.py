"""One physical trace sample: candidate reads each round, artifacts once at the end."""

import json
from time import perf_counter


def run_sample(session, trace: dict, cell_names: list[str], request: dict, build: dict) -> dict:
    """Use the real session entry points; this function never starts an oracle."""
    if build["debug_checks_enabled"] or build["build_config"] != "Release":
        raise ValueError("physical performance requires Release with debug checks OFF")
    if trace["schema_version"] != "physical-sta-trace/1.0.0":
        raise ValueError("invalid physical trace")
    batches = trace["batches"]
    if not batches or any(
        batch["expected_generation"] != index or not batch["edits"]
        for index, batch in enumerate(batches)
    ):
        raise ValueError("performance requires contiguous nonempty physical batches")
    if sum(len(batch["edits"]) for batch in batches) > 1000:
        raise ValueError("fixed trace exceeds the frozen buffer budget")
    measured = []
    inserted = 0
    started = perf_counter()
    for generation, batch in enumerate(batches):
        step_started = perf_counter()
        selected = json.loads(
            session.select_physical_buffers(
                expected_generation=generation,
                cell_names=cell_names,
                top_k=100,
                max_buffers=1000 - inserted,
            )
        )
        candidate_done = perf_counter()
        if selected["generation"] != generation:
            raise RuntimeError("candidate read returned a stale generation")
        applied = session.apply_physical_batch(batch_json=json.dumps(batch, allow_nan=False))
        committed = perf_counter()
        execution = applied["execution"]
        if (
            applied["generation"] != generation + 1
            or execution["fallback_to_full"]
            or execution["executed_backend"] != request["backend"]
            or execution["executed_update_strategy"] != request["update_strategy"]
            or (
                request["update_strategy"] == "incremental"
                and not execution["incremental_batch_executed"]
            )
        ):
            raise RuntimeError("physical performance did not execute the requested batch")
        inserted += len(batch["edits"])
        measured.append(
            {
                "generation": applied["generation"],
                "candidate_count": len(selected["candidates"]),
                "buffer_count": len(batch["edits"]),
                "execution": execution,
                "candidate_read_ms": (candidate_done - step_started) * 1000,
                "commit_ms": (committed - candidate_done) * 1000,
                "step_ms": (committed - step_started) * 1000,
                "explicit_complete_report_request": "not_run",
            }
        )
    query_started = perf_counter()
    current = session.read_physical_result()
    queried = perf_counter()
    if current["generation"] != len(batches):
        raise RuntimeError("final physical query returned a stale generation")
    artifacts = json.loads(session.publish_physical_artifacts(expected_generation=len(batches)))
    published = perf_counter()
    if artifacts["generation"] != len(batches):
        raise RuntimeError("final artifacts have a stale generation")
    return {
        "schema_version": "physical-sta-sample/3.0.0",
        "build": build,
        "debug_checks_enabled": False,
        "requested": request,
        "workload": "fixed_trace_consumption",
        "placement_cost": "positions_frozen_before_sampling",
        "stop_reason": "trace_completed",
        "result_requirements": {
            "per_round": "candidate_inputs",
            "candidate_cells": cell_names,
            "top_k": 100,
            "max_buffers": 1000,
            "final": "timing_qor_paths_power_sdf_def_netlist",
            "max_paths": 20,
            "nworst": 20,
        },
        "correctness_comparison": "not_run",
        "diagnostics": "not_run",
        "batch_timings": measured,
        "final_query_ms": (queried - query_started) * 1000,
        "final_artifact_ms": (published - queried) * 1000,
        "optimization_end_to_end_ms": (published - started) * 1000,
        "result": {"generation": current["generation"]},
        "artifacts": artifacts,
    }
