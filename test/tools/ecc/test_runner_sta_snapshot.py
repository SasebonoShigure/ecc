import inspect
import json

import pytest

from chipcompiler.data import (
    PDK,
    EccData,
    EccFeature,
    EccOutput,
    EccReport,
    EccStep,
    OriginDesign,
    Parameters,
    StepEnum,
    Workspace,
)
from chipcompiler.tools.ecc import runner as ecc_runner
from chipcompiler.tools.ecc.sta_mode import (
    StaExecutionContractError,
    StaUnsupportedError,
    preflight_stage1_request,
)
from chipcompiler.tools.ecc.sta_snapshot import (
    StaAnalysisContext,
    make_direct_sta_analysis_context,
)


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class _Logger:
    def __init__(self):
        self.infos = []
        self.warnings = []
        self.errors = []

    def info(self, message, *args):
        self.infos.append((message, args))

    def warning(self, message, *args):
        self.warnings.append((message, args))

    def error(self, message, *args):
        self.errors.append((message, args))


class _SubFlow:
    def __init__(self, *args, **kwargs):
        self.updates = []

    def update_step(self, **kwargs):
        self.updates.append(kwargs)


def _direct_case(tmp_path, *, create_sdc=True, parameters=None):
    netlist = _write(tmp_path / "output" / "gcd.v")
    tech = _write(tmp_path / "pdk" / "tech.lef")
    lef = _write(tmp_path / "pdk" / "std.lef")
    liberty = _write(tmp_path / "pdk" / "std.lib")
    sdc = tmp_path / "pdk" / "gcd.sdc"
    if create_sdc:
        _write(sdc)
    config = _write(tmp_path / "config" / "sta.json", "{}")
    workspace = Workspace(
        directory=tmp_path,
        design=OriginDesign(name="gcd", top_module="gcd"),
        pdk=PDK(tech=tech, lefs=[lef], libs=[liberty], sdc=sdc),
        config={"flow": tmp_path / "config" / "flow.json", "db": tmp_path / "config" / "db.json"},
        parameters=Parameters(data=parameters or {}),
        logger=_Logger(),
    )
    step = EccStep(
        output=EccOutput(verilog=netlist),
        data=EccData(dir=tmp_path / "Synthesis_yosys" / "data"),
        report=EccReport(dir=tmp_path / "Synthesis_yosys" / "report"),
        feature=EccFeature(dir=tmp_path / "Synthesis_yosys" / "feature"),
    )
    return workspace, step, config


class _DirectModule:
    def __init__(self):
        self.calls = []

    def init_config(self, **kwargs):
        self.calls.append(("init_config", kwargs))

    def update_step_paths(self, **kwargs):
        self.calls.append(("update_step_paths", kwargs))

    def init_techlef(self, path):
        self.calls.append(("init_techlef", path))

    def init_lefs(self, paths):
        self.calls.append(("init_lefs", paths))

    def read_verilog(self, **kwargs):
        self.calls.append(("read_verilog", kwargs))

    def run_timing(self, **kwargs):
        self.calls.append(("run_timing", kwargs))
        kwargs["snapshot_observation_sink"](
            kwargs["analysis_context"],
            None,
        )
        return preflight_stage1_request(kwargs["execution_request"])


def test_direct_success_locks_regular_config_context_and_sink_kwargs(tmp_path, monkeypatch):
    workspace, step, config = _direct_case(tmp_path)
    module = _DirectModule()
    monkeypatch.setattr(ecc_runner, "ECCToolsModule", lambda: module)

    assert ecc_runner.run_sta_without_spef(workspace, step) is True

    name, kwargs = module.calls[-1]
    assert name == "run_timing"
    sink = kwargs.pop("snapshot_observation_sink")
    context = kwargs.pop("analysis_context")
    assert callable(sink)
    assert context == make_direct_sta_analysis_context()
    assert kwargs["config"] == str(config)
    assert kwargs["work_dir"] == str(step.data.dir / "sta")
    assert kwargs["report_dir"] == step.report.dir / "post_synthesis"
    assert kwargs["feature_dir"] == step.feature.dir / "post_synthesis"
    assert kwargs["lib_paths"] == (str(workspace.pdk.libs[0]),)
    assert kwargs["sdc_path"] == str(workspace.pdk.sdc)
    assert (step.data.dir / "sta").is_dir()
    assert workspace.logger.warnings == []


