#!/usr/bin/env python
from pathlib import Path
from types import SimpleNamespace

from chipcompiler.utility import json_write
from chipcompiler.data import (
    HomeData,
    OriginDesign,
    StateEnum,
    StepEnum,
    Workspace,
    WorkspaceStep,
    get_design_parameters,
    get_pdk,
)
from chipcompiler.engine.flow import EngineFlow


REPO_ROOT = Path(__file__).resolve().parents[2]
ICS55_PDK_ROOT = REPO_ROOT / "test" / "icsprout55-pdk"
GCD_RTL = REPO_ROOT / "test" / "fixtures" / "gcd" / "gcd.v"


def _workspace(tmp_path: Path) -> Workspace:
    parameters = get_design_parameters("ics55", "gcd")
    pdk = get_pdk("ics55", pdk_root=str(ICS55_PDK_ROOT))

    return Workspace(
        directory=str(tmp_path / "ws"),
        design=OriginDesign(
            name=parameters.data["Design"],
            top_module=parameters.data["Top module"],
            origin_verilog=str(GCD_RTL),
        ),
        pdk=pdk,
        parameters=parameters,
        home=HomeData(),
    )


def _write_gcd_netlist_pair(gate: Path) -> None:
    gate.parent.mkdir(parents=True)
    gcd_text = GCD_RTL.read_text()
    gate.write_text(gcd_text)
    gate.with_name("gcd_Synthesis_golden.v").write_text(gcd_text)


def test_yosys_build_step_exposes_rtl_derived_golden_path(tmp_path):
    from chipcompiler.tools.yosys import builder

    assert GCD_RTL.is_file()

    workspace = _workspace(tmp_path)
    step = builder.build_step(
        workspace=workspace,
        step_name=StepEnum.SYNTHESIS.value,
        input_def="",
        input_verilog=str(GCD_RTL),
    )

    assert workspace.pdk.name == "ics55"
    assert workspace.design.top_module == "gcd"
    assert step.input["verilog"] == str(GCD_RTL)
    assert step.output["verilog"].endswith("/gcd_Synthesis.v")
    assert step.output["golden_verilog"].endswith("/gcd_Synthesis_golden.v")


def test_yosys_global_var_tcl_includes_golden_netlist_path(tmp_path):
    from chipcompiler.tools.yosys import builder

    workspace = _workspace(tmp_path)
    workspace.design.input_filelist = ""
    step = builder.build_step(
        workspace=workspace,
        step_name=StepEnum.SYNTHESIS.value,
        input_def="",
        input_verilog=str(GCD_RTL),
    )

    tcl = builder.generate_global_var_tcl(workspace=workspace, step=step)

    assert f"set rtl_file            [split {GCD_RTL}]" in tcl
    assert "set top_design              gcd" in tcl
    assert "set golden_netlist_file" in tcl
    assert step.output["golden_verilog"] in tcl


def test_lec_builder_derives_golden_from_gate_netlist_and_creates_workspace(tmp_path):
    from chipcompiler.tools.yosys_lec import builder

    workspace = _workspace(tmp_path)
    gate = tmp_path / "Synthesis_yosys" / "output" / "gcd_Synthesis.v"

    step = builder.build_step(
        workspace=workspace,
        step_name=StepEnum.LEC.value,
        input_def="",
        input_verilog=str(gate),
    )
    builder.build_step_space(step)

    assert step.tool == "yosys_lec"
    assert workspace.pdk.name == "ics55"
    assert workspace.design.origin_verilog == str(GCD_RTL)
    assert step.input["gate_verilog"] == str(gate)
    assert step.input["golden_verilog"] == str(gate.with_name("gcd_Synthesis_golden.v"))
    assert Path(step.script["main"]).name == "run_lec.tcl"
    assert Path(step.output["json"]).name == "gcd_lec_result.json"
    assert Path(step.script["dir"]).is_dir()
    assert Path(step.report["dir"]).is_dir()


def test_lec_builder_accepts_explicit_golden_netlist(tmp_path):
    from chipcompiler.tools.yosys_lec import builder

    workspace = _workspace(tmp_path)
    golden = tmp_path / "Synthesis_yosys" / "output" / "gcd_Synthesis.v"
    gate = tmp_path / "route_ecc" / "output" / "gcd_route.v"

    step = builder.build_step(
        workspace=workspace,
        step_name=StepEnum.POST_ROUTE_LEC.value,
        input_def="",
        input_verilog=str(gate),
        input_db=str(golden),
    )

    assert step.input["gate_verilog"] == str(gate)
    assert step.input["golden_verilog"] == str(golden)
    assert Path(step.output["json"]).name == "gcd_postRouteLec_result.json"


