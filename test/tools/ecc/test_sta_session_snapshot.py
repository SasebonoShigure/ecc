import json
from enum import Enum
from pathlib import Path

import pytest

from chipcompiler.tools.ecc import sta_session as sta_session_module
from chipcompiler.tools.ecc.sta_mode import (
    StaBackend,
    StaExecutionContractError,
    StaExecutionRequest,
    StaFallbackPolicy,
    StaUpdateStrategy,
    preflight_stage1_request,
)
from chipcompiler.tools.ecc.sta_session import IncrementalStaSession
from chipcompiler.tools.ecc.sta_snapshot import (
    StaSnapshotState,
    corner_fingerprint,
    make_direct_sta_analysis_context,
    sta_analysis_context_to_native_mapping,
)

READY_SNAPSHOT_PATH = (
    Path(__file__).parents[3]
    / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema"
    / "csr_snapshot_corpus_v1/baselines/ready_empty.json"
)
CONTEXT = make_direct_sta_analysis_context()


def _request(strategy):
    return StaExecutionRequest(
        backend=StaBackend.CPU,
        update_strategy=strategy,
        fallback_policy=StaFallbackPolicy.ERROR,
    )


def _record_mapping(request):
    record = preflight_stage1_request(request)
    return {
        name: value.value if isinstance(value, Enum) else value
        for name, value in vars(record).items()
    }


