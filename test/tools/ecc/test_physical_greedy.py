import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from chipcompiler.tools.ecc.physical_greedy import run_physical_greedy
from chipcompiler.tools.ecc.physical_placement import BufferLocation, NoLegalBufferLocation
from chipcompiler.tools.ecc.sta_mode import StaBackend, StaUpdateStrategy


@pytest.mark.parametrize("failure", [None, "placement", "apply"])
def test_greedy_commits_negative_actual_gain_and_records_real_stops(tmp_path, monkeypatch, failure):
    session = Mock()
    session.read_physical_result.side_effect = [
        {
            "generation": 0,
            "qor_json": json.dumps({"summary": {"setup": {"wns": -1.0, "tns": -2.0}}}),
        },
        {
            "generation": 1,
            "qor_json": json.dumps({"summary": {"setup": {"wns": -3.0, "tns": -4.0}}}),
        },
    ]
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
            assert records[0]["wns_change_ns"] == -2.0
            assert records[0]["tns_change_ns"] == -2.0
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
    assert session.read_physical_result.call_args_list
    assert all(
        call.kwargs == {"summary_only": True}
        for call in session.read_physical_result.call_args_list
    )
