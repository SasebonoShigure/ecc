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
from chipcompiler.tools.ecc.sta_mode import StaUnsupportedError


class _FakeLogger:
    def __init__(self):
        self.warnings = []

    def warning(self, message, *args):
        self.warnings.append((message, args))


def _write_stale_files(paths):
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"stale\n")


def _write(path, text=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_post_synthesis_cuda_preflight_preserves_stale_artifacts(tmp_path, monkeypatch):
    netlist = _write(tmp_path / "output" / "gcd.v")
    liberty = _write(tmp_path / "pdk" / "std.lib")
    sdc = _write(tmp_path / "pdk" / "gcd.sdc")
    _write(tmp_path / "config" / "sta.json", "{}")

    logger = _FakeLogger()
    workspace = Workspace(
        directory=tmp_path,
        design=OriginDesign(name="gcd", top_module="gcd"),
        pdk=PDK(libs=[liberty], sdc=sdc),
        parameters=Parameters(
            data={
                "STA backend": "cuda",
                "STA update strategy": "full",
                "STA fallback policy": "full_with_record",
            }
        ),
        logger=logger,
    )
    step = EccStep(
        output=EccOutput(verilog=netlist),
        data=EccData(dir=tmp_path / "data"),
        feature=EccFeature(dir=tmp_path / "feature"),
        report=EccReport(dir=tmp_path / "report"),
    )
    stale_files = (
        step.feature.dir / "post_synthesis" / "qor_summary.json",
        step.report.dir / "post_synthesis" / "qor_summary.rpt",
    )
    _write_stale_files(stale_files)
    constructor_calls = []

    def fail_module_constructor():
        constructor_calls.append(())
        raise AssertionError("ECCToolsModule construction must not run")

    monkeypatch.setattr(ecc_runner, "ECCToolsModule", fail_module_constructor)

    assert ecc_runner.run_sta_without_spef(workspace, step, ecc_module=None) is False

    assert constructor_calls == []
    assert [path.read_bytes() for path in stale_files] == [b"stale\n", b"stale\n"]
    assert len(logger.warnings) == 1
    message, arguments = logger.warnings[0]
    assert message == "Post-synthesis STA failed; synthesis result is kept: %s"
    assert len(arguments) == 1
    assert isinstance(arguments[0], StaUnsupportedError)


def test_signoff_cuda_preflight_precedes_engine_creation(tmp_path, monkeypatch):
    liberty = _write(tmp_path / "pdk" / "max.lib")
    sdc = _write(tmp_path / "pdk" / "gcd.sdc")
    _write(tmp_path / "RCX_ecc" / "output" / "gcd_RCworst_125C.spef")
    _write(
        tmp_path / "config" / "sta.json",
        json.dumps(
            {
                "liberty": [{"corner": "MAX", "temperature": 125, "path": [str(liberty)]}],
                "signoff": [{"MAX": ["RCworst"]}],
            }
        ),
    )

    logger = _FakeLogger()
    workspace = Workspace(
        directory=tmp_path,
        design=OriginDesign(name="gcd", top_module="gcd"),
        pdk=PDK(sdc=sdc),
        parameters=Parameters(
            data={
                "STA backend": "cuda",
                "STA update strategy": "incremental",
                "STA fallback policy": "error",
            }
        ),
        logger=logger,
    )
    step = EccStep(
        data=EccData(steps={StepEnum.STA.value: tmp_path / "data" / "sta"}),
        feature=EccFeature(dir=tmp_path / "feature"),
        report=EccReport(dir=tmp_path / "report"),
    )
    stale_files = (
        step.feature.dir / "MAX_125" / "RCworst" / "qor_summary.json",
        step.report.dir / "MAX_125" / "RCworst" / "qor_summary.rpt",
    )
    _write_stale_files(stale_files)
    engine_calls = []

    def fail_engine_creation(**kwargs):
        engine_calls.append(kwargs)
        raise AssertionError("engine creation must not run")

    monkeypatch.setattr(ecc_runner, "get_eda_instance", fail_engine_creation)

    with pytest.raises(StaUnsupportedError) as raised:
        ecc_runner.run_sta(workspace, step)

    assert raised.value.request.backend.value == "cuda"
    assert engine_calls == []
    assert [path.read_bytes() for path in stale_files] == [b"stale\n", b"stale\n"]
