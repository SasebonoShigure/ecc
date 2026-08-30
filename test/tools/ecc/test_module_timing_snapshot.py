import pytest

from chipcompiler.tools.ecc import module as ecc_module
from chipcompiler.tools.ecc.sta_mode import (
    StaBackend,
    StaExecutionRequest,
    StaFallbackPolicy,
    StaUnsupportedError,
    StaUpdateStrategy,
    preflight_stage1_request,
)
from chipcompiler.tools.ecc.sta_snapshot import (
    StaAnalysisContext,
    StaSnapshotContractError,
    make_direct_sta_analysis_context,
)


def _request(backend=StaBackend.CPU):
    return StaExecutionRequest(
        backend=backend,
        update_strategy=StaUpdateStrategy.FULL,
        fallback_policy=StaFallbackPolicy.ERROR,
    )


class _Native:
    def __init__(self, events):
        self.events = events

    def lib_init(self, **kwargs):
        self.events.append(("lib", kwargs))

    def sdc_init(self, path):
        self.events.append(("sdc", path))

    def spef_init(self, path):
        self.events.append(("spef", path))


def _module(events):
    module = ecc_module.ECCToolsModule.__new__(ecc_module.ECCToolsModule)
    module.ecc = _Native(events)
    return module


def _install_success_boundary(monkeypatch, events, observation):
    class _Session:
        snapshot_observation = observation

        def __init__(self, native, request, context, **kwargs):
            self.request = request
            self.context = context
            events.append(("session", context, kwargs))

        def __enter__(self):
            events.append("enter")
            return self

        def run_full_baseline(self):
            events.append("run")
            return preflight_stage1_request(self.request)

        def __exit__(self, exc_type, exc, traceback):
            events.append("close")
            return False

    monkeypatch.setattr(ecc_module, "IncrementalStaSession", _Session)
    monkeypatch.setattr(
        ecc_module,
        "discard_sta_run_outputs",
        lambda *args: events.append(("discard", args)),
    )


def test_sink_runs_once_after_close_and_before_publish(tmp_path, monkeypatch):
    events = []
    observation = object()
    _install_success_boundary(monkeypatch, events, observation)
    monkeypatch.setattr(
        ecc_module,
        "publish_sta_artifacts",
        lambda **kwargs: events.append(("publish", kwargs)),
    )
    captured = []

    record = _module(events).run_timing(
        work_dir=tmp_path / "work",
        feature_dir=tmp_path / "feature",
        output_modes=("structured",),
        snapshot_observation_sink=lambda context, value: (
            events.append("sink"),
            captured.append((context, value)),
        ),
    )

    assert record == preflight_stage1_request(_request())
    assert captured == [(make_direct_sta_analysis_context(), observation)]
    assert [event if isinstance(event, str) else event[0] for event in events] == [
        "discard",
        "lib",
        "sdc",
        "spef",
        "session",
        "enter",
        "run",
        "close",
        "sink",
        "publish",
    ]


@pytest.mark.parametrize(
    ("modes", "report", "feature"),
    [
        (("report",), "shared", ""),
        (("structured",), "", "shared"),
    ],
)
def test_single_output_mode_allows_empty_inactive_destination(
    tmp_path, monkeypatch, modes, report, feature
):
    events = []
    _install_success_boundary(monkeypatch, events, None)
    monkeypatch.setattr(ecc_module, "publish_sta_artifacts", lambda **kwargs: None)

    _module(events).run_timing(
        work_dir=tmp_path / "work",
        report_dir=tmp_path / report if report else "",
        feature_dir=tmp_path / feature if feature else "",
        output_modes=modes,
    )

    assert "run" in events


def test_context_alias_and_capability_preflight_have_zero_side_effects(tmp_path, monkeypatch):
    events = []
    module = _module(events)
    monkeypatch.setattr(
        ecc_module,
        "discard_sta_run_outputs",
        lambda *args: events.append("discard"),
    )
    request = _request(StaBackend.CUDA)

    invalid = StaAnalysisContext(
        liberty_corner="",
        temperature="__unspecified_temperature__",
        rc_corner="__no_rc_corner__",
    )
    with pytest.raises(StaSnapshotContractError):
        module.run_timing(
            work_dir=tmp_path / "work",
            report_dir=tmp_path / "report",
            feature_dir=tmp_path / "feature",
            analysis_context=invalid,
            execution_request=request,
        )
    assert events == []

    shared = tmp_path / "shared"
    with pytest.raises(ValueError, match="must not alias"):
        module.run_timing(
            work_dir=tmp_path / "work",
            report_dir=shared,
            feature_dir=shared,
            execution_request=request,
        )
    assert events == []

    target = tmp_path / "alias-target"
    target.mkdir()
    report_link = tmp_path / "report-link"
    feature_link = tmp_path / "feature-link"
    report_link.symlink_to(target, target_is_directory=True)
    feature_link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="must not alias"):
        module.run_timing(
            work_dir=tmp_path / "work",
            report_dir=report_link,
            feature_dir=feature_link,
            execution_request=request,
        )
    assert events == []

    with pytest.raises(ValueError, match="must be callable"):
        module.run_timing(
            work_dir=tmp_path / "work",
            report_dir=tmp_path / "report",
            feature_dir=tmp_path / "feature",
            snapshot_observation_sink=object(),
        )
    assert events == []

    with pytest.raises(StaUnsupportedError):
        module.run_timing(
            work_dir=tmp_path / "work",
            report_dir=tmp_path / "report",
            feature_dir=tmp_path / "feature",
            execution_request=request,
        )
    assert events == []


def test_spef_consistency_precedes_capability_and_native_setup(tmp_path):
    events = []
    module = _module(events)

    with pytest.raises(StaSnapshotContractError):
        module.run_timing(
            work_dir=tmp_path / "work",
            report_dir=tmp_path / "report",
            feature_dir=tmp_path / "feature",
            spef_path=tmp_path / "corner.spef",
            execution_request=_request(StaBackend.CUDA),
        )

    assert events == []


def test_sink_failure_prevents_publish(tmp_path, monkeypatch):
    events = []
    _install_success_boundary(monkeypatch, events, None)
    monkeypatch.setattr(
        ecc_module,
        "publish_sta_artifacts",
        lambda **kwargs: events.append("publish"),
    )
    sink_calls = []

    def fail_sink(context, observation):
        sink_calls.append((context, observation))
        raise RuntimeError("sink failed")

    with pytest.raises(RuntimeError, match="sink failed"):
        _module(events).run_timing(
            work_dir=tmp_path / "work",
            feature_dir=tmp_path / "feature",
            output_modes=("structured",),
            snapshot_observation_sink=fail_sink,
        )

    assert len(sink_calls) == 1
    assert "publish" not in events


def test_publish_failure_happens_after_one_successful_sink(tmp_path, monkeypatch):
    events = []
    observation = object()
    _install_success_boundary(monkeypatch, events, observation)

    def fail_publish(**kwargs):
        events.append("publish")
        raise RuntimeError("publish failed")

    monkeypatch.setattr(ecc_module, "publish_sta_artifacts", fail_publish)
    captured = []

    with pytest.raises(RuntimeError, match="publish failed"):
        _module(events).run_timing(
            work_dir=tmp_path / "work",
            feature_dir=tmp_path / "feature",
            output_modes=("structured",),
            snapshot_observation_sink=lambda context, value: captured.append((context, value)),
        )

    assert captured == [(make_direct_sta_analysis_context(), observation)]
    assert events[-1] == "publish"