def test_lec_build_step_config_writes_ics55_gcd_models_and_repo_local_script(tmp_path):
    from chipcompiler.tools.yosys_lec import builder

    workspace = _workspace(tmp_path)
    gate = tmp_path / "Synthesis_yosys" / "output" / "gcd_Synthesis.v"
    _write_gcd_netlist_pair(gate)

    step = builder.build_step(
        workspace=workspace,
        step_name=StepEnum.LEC.value,
        input_def="",
        input_verilog=str(gate),
    )
    builder.build_step_space(step)
    builder.build_step_config(workspace=workspace, step=step)

    config = Path(step.data["config"]).read_text()
    script = Path(step.script["main"]).read_text()

    assert str(gate) in config
    assert str(gate.with_name("gcd_Synthesis_golden.v")) in config
    for lib in workspace.pdk.libs:
        assert Path(lib).is_file()
        assert lib in config
    assert "stdcell.lib" not in config
    assert "set use_undef true" in config
    assert "splitnets -ports -format __v" in script
    assert "equiv_make" in script
    assert "/home/zhaoxueyan/code/yosys-flow1" not in script


def test_lec_runner_marks_success_from_yosys_status(tmp_path, monkeypatch):
    from chipcompiler.tools.yosys_lec import builder, runner

    workspace = _workspace(tmp_path)
    gate = tmp_path / "Synthesis_yosys" / "output" / "gcd_Synthesis.v"
    _write_gcd_netlist_pair(gate)

    step = builder.build_step(
        workspace=workspace,
        step_name=StepEnum.LEC.value,
        input_def="",
        input_verilog=str(gate),
    )
    builder.build_step_space(step)
    builder.build_step_config(workspace=workspace, step=step)

    updates = []

    class FakeSubFlow:
        def __init__(self, workspace, workspace_step):
            pass

        def update_step(self, step_name, state, info=None):
            updates.append((step_name, state))

    def fake_run(cmd, cwd, env, stdout, stderr):
        Path(step.report["equiv_status"]).write_text("Equivalence successfully proven!\n")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner, "YosysLecSubFlow", FakeSubFlow)
    monkeypatch.setattr(runner, "get_yosys_runtime", lambda: (["yosys"], {"PATH": "/tmp"}))
    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    assert runner.run_step(workspace=workspace, step=step) is True
    assert ("run lec", StateEnum.Success) in updates
    assert Path(step.output["json"]).exists()


def test_engine_flow_accepts_lec_result_json(tmp_path):
    result_json = tmp_path / "lec_result.json"
    result_json.write_text('{"status": "proven"}\n')
    step = WorkspaceStep(name=StepEnum.LEC.value, output={"json": str(result_json)})

    assert EngineFlow(workspace=None).check_step_result(step) is True


def test_post_route_lec_flow_appends_lec_after_route():
    from chipcompiler.rtl2gds import build_post_route_lec_flow

    steps = build_post_route_lec_flow()

    assert steps[-2][0] == StepEnum.ROUTING
    assert steps[-1] == (StepEnum.POST_ROUTE_LEC, "yosys_lec", StateEnum.Unstart)


def test_engine_flow_wires_post_route_lec_against_synthesis_gate(tmp_path, monkeypatch):
    import chipcompiler.tools as tools

    workspace = _workspace(tmp_path)
    workspace.flow.path = str(tmp_path / "flow.json")
    workspace.flow.data = {
        "steps": [
            {"name": StepEnum.SYNTHESIS.value, "tool": "yosys", "state": StateEnum.Unstart.value},
            {"name": StepEnum.ROUTING.value, "tool": "ecc", "state": StateEnum.Unstart.value},
            {
                "name": StepEnum.POST_ROUTE_LEC.value,
                "tool": "yosys_lec",
                "state": StateEnum.Unstart.value,
            },
        ]
    }
    json_write(workspace.flow.path, workspace.flow.data)

    def fake_create_step(
        workspace,
        step,
        eda,
        input_def,
        input_verilog,
        input_db=None,
        **kwargs,
    ):
        workspace_step = WorkspaceStep()
        workspace_step.name = step
        workspace_step.tool = eda
        workspace_step.input = {
            "def": input_def,
            "verilog": input_verilog,
            "db": input_db,
        }
        workspace_step.output = {
            "def": str(tmp_path / step / "output" / f"gcd_{step}.def.gz"),
            "verilog": str(tmp_path / step / "output" / f"gcd_{step}.v"),
            "golden_verilog": str(tmp_path / step / "output" / f"gcd_{step}_golden.v"),
            "db": str(tmp_path / step / "output" / f"gcd_{step}_db"),
        }
        if eda == "yosys_lec":
            workspace_step.input = {
                "gate_verilog": input_verilog,
                "golden_verilog": input_db,
                "db": input_db,
            }
        return workspace_step

    monkeypatch.setattr(tools, "create_step", fake_create_step)

    engine_flow = EngineFlow(workspace=workspace)
    engine_flow.create_step_workspaces()

    synth_step, route_step, lec_step = engine_flow.workspace_steps
    assert synth_step.name == StepEnum.SYNTHESIS.value
    assert route_step.name == StepEnum.ROUTING.value
    assert lec_step.name == StepEnum.POST_ROUTE_LEC.value
    assert lec_step.input["gate_verilog"] == route_step.output["verilog"]
    assert lec_step.input["golden_verilog"] == synth_step.output["verilog"]
