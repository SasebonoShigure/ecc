import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from chipcompiler.data import StepEnum, Workspace
from chipcompiler.rtl2gds import get_flow_builders
from chipcompiler.tools.ecc import runner
from chipcompiler.tools.ecc.builder import build_step
from chipcompiler.tools.ecc.physical_artifacts import PhysicalArtifacts


def test_experimental_routing_loads_manifest_instead_of_old_db(tmp_path, monkeypatch):
    workspace = Workspace(directory=tmp_path)
    workspace.flow.data["steps"] = [
        {"name": step.value, "tool": tool}
        for step, tool, _ in get_flow_builders()["incregpusta_experimental"]()
    ]
    output = tmp_path / "timing_opt_ecc" / "output"
    products = tmp_path / "immutable-generation-2"
    products.mkdir()
    files = {name: products / name for name in ("design.def", "design.v")}
    for path in files.values():
        path.write_text("current")
    old_def = tmp_path / "old.def"
    old_def.write_text("old")
    step = build_step(
        workspace, StepEnum.ROUTING.value, old_def, None, input_db=output / "stale_db"
    )
    read = Mock(return_value=PhysicalArtifacts(2, products, files))
    monkeypatch.setattr("chipcompiler.tools.ecc.physical_runner.read_physical_artifacts", read)
    module = Mock()
    module.read_def.return_value = True
    monkeypatch.setattr(runner, "is_eda_exist", lambda: True)
    monkeypatch.setattr(runner, "ECCToolsModule", Mock(return_value=module))
    assert runner.create_db_engine(workspace, step) is module
    assert (step.input.def_, step.input.verilog) == (files["design.def"], files["design.v"])
    module.is_db_data_exists.assert_not_called()
    module.load_data.assert_not_called()
    module.read_def.assert_called_once_with(str(files["design.def"]))
    read.assert_called_once_with(output / "physical_session")
    module.read_def.return_value = False
    module.reset_mock()
    with pytest.raises(RuntimeError, match="rejected the current"):
        runner.create_db_engine(workspace, step)
    module.read_def.assert_called_once_with(str(files["design.def"]))
    module.load_data.assert_not_called()
    # A later stale/partial manifest must fail before creating or loading any DB.
    read.side_effect = ValueError("stale generation")
    module.reset_mock()
    with pytest.raises(ValueError, match="stale"):
        runner.create_db_engine(workspace, step)
    assert not module.mock_calls


def test_regular_preset_keeps_existing_database_loading(tmp_path, monkeypatch):
    workspace = Workspace(directory=tmp_path)
    workspace.flow.data["steps"] = [
        {"name": step.value, "tool": tool} for step, tool, _ in get_flow_builders()["rtl2gds"]()
    ]
    source = tmp_path / "baseline.def"
    source.write_text("baseline")
    step = build_step(workspace, StepEnum.ROUTING.value, source, None, input_db=Path("existing_db"))
    module = Mock()
    module.is_db_data_exists.return_value = True
    module.load_data.return_value = True
    monkeypatch.setattr(runner, "is_eda_exist", lambda: True)
    monkeypatch.setattr(runner, "ECCToolsModule", Mock(return_value=module))
    assert runner.create_db_engine(workspace, step) is module
    module.load_data.assert_called_once_with(path=Path("existing_db"))
    module.read_def.assert_not_called()


