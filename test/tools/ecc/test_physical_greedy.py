import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from chipcompiler.tools.ecc.physical_greedy import run_physical_greedy
from chipcompiler.tools.ecc.physical_placement import BufferLocation, NoLegalBufferLocation
from chipcompiler.tools.ecc.sta_mode import StaBackend, StaUpdateStrategy


@pytest.mark.parametrize("failure", [None, "placement", "apply"])
def test_greedy_uses_no_reports_and_records_real_stops(tmp_path, monkeypatch, failure):
    session = Mock()
    session.read_physical_result.side_effect = AssertionError("greedy requested a full report")
    session.read_physical_placement.return_value = {"generation": 0}
    session.select_physical_buffers.return_value = {
        "generation": 0,
        "candidates": [
            {
                "edit": {"library_cell": {"cell_name": "BUF"}},
                "target_dbu": [10, 20],
                "predicted_gain_ns": 0.5,
            }
        ],
    }
    session.apply_physical_batch.return_value = SimpleNamespace(
        generation=1,
        execution=SimpleNamespace(
            executed_backend=StaBackend.CUDA,
            executed_update_strategy=StaUpdateStrategy.INCREMENTAL,
            fallback_to_full=False,
        ),
    )
    legalizer = Mock(dbu_per_um=1000)
    legalizer.prepare.return_value = [BufferLocation(100, 200, "FS")]
    if failure == "placement":
        legalizer.prepare.side_effect = NoLegalBufferLocation("occupied")
    elif failure == "apply":
        session.apply_physical_batch.side_effect = RuntimeError("rollback completed")
    monkeypatch.setattr(
        "chipcompiler.tools.ecc.physical_greedy.PhysicalBufferLegalizer",
        Mock(return_value=legalizer),
    )
    path = tmp_path / "greedy.jsonl"
    if failure == "apply":
        with pytest.raises(RuntimeError, match="rollback completed"):
            run_physical_greedy(session, ["BUF"], path, max_rounds=1)
        legalizer.abandon.assert_called_once_with()
        legalizer.committed.assert_not_called()
        assert json.loads(path.read_text())["stop_reason"] == "execution_failed"
    else:
        result = run_physical_greedy(session, ["BUF"], path, max_rounds=1)
        records = [json.loads(line) for line in path.read_text().splitlines()]
        if failure == "placement":
            assert result == {
                "generation": 0,
                "rounds": 0,
                "buffers": 0,
                "stop_reason": "no_legal_location",
            }
            session.apply_physical_batch.assert_not_called()
        else:
            assert result == {
                "generation": 1,
                "rounds": 1,
                "buffers": 1,
                "stop_reason": "round_budget_exhausted",
            }
            assert records[0] == {
                "schema_version": "physical-sta-greedy/2.0.0",
                "generation": 1,
                "buffers": 1,
                "predicted_gain_ns": [0.5],
                "executed_backend": "cuda",
                "executed_update_strategy": "incremental",
                "fallback": False,
            }
            legalizer.committed.assert_called_once_with(1)
            legalizer.abandon.assert_not_called()
            session.apply_physical_batch.assert_called_once_with(
                expected_generation=0,
                edits=[
                    {
                        "edit": {
                            "library_cell": {"cell_name": "BUF"},
                            "placement_inputs": {
                                "kind": "placed",
                                "x_microns": 0.1,
                                "y_microns": 0.2,
                            },
                        },
                        "physical": {"x_dbu": 100, "y_dbu": 200, "orientation": "FS"},
                    }
                ],
            )
    session.read_physical_result.assert_not_called()


@pytest.mark.parametrize(
    "cells,generation,buffers,stop",
    [
        ([], 1, 1, "no_eligible_buffer"),
        (["BUF"], 2, 1, "round_budget_exhausted"),
        (["BUF"], 1, 2, "buffer_budget_exhausted"),
    ],
)
def test_greedy_reuses_recovery_generation_without_a_report(
    tmp_path, cells, generation, buffers, stop
):
    session = Mock()
    session.read_physical_result.side_effect = AssertionError("unrequested report")
    result = run_physical_greedy(
        session,
        cells,
        tmp_path / "greedy.jsonl",
        generation=generation,
        committed_buffers=buffers,
        max_rounds=2,
        max_buffers=2,
    )
    assert result == {
        "generation": generation,
        "rounds": generation,
        "buffers": buffers,
        "stop_reason": stop,
    }
    session.read_physical_result.assert_not_called()
    session.select_physical_buffers.assert_not_called()
    session.apply_physical_batch.assert_not_called()