def _snapshot_mapping(token, state="ready"):
    mapping = json.loads(READY_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    mapping["state"] = state
    mapping["identity"]["session_token"] = token
    mapping["identity"]["corner_fingerprint"] = corner_fingerprint(CONTEXT)
    return mapping


class _NeverNativeError(RuntimeError):
    pass


class _NativeSession:
    def __init__(
        self,
        request,
        *,
        token=1,
        close_result=None,
        close_error=None,
        record_mapping=None,
        observation_script=None,
        released_error=None,
    ):
        self.request = request
        self.token = token
        self.close_result = close_result
        self.close_error = close_error
        self.released_error = released_error
        self.record_mapping = _record_mapping(request) if record_mapping is None else record_mapping
        self.observation_script = observation_script
        self.state = "created"
        self.token_reads = 0
        self.observation_reads = 0
        self.close_calls = 0
        self.initialized_context = None

    @property
    def session_token(self):
        self.token_reads += 1
        return self.token

    @property
    def csr_snapshot_observation(self):
        index = self.observation_reads
        self.observation_reads += 1
        if self.state == "closed" and self.released_error is not None:
            raise self.released_error
        if self.observation_script is not None:
            if index >= len(self.observation_script):
                raise AssertionError("unexpected snapshot observation read")
            value = self.observation_script[index]
            if isinstance(value, BaseException):
                raise value
            return value
        if self.request.update_strategy is StaUpdateStrategy.FULL:
            return None
        state = "released" if self.state == "closed" else "ready"
        return _snapshot_mapping(self.token, state)

    def initialize(self, *, analysis_context, config, config_dict):
        self.initialized_context = dict(analysis_context)
        self.state = "initialized"

    def run_full_baseline(self):
        self.state = "baseline_executed"
        return self.record_mapping

    def close(self):
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error
        self.state = "closed"
        return self.close_result


class _NativeModule:
    incregpusta_debug_checks_enabled = True

    StaSessionError = _NeverNativeError

    def __init__(self, request, **session_kwargs):
        self.request = request
        self.session = _NativeSession(request, **session_kwargs)
        self.factory_calls = 0

    def resolve_sta_execution(self, request):
        return _record_mapping(self.request)

    def create_incremental_sta_session(self, request):
        self.factory_calls += 1
        return self.session


def _assert_failed_session_terminal(session, native):
    assert session.state == "closed"
    assert session.snapshot_observation is None
    assert session._native_session is None
    assert session._active_observation is None
    assert session._snapshot_observation is None
    assert session._closed is True
    calls = (
        native.factory_calls,
        native.session.token_reads,
        native.session.observation_reads,
        native.session.close_calls,
    )
    session.close()
    assert calls == (
        native.factory_calls,
        native.session.token_reads,
        native.session.observation_reads,
        native.session.close_calls,
    )


def test_incremental_observation_is_token_bound_and_released_exactly_once():
    request = _request(StaUpdateStrategy.INCREMENTAL)
    native = _NativeModule(request)
    session = IncrementalStaSession(native, request, CONTEXT)

    with session:
        record = session.run_full_baseline()
        assert session.snapshot_observation is not None
        assert session.snapshot_observation.state is StaSnapshotState.READY

    assert record == preflight_stage1_request(request)
    assert session.snapshot_observation is not None
    assert session.snapshot_observation.state is StaSnapshotState.RELEASED
    assert session.snapshot_observation.identity.session_token == 1
    assert native.session.initialized_context == sta_analysis_context_to_native_mapping(CONTEXT)
    assert native.session.token_reads == 1
    assert native.session.observation_reads == 2
    assert native.session.close_calls == 1
    session.close()
    assert native.session.observation_reads == 2
    assert native.session.close_calls == 1


def test_full_session_keeps_observation_none_through_release():
    request = _request(StaUpdateStrategy.FULL)
    native = _NativeModule(request)

    with IncrementalStaSession(native, request, CONTEXT) as session:
        session.run_full_baseline()
        assert session.snapshot_observation is None

    assert session.snapshot_observation is None
    assert native.session.token_reads == 1
    assert native.session.observation_reads == 1


@pytest.mark.parametrize("token", [True, 0, -1, 1 << 64, "1"])
def test_session_token_is_an_exact_nonzero_uint64(token):
    request = _request(StaUpdateStrategy.FULL)
    native = _NativeModule(request, token=token)

    with (
        pytest.raises(StaExecutionContractError, match="nonzero uint64"),
        IncrementalStaSession(native, request, CONTEXT),
    ):
        pytest.fail("invalid token must prevent body entry")

    assert native.session.token_reads == 1
    assert native.session.close_calls == 1


def test_native_close_throw_skips_released_getter_and_clears_public_value():
    request = _request(StaUpdateStrategy.INCREMENTAL)
    close_error = RuntimeError("close failed")
    native = _NativeModule(request, close_error=close_error)
    session = IncrementalStaSession(native, request, CONTEXT)

    with pytest.raises(RuntimeError, match="close failed") as raised, session:
        session.run_full_baseline()
        assert session.snapshot_observation is not None

    assert raised.value is close_error
    assert native.session.observation_reads == 1
    _assert_failed_session_terminal(session, native)


@pytest.mark.parametrize("close_stage", ["clean", "native", "wrong_return"])
def test_body_contract_error_preserved_without_unrequested_observation(close_stage):
    request = _request(StaUpdateStrategy.FULL)
    bad_record = _record_mapping(request)
    bad_record["update_strategy"] = StaUpdateStrategy.INCREMENTAL.value
    cleanup_error = RuntimeError("close failed")
    native = _NativeModule(
        request,
        record_mapping=bad_record,
        close_error=cleanup_error if close_stage == "native" else None,
        close_result=False if close_stage == "wrong_return" else None,
    )
    session = IncrementalStaSession(native, request, CONTEXT)
    body_errors = []
    with pytest.raises(StaExecutionContractError) as raised, session:
        try:
            session.run_full_baseline()
        except StaExecutionContractError as body_error:
            body_errors.append(body_error)
            raise

    assert raised.value is body_errors[0]
    if close_stage == "wrong_return":
        assert isinstance(raised.value.__cause__, StaExecutionContractError)
        assert "close must return None" in str(raised.value.__cause__)
    else:
        assert raised.value.__cause__ is (cleanup_error if close_stage == "native" else None)
    assert native.session.close_calls == 1
    assert native.session.observation_reads == 0
    _assert_failed_session_terminal(session, native)


@pytest.mark.parametrize("release_failure", ["getter", "parse", "transition"])
def test_requested_observation_release_failure_clears_cached_value(release_failure, monkeypatch):
    request = _request(StaUpdateStrategy.INCREMENTAL)
    cleanup_error = RuntimeError("observation release failed")
    native = _NativeModule(request)
    session = IncrementalStaSession(native, request, CONTEXT)
    with pytest.raises(RuntimeError, match="observation release failed"), session:
        session.run_full_baseline()
        assert session.snapshot_observation is not None
        if release_failure == "getter":
            native.session.released_error = cleanup_error
        else:
            def fail(*_args):
                raise cleanup_error

            name = (
                "snapshot_observation_from_mapping"
                if release_failure == "parse"
                else "validate_snapshot_observation_transition"
            )
            monkeypatch.setattr(sta_session_module, name, fail)
    assert native.session.close_calls == 1
    assert native.session.observation_reads == 2
    _assert_failed_session_terminal(session, native)


@pytest.mark.parametrize("debug_checks", [False, True])
@pytest.mark.parametrize("request_observation", [False, True])
def test_build_flag_controls_explicit_observation_collection(debug_checks, request_observation):
    request = _request(StaUpdateStrategy.INCREMENTAL)
    native = _NativeModule(request)
    native.incregpusta_debug_checks_enabled = debug_checks
    with IncrementalStaSession(native, request, CONTEXT) as session:
        session.run_full_baseline()
        assert native.session.observation_reads == 0
        if request_observation:
            assert (session.snapshot_observation is not None) is debug_checks
            assert (session.snapshot_observation is not None) is debug_checks
    captured = debug_checks and request_observation
    assert native.session.close_calls == 1
    assert native.session.observation_reads == (2 if captured else 0)
    assert (session.snapshot_observation is not None) is captured


@pytest.mark.parametrize(
    "wrong_fingerprint",
    [
        "9e0c49b01171ddde3bf24e9ae4ebdfa92fdcc22ba4f4dcba65aff23eb1060caa",  # Old generic payload.
        "3e1ae07c69c21623632f49b62cac0604e6b62d5acabdd2ba5c992a08ea2d9de0",  # Different context.
    ],
)
def test_initial_snapshot_rejects_wrong_corner_fingerprint(wrong_fingerprint):
    request = _request(StaUpdateStrategy.INCREMENTAL)
    observation = _snapshot_mapping(1)
    observation["identity"]["corner_fingerprint"] = wrong_fingerprint
    native = _NativeModule(request, observation_script=(observation, None))
    session = IncrementalStaSession(native, request, CONTEXT)
    with pytest.raises(StaExecutionContractError, match="capture contract"), session:
        session.run_full_baseline()
        _ = session.snapshot_observation
    assert native.session.close_calls == 1
    _assert_failed_session_terminal(session, native)


@pytest.mark.parametrize("with_sink", [False, True])
@pytest.mark.parametrize("debug_checks", [False, True])
def test_run_timing_explicit_sink_requests_observation_before_close(
    tmp_path, monkeypatch, with_sink, debug_checks
):
    from chipcompiler.tools.ecc import module as ecc_module

    request = _request(StaUpdateStrategy.INCREMENTAL)
    native = _NativeModule(request)
    native.incregpusta_debug_checks_enabled = debug_checks
    native.lib_init = lambda **_kwargs: None
    native.sdc_init = lambda _path: None
    native.spef_init = lambda _path: None
    module = ecc_module.ECCToolsModule.__new__(ecc_module.ECCToolsModule)
    module.ecc = native
    monkeypatch.setattr(ecc_module, "discard_sta_run_outputs", lambda *_args: None)
    monkeypatch.setattr(ecc_module, "publish_sta_artifacts", lambda **_kwargs: None)
    captured = []
    module.run_timing(
        work_dir=tmp_path / "work",
        feature_dir=tmp_path / "features",
        output_modes=("structured",),
        execution_request=request,
        snapshot_observation_sink=(
            (lambda context, observation: captured.append((context, observation)))
            if with_sink
            else None
        ),
    )
    assert native.session.close_calls == 1
    assert native.session.observation_reads == (2 if with_sink and debug_checks else 0)
    if with_sink:
        assert len(captured) == 1
        assert captured[0][0] == CONTEXT
        if debug_checks:
            assert captured[0][1].state is StaSnapshotState.RELEASED
        else:
            assert captured[0][1] is None
    else:
        assert not captured