@pytest.mark.parametrize("failure", [None, "report", "configuration"])
def test_physical_entry_filters_pdk_patterns_and_publishes_committed_generation(
    tmp_path, monkeypatch, failure
):
    from chipcompiler.tools.ecc import physical_runner

    workspace = Workspace(directory=tmp_path)
    workspace.flow.data["steps"] = [
        {"name": step.value, "tool": tool}
        for step, tool, _ in get_flow_builders()["incregpusta_experimental"]()
    ]
    inputs = tmp_path / "inputs"
    inputs.write_text("fixture")
    workspace.pdk.tech = inputs
    workspace.pdk.lefs = [inputs]
    workspace.pdk.libs = [inputs]
    workspace.pdk.sdc = inputs
    workspace.pdk.buffers = ["BUF_SMALL", "BUF_LARGE", "BUF_FORBIDDEN", "BUF_SMALL"]
    workspace.pdk.dont_use = ["*_FORBIDDEN", "BUF_L?RGE"]
    routing = tmp_path / "routing.json"
    routing.write_text(
        json.dumps({"RT": {"-bottom_routing_layer": "M1", "-top_routing_layer": "M5"}})
    )
    workspace.config[StepEnum.ROUTING.value] = routing
    workspace.parameters.data["incregpusta"] = {"max_rounds": 2}
    step = build_step(workspace, StepEnum.TIMING_OPT.value, inputs, inputs)
    session = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=session)
    context.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(physical_runner, "IncrementalStaSession", Mock(return_value=context))
    result = {"generation": 2, "rounds": 2, "buffers": 3, "stop_reason": "round_budget_exhausted"}

    def commits(*args, **kwargs):
        journal = Path(step.output.dir) / "physical_session"
        journal.mkdir()
        (journal / "baseline.json").write_text("{}")
        for index, edits in ((1, [1, 2]), (2, [3])):
            (journal / f"committed-{index}.json").write_text(json.dumps({"edits": edits}))
        return result

    greedy = Mock(side_effect=commits)
    monkeypatch.setattr(physical_runner, "run_physical_greedy", greedy)
    products = {"design.def": tmp_path / "current.def", "design.v": tmp_path / "current.v"}
    monkeypatch.setattr(
        physical_runner,
        "read_physical_artifacts",
        Mock(return_value=PhysicalArtifacts(2, tmp_path, products)),
    )
    module = Mock()

    def geometry_snapshot_save(*, output_dir):
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        step.output.geometry_manifest.write_text("current geometry")
        return True

    module.geometry_snapshot_save.side_effect = geometry_snapshot_save
    if failure == "configuration":
        write_text = Path.write_text

        def interrupted_config(path, *args, **kwargs):
            if path.parent.name.startswith(".greedy-config-"):
                write_text(path, "{")
                raise OSError("configuration output failed")
            return write_text(path, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", interrupted_config)
        with pytest.raises(OSError, match="configuration output"):
            physical_runner.run_physical_timing_opt(workspace, step, module)
        assert not (Path(step.output.dir) / "greedy-config.json").exists()
        assert not list(Path(step.output.dir).glob(".greedy-config-*"))
        session.run_physical_baseline.assert_not_called()
        monkeypatch.setattr(Path, "write_text", write_text)
    if failure == "report":
        from types import SimpleNamespace

        session.publish_physical_artifacts.side_effect = [
            OSError("report output unavailable"),
            None,
        ]
        session.recover_physical_baseline.return_value = SimpleNamespace(generation=2)
        with pytest.raises(OSError, match="report output"):
            physical_runner.run_physical_timing_opt(workspace, step, module)
        assert (Path(step.output.dir) / "physical_session/committed-2.json").is_file()
    assert physical_runner.run_physical_timing_opt(workspace, step, module)
    session.run_physical_baseline.assert_called_once()
    if failure == "report":
        session.recover_physical_baseline.assert_called_once()
        module.read_def.assert_called_once_with(str(inputs))
    greedy.assert_called_once_with(
        session,
        ["BUF_SMALL"],
        Path(step.output.dir) / "greedy.jsonl",
        top_k=100,
        max_rounds=2,
        max_buffers=1000,
        committed_buffers=0,
        generation=0,
    )
    assert session.publish_physical_artifacts.call_count == (2 if failure == "report" else 1)
    session.publish_physical_artifacts.assert_called_with(expected_generation=2)
    from chipcompiler.engine.flow import EngineFlow

    for path in products.values():
        path.write_text("current")
    monkeypatch.setattr(
        "chipcompiler.tools.ecc.physical_artifacts.read_physical_artifacts",
        Mock(return_value=PhysicalArtifacts(2, tmp_path, products)),
    )
    assert EngineFlow.check_step_result(None, step)
    step.output.geometry_manifest.unlink()
    assert not EngineFlow.check_step_result(None, step)
    assert (step.output.def_, step.output.verilog) == (products["design.def"], products["design.v"])


def test_sizer_timing_opt_does_not_use_physical_handoff(tmp_path):
    from chipcompiler.tools.ecc.physical_runner import bind_physical_routing_input

    workspace = Workspace(directory=tmp_path)
    workspace.flow.data["steps"] = [
        {"name": step.value, "tool": "sizer" if step is StepEnum.TIMING_OPT else tool}
        for step, tool, _ in get_flow_builders()["incregpusta_experimental"]()
    ]
    step = build_step(workspace, StepEnum.ROUTING.value, None, None)
    assert not bind_physical_routing_input(workspace, step)