_DIRECT_RAW_ERRORS = {
    "missing_netlist": (FileNotFoundError, "synthesis netlist"),
    "missing_liberty": (FileNotFoundError, "STA liberty[0]"),
    "missing_config": (FileNotFoundError, "STA config"),
    "missing_sdc": (FileNotFoundError, "STA SDC"),
    "empty_liberties": (ValueError, "liberty list"),
    "direct_alias": (ValueError, "must not alias"),
    "symlink_alias": (ValueError, "must not alias"),
    "nonbool_max_paths": (ValueError, "positive nonbool integer"),
}


def _invalidate_direct_case(tmp_path, workspace, step, config, problem):
    if problem == "missing_netlist":
        step.output.verilog.unlink()
    elif problem == "missing_liberty":
        workspace.pdk.libs[0].unlink()
    elif problem == "missing_config":
        config.unlink()
    elif problem == "missing_sdc":
        workspace.pdk.sdc.unlink()
    elif problem == "empty_liberties":
        workspace.pdk.libs.clear()
    elif problem == "direct_alias":
        step.feature.dir = step.report.dir
    elif problem == "symlink_alias":
        alias_target = tmp_path / "resolved-alias"
        alias_target.mkdir()
        report_link = tmp_path / "report-alias"
        feature_link = tmp_path / "feature-alias"
        report_link.symlink_to(alias_target, target_is_directory=True)
        feature_link.symlink_to(alias_target, target_is_directory=True)
        step.report.dir = report_link
        step.feature.dir = feature_link
    elif problem == "nonbool_max_paths":
        workspace.parameters.data["STA max paths"] = True
    else:
        raise AssertionError(f"unknown direct preflight problem: {problem}")


def _assert_direct_invalid_raw_is_side_effect_free(tmp_path, monkeypatch, injected, *, problem):
    workspace, step, config = _direct_case(
        tmp_path,
        parameters={"STA backend": "cuda"},
    )
    stale = [
        _write(step.report.dir / "post_synthesis" / "qor_summary.rpt", "old-report"),
        _write(step.feature.dir / "post_synthesis" / "qor_summary.json", "old-feature"),
    ]
    _invalidate_direct_case(tmp_path, workspace, step, config, problem)
    work_dir = step.data.dir / "sta"
    parameters_before = dict(workspace.parameters.data)
    constructor_calls = []
    discard_calls = []
    sink_factory_calls = []
    record_log_calls = []
    snapshot_log_calls = []

    def fail_constructor():
        constructor_calls.append(None)
        raise AssertionError("constructor must not run")

    monkeypatch.setattr(ecc_runner, "ECCToolsModule", fail_constructor)
    monkeypatch.setattr(
        ecc_runner,
        "discard_sta_outputs",
        lambda path: discard_calls.append(path),
    )
    monkeypatch.setattr(
        ecc_runner,
        "_make_sta_snapshot_capture",
        lambda *args: sink_factory_calls.append(args),
    )
    monkeypatch.setattr(
        ecc_runner,
        "_log_sta_execution_record",
        lambda *args: record_log_calls.append(args),
    )
    monkeypatch.setattr(
        ecc_runner,
        "_log_sta_snapshot_observation",
        lambda *args: snapshot_log_calls.append(args),
    )
    module = _DirectModule() if injected else None

    assert ecc_runner.run_sta_without_spef(workspace, step, module) is False

    assert [path.read_text(encoding="utf-8") for path in stale] == [
        "old-report",
        "old-feature",
    ]
    assert not work_dir.exists()
    assert workspace.parameters.data == parameters_before
    assert constructor_calls == []
    assert discard_calls == []
    assert sink_factory_calls == []
    assert record_log_calls == []
    assert snapshot_log_calls == []
    assert workspace.logger.infos == []
    assert workspace.logger.errors == []
    assert len(workspace.logger.warnings) == 1
    raw_error = workspace.logger.warnings[0][1][0]
    expected_type, expected_text = _DIRECT_RAW_ERRORS[problem]
    assert isinstance(raw_error, expected_type)
    assert not isinstance(raw_error, StaUnsupportedError)
    assert expected_text in str(raw_error)
    if module is not None:
        assert module.calls == []


