import json
from dataclasses import FrozenInstanceError

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
from chipcompiler.tools.ecc.sta_signoff import (
    preflight_sta_direct_run,
    preflight_sta_signoff_run,
)
from chipcompiler.tools.ecc.sta_snapshot import (
    StaAnalysisContext,
    make_direct_sta_analysis_context,
)


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _signoff_case(tmp_path, *, second_spef=True, shared_roots=False):
    max_lib = _write(tmp_path / "pdk" / "max.lib")
    min_lib = _write(tmp_path / "pdk" / "min.lib")
    sdc = _write(tmp_path / "pdk" / "gcd.sdc")
    first_spef = _write(tmp_path / "RCX_ecc" / "output" / "gcd_RCworst_125C.spef")
    second_path = tmp_path / "RCX_ecc" / "output" / "gcd_Cbest_m40C.spef"
    if second_spef:
        _write(second_path)
    config = {
        "liberty": [
            {"corner": "MAX", "temperature": 125, "path": [str(max_lib)]},
            {"corner": "MIN", "temperature": -40, "path": [str(min_lib)]},
        ],
        "signoff": [{"MAX": ["RCworst"], "MIN": ["Cbest"]}],
    }
    config_path = _write(
        tmp_path / "config" / "sta.json",
        json.dumps(config),
    )
    workspace = Workspace(
        directory=tmp_path,
        design=OriginDesign(name="gcd", top_module="gcd"),
        pdk=PDK(sdc=sdc),
        parameters=Parameters(data={"STA max paths": 37}),
    )
    report_root = tmp_path / "artifacts" / "report"
    feature_root = report_root if shared_roots else tmp_path / "artifacts" / "feature"
    step = EccStep(
        data=EccData(steps={StepEnum.STA.value: tmp_path / "work" / "sta"}),
        report=EccReport(dir=report_root),
        feature=EccFeature(dir=feature_root),
    )
    return workspace, step, config_path, config, first_spef, second_path


def test_signoff_preflight_freezes_order_context_and_destinations(tmp_path):
    workspace, step, config_path, _, first_spef, second_spef = _signoff_case(tmp_path)

    items = preflight_sta_signoff_run(workspace, step)

    assert isinstance(items, tuple)
    assert [item.artifact_corner for item in items] == [
        "MAX_125/RCworst",
        "MIN_m40/Cbest",
    ]
    assert [item.analysis_context for item in items] == [
        StaAnalysisContext("MAX", "125", "RCworst"),
        StaAnalysisContext("MIN", "-40", "Cbest"),
    ]
    assert [item.spef_path for item in items] == [str(first_spef), str(second_spef)]
    assert items[0].config == str(config_path)
    assert items[0].max_paths == 37
    assert items[0].report_dir == step.report.dir / "MAX_125" / "RCworst"
    assert items[1].feature_dir == step.feature.dir / "MIN_m40" / "Cbest"
    with pytest.raises(FrozenInstanceError):
        items[0].max_paths = 1
    assert not step.report.dir.exists()
    assert not step.feature.dir.exists()


def test_invalid_second_corner_is_pure_and_creates_no_artifacts(tmp_path):
    workspace, step, _, _, _, missing_spef = _signoff_case(tmp_path, second_spef=False)
    parameters_before = dict(workspace.parameters.data)

    with pytest.raises(FileNotFoundError, match="MIN/Cbest"):
        preflight_sta_signoff_run(workspace, step)

    assert not missing_spef.exists()
    assert not step.report.dir.exists()
    assert not step.feature.dir.exists()
    assert workspace.parameters.data == parameters_before


def test_report_feature_alias_is_rejected_without_mkdir(tmp_path):
    workspace, step, _, _, _, _ = _signoff_case(tmp_path, shared_roots=True)

    with pytest.raises(ValueError, match="globally unique"):
        preflight_sta_signoff_run(workspace, step)

    assert not step.report.dir.exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("liberty", [], "liberty outer"),
        ("signoff", [], "signoff outer"),
        ("signoff", [{"MAX": []}], "non-empty exact RC list"),
    ],
)
def test_empty_strict_containers_have_distinct_failures(tmp_path, field, value, message):
    workspace, step, config_path, config, _, _ = _signoff_case(tmp_path)
    config[field] = value
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        preflight_sta_signoff_run(workspace, step)

    assert not step.report.dir.exists()
    assert not step.feature.dir.exists()


def test_only_referenced_liberty_corner_requires_nonempty_file_list(tmp_path):
    workspace, step, config_path, config, _, _ = _signoff_case(tmp_path)
    config["liberty"].append({"corner": "UNUSED", "temperature": 25, "path": []})
    config_path.write_text(json.dumps(config), encoding="utf-8")
    assert len(preflight_sta_signoff_run(workspace, step)) == 2

    config["signoff"].append({"UNUSED": ["RCtyp"]})
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="must have files"):
        preflight_sta_signoff_run(workspace, step)


def test_sanitized_corner_collision_is_rejected(tmp_path):
    workspace, step, config_path, config, _, _ = _signoff_case(tmp_path)
    shared_lib = config["liberty"][0]["path"]
    config["liberty"] = [
        {"corner": "A/B", "temperature": 125, "path": shared_lib},
        {"corner": "A_B", "temperature": 125, "path": shared_lib},
    ]
    config["signoff"] = [{"A/B": ["RCworst"], "A_B": ["RCworst"]}]
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="artifact corner names"):
        preflight_sta_signoff_run(workspace, step)


def test_direct_preflight_requires_regular_inputs_and_freezes_context(tmp_path):
    netlist = _write(tmp_path / "output" / "gcd.v")
    liberty = _write(tmp_path / "pdk" / "std.lib")
    sdc = _write(tmp_path / "pdk" / "gcd.sdc")
    config = _write(tmp_path / "config" / "sta.json", "{}")
    workspace = Workspace(
        directory=tmp_path,
        design=OriginDesign(name="gcd", top_module="gcd"),
        pdk=PDK(libs=[liberty], sdc=sdc),
    )
    step = EccStep(
        output=EccOutput(verilog=netlist),
        data=EccData(dir=tmp_path / "data"),
        report=EccReport(dir=tmp_path / "report"),
        feature=EccFeature(dir=tmp_path / "feature"),
    )

    item = preflight_sta_direct_run(workspace, step)

    assert item.config == str(config)
    assert item.analysis_context == make_direct_sta_analysis_context()
    assert item.liberty_files == (str(liberty),)
    assert item.spef_path == ""
    assert item.report_dir == step.report.dir / "post_synthesis"
    assert item.feature_dir == step.feature.dir / "post_synthesis"
    assert not step.data.dir.exists()

    sdc.unlink()
    with pytest.raises(FileNotFoundError, match="STA SDC"):
        preflight_sta_direct_run(workspace, step)
    assert not step.data.dir.exists()
