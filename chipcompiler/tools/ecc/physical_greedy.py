"""Closed-loop data-only buffer selection on the committed physical session."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from chipcompiler.tools.ecc.physical_placement import (
    NoLegalBufferLocation,
    PhysicalBufferLegalizer,
)
from chipcompiler.tools.ecc.sta_session import IncrementalStaSession


def _setup_qor(current: Mapping[str, object]) -> dict:
    raw = current["qor_json"]
    if not isinstance(raw, str):
        raise ValueError("physical QOR must be serialized JSON")
    return json.loads(raw)["summary"]["setup"]


def run_physical_greedy(
    session: IncrementalStaSession,
    cell_names: Sequence[str],
    log_path: Path,
    *,
    top_k: int = 100,
    max_rounds: int = 10,
    max_buffers: int = 1000,
    committed_buffers: int = 0,
) -> dict:
    """Commit legal positive-gain batches; observed QOR never vetoes a commit."""
    for value in (top_k, max_rounds, max_buffers):
        if type(value) is not int or not 0 < value < 1 << 64:
            raise ValueError("greedy budgets must be positive uint64 integers")
    current = session.read_physical_result(summary_only=True)
    generation = current["generation"]
    if type(generation) is not int:
        raise ValueError("physical generation must be an integer")
    if (
        type(committed_buffers) is not int
        or not 0 <= committed_buffers <= max_buffers
        or not 0 <= generation <= max_rounds
    ):
        raise ValueError("committed physical history exceeds greedy budget")
    before = _setup_qor(current)
    result = {
        "generation": generation,
        "rounds": generation,
        "buffers": committed_buffers,
        "stop_reason": "",
    }
    # This log is an execution record. Journal markers own design commits.
    with log_path.open("a", encoding="utf-8") as log:

        def record(value: dict) -> None:
            log.write(json.dumps(value, allow_nan=False, sort_keys=True) + "\n")
            log.flush()

        if generation == max_rounds or committed_buffers == max_buffers:
            result["stop_reason"] = (
                "buffer_budget_exhausted"
                if committed_buffers == max_buffers
                else "round_budget_exhausted"
            )
            record(result)
            return result
        if not cell_names:
            result["stop_reason"] = "no_eligible_buffer"
            record(result)
            return result
        geometry = session.read_physical_placement(
            expected_generation=generation,
            cell_names=cell_names,
        )
        legalizer = PhysicalBufferLegalizer(
            geometry,
            batch_capacity=min(top_k, max_buffers - committed_buffers),
            total_capacity=max_buffers - committed_buffers,
        )
        try:
            for _ in range(max_rounds - generation):
                if result["buffers"] == max_buffers:
                    result["stop_reason"] = "buffer_budget_exhausted"
                    break
                selected = session.select_physical_buffers(
                    expected_generation=generation,
                    cell_names=cell_names,
                    top_k=top_k,
                    max_buffers=max_buffers - result["buffers"],
                )
                if selected["generation"] != generation:
                    raise ValueError("greedy selection returned a stale generation")
                candidates = selected["candidates"]
                if not isinstance(candidates, list):
                    raise ValueError("greedy candidates must be a list")
                if not candidates:
                    result["stop_reason"] = "no_positive_gain"
                    break
                try:
                    locations = legalizer.prepare(
                        [
                            candidate["edit"]["library_cell"]["cell_name"]
                            for candidate in candidates
                        ],
                        [tuple(candidate["target_dbu"]) for candidate in candidates],
                    )
                except NoLegalBufferLocation:
                    result["stop_reason"] = "no_legal_location"
                    break
                edits = []
                for candidate, location in zip(candidates, locations, strict=True):
                    edit = dict(candidate["edit"])
                    edit["placement_inputs"] = {
                        "kind": "placed",
                        "x_microns": location.x_dbu / legalizer.dbu_per_um,
                        "y_microns": location.y_dbu / legalizer.dbu_per_um,
                    }
                    edits.append(
                        {
                            "edit": edit,
                            "physical": {
                                "x_dbu": location.x_dbu,
                                "y_dbu": location.y_dbu,
                                "orientation": location.orientation,
                            },
                        }
                    )
                applied = session.apply_physical_batch(expected_generation=generation, edits=edits)
                legalizer.committed(applied.generation)
                generation = applied.generation
                result.update(
                    generation=generation,
                    rounds=result["rounds"] + 1,
                    buffers=result["buffers"] + len(edits),
                )
                current = session.read_physical_result(summary_only=True)
                if current["generation"] != generation:
                    raise ValueError("physical query returned a stale generation")
                after = _setup_qor(current)
                record(
                    {
                        "generation": generation,
                        "buffers": len(edits),
                        "predicted_gain_ns": [
                            candidate["predicted_gain_ns"] for candidate in candidates
                        ],
                        "before_setup": before,
                        "after_setup": after,
                        "wns_change_ns": after["wns"] - before["wns"],
                        "tns_change_ns": after["tns"] - before["tns"],
                        "executed_backend": applied.execution.executed_backend.value,
                        "executed_update_strategy": (
                            applied.execution.executed_update_strategy.value
                        ),
                        "fallback": applied.execution.fallback_to_full,
                    }
                )
                before = after
            else:
                result["stop_reason"] = "round_budget_exhausted"
        except Exception as error:
            legalizer.abandon()
            result["stop_reason"] = "execution_failed"
            record(result | {"error": str(error)})
            raise
        record(result)
    return result
