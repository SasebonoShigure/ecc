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
    StaSessionError = _NeverNativeError

    def __init__(self, request, **session_kwargs):
        self.request = request
        self.session = _NativeSession(request, **session_kwargs)
        self.factory_calls = 0

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
        assert session.snapshot_observation.state is StaSnapshotState.READY

    assert record == preflight_stage1_request(request)
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
    assert native.session.observation_reads == 2


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

    assert raised.value is close_error
    assert native.session.observation_reads == 1
    _assert_failed_session_terminal(session, native)


@pytest.mark.parametrize("released_stage", ["clean", "getter", "parse", "transition"])
def test_wrong_close_return_dominates_every_release_stage(released_stage, monkeypatch):
    request = _request(StaUpdateStrategy.FULL)
    cleanup_error = RuntimeError(f"{released_stage} release failed")
    native_kwargs = {"close_result": False}
    expected_cause = None if released_stage == "clean" else cleanup_error
    if released_stage == "getter":
        native_kwargs["released_error"] = cleanup_error
    elif released_stage == "parse":

        def fail_parse(_raw):
            raise cleanup_error

        monkeypatch.setattr(sta_session_module, "snapshot_observation_from_mapping", fail_parse)
    elif released_stage == "transition":

        def fail_transition(*_args):
            raise cleanup_error

        monkeypatch.setattr(
            sta_session_module,
            "validate_snapshot_observation_transition",
            fail_transition,
        )

    native = _NativeModule(request, **native_kwargs)
    session = IncrementalStaSession(native, request, CONTEXT)
    with (
        pytest.raises(StaExecutionContractError, match="close must return None") as raised,
        session,
    ):
        pass

    assert raised.value.__cause__ is expected_cause
    assert native.session.observation_reads == 1
    assert native.session.close_calls == 1
    _assert_failed_session_terminal(session, native)


@pytest.mark.parametrize("body_stage", ["bad_record", "bad_active"])
@pytest.mark.parametrize(
    "close_stage",
    ["clean", "native", "wrong_return", "getter", "parse", "transition"],
)
def test_body_contract_error_identity_dominates_every_close_stage(
    body_stage, close_stage, monkeypatch
):
    if body_stage == "bad_record":
        request = _request(StaUpdateStrategy.FULL)
        bad_record = _record_mapping(request)
        bad_record["update_strategy"] = StaUpdateStrategy.INCREMENTAL.value
        native_kwargs = {"record_mapping": bad_record}
        active_reads = 0
        close_parse_call = 1
    else:
        request = _request(StaUpdateStrategy.INCREMENTAL)
        native_kwargs = {"observation_script": (_snapshot_mapping(2), None)}
        active_reads = 1
        close_parse_call = 2

    cleanup_error = RuntimeError(f"{close_stage} close failed")
    expected_cause = cleanup_error
    if close_stage == "native":
        native_kwargs["close_error"] = cleanup_error
    elif close_stage == "wrong_return":
        native_kwargs["close_result"] = False
        expected_cause = None
    elif close_stage == "getter":
        native_kwargs["released_error"] = cleanup_error
    elif close_stage == "parse":
        original_parse = sta_session_module.snapshot_observation_from_mapping
        parse_calls = 0

        def fail_close_parse(raw):
            nonlocal parse_calls
            parse_calls += 1
            if parse_calls == close_parse_call:
                raise cleanup_error
            return original_parse(raw)

        monkeypatch.setattr(
            sta_session_module,
            "snapshot_observation_from_mapping",
            fail_close_parse,
        )
    elif close_stage == "transition":

        def fail_close_transition(*_args):
            raise cleanup_error

        monkeypatch.setattr(
            sta_session_module,
            "validate_snapshot_observation_transition",
            fail_close_transition,
        )
    else:
        expected_cause = None

    native = _NativeModule(request, **native_kwargs)
    session = IncrementalStaSession(native, request, CONTEXT)
    body_errors = []
    with pytest.raises(StaExecutionContractError) as raised, session:
        try:
            session.run_full_baseline()
        except StaExecutionContractError as body_error:
            body_errors.append(body_error)
            raise

    assert len(body_errors) == 1
    assert raised.value is body_errors[0]
    if close_stage == "wrong_return":
        assert isinstance(raised.value.__cause__, StaExecutionContractError)
        assert "close must return None" in str(raised.value.__cause__)
    else:
        assert raised.value.__cause__ is expected_cause
    assert native.session.close_calls == 1
    assert native.session.observation_reads == active_reads + (close_stage != "native")
    _assert_failed_session_terminal(session, native)