@pytest.mark.parametrize("problem", _DIRECT_RAW_ERRORS)
@pytest.mark.parametrize("injected", [False, True])
def test_direct_raw_preflight_dominates_cuda_without_side_effects(
    tmp_path, monkeypatch, problem, injected
):
    _assert_direct_invalid_raw_is_side_effect_free(
        tmp_path,
        monkeypatch,
        injected,
        problem=problem,
    )


def _signoff_case(tmp_path):
    max_lib = _write(tmp_path / "pdk" / "max.lib")
    min_lib = _write(tmp_path / "pdk" / "min.lib")
    sdc = _write(tmp_path / "pdk" / "gcd.sdc")
    _write(tmp_path / "RCX_ecc" / "output" / "gcd_RCworst_125C.spef")
    _write(tmp_path / "RCX_ecc" / "output" / "gcd_Cbest_m40C.spef")
    config = _write(
        tmp_path / "config" / "sta.json",
        json.dumps(
            {
                "liberty": [
                    {"corner": "MAX", "temperature": 125, "path": [str(max_lib)]},
                    {"corner": "MIN", "temperature": -40, "path": [str(min_lib)]},
                ],
                "signoff": [{"MAX": ["RCworst"], "MIN": ["Cbest"]}],
            }
        ),
    )
    workspace = Workspace(
        directory=tmp_path,
        design=OriginDesign(name="gcd", top_module="gcd"),
        pdk=PDK(sdc=sdc),
        parameters=Parameters(data={}),
        logger=_Logger(),
    )
    step = EccStep(
        name=StepEnum.STA.value,
        data=EccData(steps={StepEnum.STA.value: tmp_path / "sta_ecc" / "data" / "sta"}),
        report=EccReport(dir=tmp_path / "sta_ecc" / "report"),
        feature=EccFeature(dir=tmp_path / "sta_ecc" / "feature"),
    )
    return workspace, step, config


class _SignoffModule:
    def __init__(self):
        self.calls = []
        self.observations = []

    def run_timing(self, **kwargs):
        observation = object()
        self.observations.append(observation)
        kwargs["snapshot_observation_sink"](
            kwargs["analysis_context"],
            observation,
        )
        self.calls.append(kwargs)
        return preflight_stage1_request(kwargs["execution_request"])


def test_signoff_uses_isolated_exact_once_sink_per_frozen_corner(tmp_path, monkeypatch):
    workspace, step, _ = _signoff_case(tmp_path)
    module = _SignoffModule()
    logged = []
    monkeypatch.setattr(ecc_runner, "EccSubFlow", _SubFlow)
    monkeypatch.setattr(ecc_runner, "get_eda_instance", lambda **kwargs: module)
    monkeypatch.setattr(ecc_runner, "save_data", lambda **kwargs: True)
    monkeypatch.setattr(ecc_runner, "run_analysis", lambda **kwargs: None)
    monkeypatch.setattr(
        ecc_runner,
        "_log_sta_snapshot_observation",
        lambda workspace, context, observation: logged.append((context, observation)),
    )

    assert ecc_runner.run_sta(workspace, step, module) is True

    contexts = [call["analysis_context"] for call in module.calls]
    assert contexts == [
        StaAnalysisContext("MAX", "125", "RCworst"),
        StaAnalysisContext("MIN", "-40", "Cbest"),
    ]
    assert logged == list(zip(contexts, module.observations, strict=True))
    sinks = [call["snapshot_observation_sink"] for call in module.calls]
    assert sinks[0] is not sinks[1]
    for sink, context, observation in zip(sinks, contexts, module.observations, strict=True):
        with pytest.raises(StaExecutionContractError, match="only be called once"):
            sink(context, observation)
    assert [call["corner"] for call in module.calls] == [
        "MAX_125/RCworst",
        "MIN_m40/Cbest",
    ]


@pytest.mark.parametrize("injected", [False, True])
def test_invalid_second_signoff_corner_dominates_cuda_without_side_effects(
    tmp_path, monkeypatch, injected
):
    workspace, step, _ = _signoff_case(tmp_path)
    workspace.parameters.data["STA backend"] = "cuda"
    first_spef = tmp_path / "RCX_ecc" / "output" / "gcd_RCworst_125C.spef"
    missing_second_spef = tmp_path / "RCX_ecc" / "output" / "gcd_Cbest_m40C.spef"
    missing_second_spef.unlink()
    stale = [
        _write(step.report.dir / "MAX_125" / "RCworst" / "qor_summary.rpt", "max-report"),
        _write(step.feature.dir / "MAX_125" / "RCworst" / "qor_summary.json", "max-feature"),
        _write(step.report.dir / "MIN_m40" / "Cbest" / "qor_summary.rpt", "min-report"),
        _write(step.feature.dir / "MIN_m40" / "Cbest" / "qor_summary.json", "min-feature"),
    ]
    stale_bytes = [path.read_bytes() for path in stale]
    parameters_before = dict(workspace.parameters.data)
    work_dir = step.data.steps[StepEnum.STA.value]
    subflow_calls = []
    engine_calls = []
    discard_calls = []
    sink_factory_calls = []
    save_calls = []
    analysis_calls = []

    def fail_subflow(*args, **kwargs):
        subflow_calls.append((args, kwargs))
        raise AssertionError("subflow must not be constructed")

    def fail_engine(**kwargs):
        engine_calls.append(kwargs)
        raise AssertionError("engine must not be loaded")

    monkeypatch.setattr(ecc_runner, "EccSubFlow", fail_subflow)
    monkeypatch.setattr(ecc_runner, "get_eda_instance", fail_engine)
    monkeypatch.setattr(
        ecc_runner,
        "discard_sta_outputs",
        lambda path: discard_calls.append(path),
    )
    monkeypatch.setattr(
        ecc_runner,
        "_make_sta_snapshot_capture",
        lambda *args: sink_factory_calls.append(args),
    )
    monkeypatch.setattr(
        ecc_runner,
        "save_data",
        lambda **kwargs: save_calls.append(kwargs),
    )
    monkeypatch.setattr(
        ecc_runner,
        "run_analysis",
        lambda **kwargs: analysis_calls.append(kwargs),
    )
    module = _SignoffModule() if injected else None

    with pytest.raises(FileNotFoundError) as raised:
        ecc_runner.run_sta(workspace, step, module)

    assert first_spef.is_file()
    assert not missing_second_spef.exists()
    assert str(missing_second_spef) in str(raised.value)
    assert not isinstance(raised.value, StaUnsupportedError)
    assert [path.read_bytes() for path in stale] == stale_bytes
    assert not work_dir.exists()
    assert workspace.parameters.data == parameters_before
    assert subflow_calls == []
    assert engine_calls == []
    assert discard_calls == []
    assert sink_factory_calls == []
    assert save_calls == []
    assert analysis_calls == []
    assert workspace.logger.infos == []
    assert workspace.logger.warnings == []
    assert workspace.logger.errors == []
    if module is not None:
        assert module.calls == []


class _HardenModule:
    def __init__(self):
        self.calls = []

    def write_abstract_lef(self, **kwargs):
        self.calls.append(("write_abstract_lef", kwargs))

    def write_timing_model(self, **kwargs):
        self.calls.append(("write_timing_model", kwargs))

    def gds_save(self, **kwargs):
        self.calls.append(("gds_save", kwargs))


def test_legacy_collector_and_run_harden_keep_dict_contract(tmp_path, monkeypatch):
    workspace, _, config = _signoff_case(tmp_path)
    workspace.parameters = Parameters()
    step = EccStep(
        data=EccData(steps={StepEnum.STA.value: tmp_path / "harden" / "sta"}),
        output=EccOutput(
            lef=tmp_path / "harden" / "gcd.lef",
            lib=tmp_path / "harden" / "gcd.lib",
            gds=tmp_path / "harden" / "gcd.gds",
        ),
    )
    items = ecc_runner.collect_sta_signoff_items(workspace)
    assert list(inspect.signature(ecc_runner.collect_sta_signoff_items).parameters) == ["workspace"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    assert set(items[0]) == {
        "corner",
        "temperature",
        "rcx_corner",
        "liberty_files",
        "spef_file",
    }
    module = _HardenModule()
    monkeypatch.setattr(ecc_runner, "EccSubFlow", _SubFlow)
    monkeypatch.setattr(ecc_runner, "get_eda_instance", lambda **kwargs: module)
    monkeypatch.setattr(ecc_runner, "run_analysis", lambda **kwargs: None)

    assert ecc_runner.run_harden(workspace, step, module) is True

    timing = next(payload for name, payload in module.calls if name == "write_timing_model")
    assert timing["config"] == str(config)
    assert timing["lib_paths"] == items[0]["liberty_files"]
    assert timing["spef_path"] == items[0]["spef_file"]
