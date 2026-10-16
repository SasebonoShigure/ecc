import json
from dataclasses import replace
from enum import Enum
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from chipcompiler.tools.ecc.sta_mode import (
    StaBackend,
    StaCapabilityReason,
    StaExecutionContractError,
    StaExecutionRequest,
    StaFallbackPolicy,
    StaSessionError,
    StaSessionStatusCode,
    StaUnsupportedError,
    StaUpdateStrategy,
    execution_record_from_mapping,
    preflight_stage1_request,
)
from chipcompiler.tools.ecc.sta_session import IncrementalStaSession, preflight_sta_request
from chipcompiler.tools.ecc.sta_snapshot import make_direct_sta_analysis_context

_CONTEXT = make_direct_sta_analysis_context()


def _request(strategy=StaUpdateStrategy.FULL):
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


class FakeNativeStaSessionError(RuntimeError):
    def __init__(
        self,
        message,
        *,
        request,
        status_code,
        state,
        capability_reason=None,
    ):
        super().__init__(message)
        self.request = request
        self.status_code = status_code
        self.state = state
        self.capability_reason = capability_reason


def _native_error(
    *,
    request=None,
    status_code="run_failed",
    state="poisoned",
    capability_reason=None,
    message="native failure",
):
    typed_request = request or _request()
    request_payload = {
        "backend": typed_request.backend.value,
        "update_strategy": typed_request.update_strategy.value,
        "fallback_policy": typed_request.fallback_policy.value,
    }
    return FakeNativeStaSessionError(
        message,
        request=request_payload,
        status_code=status_code,
        state=state,
        capability_reason=capability_reason,
    )


class FakeNativeSession:
    def __init__(
        self,
        request,
        *,
        init_error=None,
        init_result=None,
        run_error=None,
        close_error=None,
        close_result=None,
    ):
        self.request = request
        self.init_error = init_error
        self.init_result = init_result
        self.run_error = run_error
        self.close_error = close_error
        self.close_result = close_result
        self.calls = []
        self.state = "created"
        self.session_token = 1

    def initialize(self, *, analysis_context, config, config_dict):
        self.calls.append(("initialize", config, dict(config_dict)))
        if self.init_error is not None:
            raise self.init_error
        self.state = "initialized"
        return self.init_result

    def run_full_baseline(self):
        self.calls.append(("run_full_baseline",))
        if self.run_error is not None:
            raise self.run_error
        self.state = "baseline_executed"
        return _record_mapping(self.request)

    def run_physical_baseline(self, **config):
        self.calls.append(("run_physical_baseline", config))
        self.state = "baseline_executed"
        return _record_mapping(self.request)

    def apply_physical_batch(self, *, batch_json):
        self.calls.append(("apply_physical_batch", json.loads(batch_json)))
        if self.run_error is not None:
            raise self.run_error
        execution = _record_mapping(self.request)
        execution["execution_kind"] = "full_update"
        return {
            "generation": json.loads(batch_json)["expected_generation"] + 1,
            "execution": execution,
        }

    def recover_physical_baseline(self, **config):
        self.calls.append(("recover_physical_baseline", config))
        execution = _record_mapping(self.request)
        execution["execution_kind"] = "full_update"
        return {"generation": 2, "execution": execution}

    def read_physical_placement(self, *, expected_generation, cell_names):
        self.calls.append(("read_physical_placement", expected_generation, cell_names))
        if self.run_error is not None:
            raise self.run_error
        return {"generation": expected_generation, "cells": dict.fromkeys(cell_names, [2, 4])}

    def read_physical_result(self, *, summary_only=False):
        self.calls.append(("read_physical_result", summary_only))
        return {"generation": 0, "timing": [], "qor_json": "{}", "paths_json": "{}"}

    @property
    def csr_snapshot_observation(self):
        return None

    def close(self):
        self.calls.append(("close",))
        self.state = "closed"
        if self.close_error is not None:
            raise self.close_error
        return self.close_result


class FakeNativeModule:
    incregpusta_debug_checks_enabled = True

    StaSessionError = FakeNativeStaSessionError

    def __init__(self, *, factory_error=None, **session_kwargs):
        self.factory_error = factory_error
        self.session_kwargs = session_kwargs
        self.requests = []
        self.session = None

    def create_incremental_sta_session(self, request):
        self.requests.append(dict(request))
        if self.factory_error is not None:
            raise self.factory_error
        typed_request = StaExecutionRequest(
            backend=StaBackend(request["backend"]),
            update_strategy=StaUpdateStrategy(request["update_strategy"]),
            fallback_policy=StaFallbackPolicy(request["fallback_policy"]),
        )
        self.session = FakeNativeSession(typed_request, **self.session_kwargs)
        return self.session


def test_session_returns_validated_full_record_and_closes():
    native = FakeNativeModule()
    request = _request()

    with IncrementalStaSession(
        native,
        request,
        _CONTEXT,
        config="sta.json",
        config_dict={"-max_paths": "100"},
    ) as session:
        record = session.run_full_baseline()

    assert record == preflight_stage1_request(request)
    assert native.requests == [
        {"backend": "cpu", "update_strategy": "full", "fallback_policy": "error"}
    ]
    assert native.session.calls == [
        ("initialize", "sta.json", {"-max_paths": "100"}),
        ("run_full_baseline",),
        ("close",),
    ]


def test_physical_baseline_and_current_result_use_the_same_session():
    native = FakeNativeModule()
    with IncrementalStaSession(native, _request(), _CONTEXT) as session:
        record = session.run_physical_baseline(
            bottom_layer="MET2",
            top_layer="MET5",
            recovery_directory="/tmp/checkpoint",
            checkpoint_files={"def": "/tmp/design.def"},
        )
        current = session.read_physical_result()
        session.read_physical_result(summary_only=True)
        assert native.session.calls[-1] == ("read_physical_result", True)
        with pytest.raises(ValueError, match="summary_only must be a boolean"):
            session.read_physical_result(summary_only=1)
    assert record == preflight_stage1_request(_request())
    assert current["generation"] == 0
    assert native.session.calls[1] == (
        "run_physical_baseline",
        {
            "bottom_layer": "MET2",
            "top_layer": "MET5",
            "horizontal_layer": "",
            "vertical_layer": "",
            "recovery_directory": "/tmp/checkpoint",
            "checkpoint_files": {"def": "/tmp/design.def"},
        },
    )
    assert native.session.calls[2] == ("read_physical_result", False)


def test_physical_placement_query_preserves_generation_and_native_errors():
    native = FakeNativeModule()
    with IncrementalStaSession(native, _request(), _CONTEXT) as session:
        assert session.read_physical_placement(expected_generation=3, cell_names=["BUF"]) == {
            "generation": 3,
            "cells": {"BUF": [2, 4]},
        }
        assert native.session.calls[-1] == ("read_physical_placement", 3, ["BUF"])
        with pytest.raises(ValueError, match="uint64"):
            session.read_physical_placement(expected_generation=True, cell_names=["BUF"])


def test_physical_batch_and_recovery_preserve_edits_and_native_errors():
    native = FakeNativeModule()
    edits = [{"edit": {"creation_token": "buffer-one"}, "physical": {"x_dbu": 17}}]
    with IncrementalStaSession(native, _request(), _CONTEXT) as session:
        result = session.apply_physical_batch(expected_generation=1, edits=edits)
        assert result.generation == 2
        assert native.session.calls[-1] == (
            "apply_physical_batch",
            {
                "schema_version": "physical-sta-batch/1.0.0",
                "expected_generation": 1,
                "edits": edits,
            },
        )
        recovered = session.recover_physical_baseline(
            bottom_layer="MET2",
            top_layer="MET5",
            recovery_directory="/tmp/journal",
            checkpoint_files={"def": "/tmp/input.def"},
        )
        assert recovered == result
        native.session.run_error = _native_error(
            state="baseline_executed", message="stale generation"
        )
        with pytest.raises(StaSessionError, match="stale generation"):
            session.apply_physical_batch(expected_generation=1, edits=edits)
        with pytest.raises(ValueError):
            session.apply_physical_batch(expected_generation=2, edits=[{"bad": float("nan")}])


def test_factory_native_error_is_converted_and_chained():
    native_error = _native_error(status_code="owner_conflict", state="created")
    native = FakeNativeModule(factory_error=native_error)

    with (
        pytest.raises(StaSessionError) as raised,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert type(raised.value) is StaSessionError
    assert raised.value.request == _request()
    assert raised.value.status_code is StaSessionStatusCode.OWNER_CONFLICT
    assert raised.value.state == "created"
    assert raised.value.capability_reason is None
    assert raised.value.__cause__ is native_error
    assert native.session is None


def test_init_native_unsupported_is_converted_and_handle_is_closed():
    native_error = _native_error(
        status_code="unsupported",
        state="closed",
        capability_reason="backend_unavailable",
    )
    native = FakeNativeModule(init_error=native_error)

    with (
        pytest.raises(StaUnsupportedError) as raised,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert raised.value.request == _request()
    assert raised.value.status_code is StaSessionStatusCode.UNSUPPORTED
    assert raised.value.capability_reason is StaCapabilityReason.BACKEND_UNAVAILABLE
    assert raised.value.state == "closed"
    assert raised.value.__cause__ is native_error
    assert native.session.calls == [("initialize", "", {}), ("close",)]


@pytest.mark.parametrize(
    "status,reason,error_type",
    [
        (StaSessionStatusCode.RUN_FAILED, None, StaSessionError),
        (
            StaSessionStatusCode.UNSUPPORTED,
            StaCapabilityReason.UNSUPPORTED_ANALYSIS_FEATURES,
            StaUnsupportedError,
        ),
    ],
)
def test_run_native_error_is_converted_and_session_is_closed(status, reason, error_type):
    native_error = _native_error(
        status_code=status.value,
        state="poisoned",
        capability_reason=None if reason is None else reason.value,
    )
    native = FakeNativeModule(run_error=native_error)

    with (
        pytest.raises(StaSessionError) as raised,
        IncrementalStaSession(native, _request(), _CONTEXT) as session,
    ):
        session.run_full_baseline()

    assert type(raised.value) is error_type
    assert raised.value.status_code is status
    assert raised.value.capability_reason is reason
    assert raised.value.state == "poisoned"
    assert raised.value.__cause__ is native_error
    assert native.session.calls == [
        ("initialize", "", {}),
        ("run_full_baseline",),
        ("close",),
    ]


def test_close_native_error_is_converted_and_not_retried():
    native_error = _native_error(status_code="cleanup_failed", state="closed")
    native = FakeNativeModule(close_error=native_error)
    session = IncrementalStaSession(native, _request(), _CONTEXT)

    with pytest.raises(StaSessionError) as raised, session:
        pass

    assert type(raised.value) is StaSessionError
    assert raised.value.status_code is StaSessionStatusCode.CLEANUP_FAILED
    assert raised.value.__cause__ is native_error
    session.close()
    assert native.session.calls == [("initialize", "", {}), ("close",)]


def test_body_typed_error_remains_primary_when_typed_close_fails_once():
    request = _request()
    body_error = StaSessionError(
        request=request,
        status_code=StaSessionStatusCode.RUN_FAILED,
        state="poisoned",
        message="body failed",
    )
    native_error = _native_error(status_code="cleanup_failed", state="closed")
    native = FakeNativeModule(close_error=native_error)
    session = IncrementalStaSession(native, request, _CONTEXT)

    with pytest.raises(StaSessionError, match="body failed") as raised, session:
        raise body_error

    assert raised.value is body_error
    cleanup_error = raised.value.__cause__
    assert type(cleanup_error) is StaSessionError
    assert cleanup_error.status_code is StaSessionStatusCode.CLEANUP_FAILED
    assert cleanup_error.__cause__ is native_error
    session.close()
    assert native.session.calls == [("initialize", "", {}), ("close",)]


@pytest.mark.parametrize(
    "attribute,value,error_match",
    [
        ("request", None, "request must be a mapping"),
        ("request", {"backend": "cpu"}, "request keys differ"),
        ("status_code", None, "status_code must be a string"),
        ("status_code", "unknown", "invalid .* status_code"),
        ("state", None, "state must be a string"),
        ("state", "unknown", "invalid .* state"),
        ("capability_reason", 1, "capability_reason must be a string"),
        ("capability_reason", "unknown", "invalid .* capability_reason"),
    ],
)
def test_malformed_native_error_is_a_chained_contract_error(attribute, value, error_match):
    native_error = _native_error()
    setattr(native_error, attribute, value)
    native = FakeNativeModule(factory_error=native_error)

    with (
        pytest.raises(StaExecutionContractError, match=error_match) as raised,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert raised.value.__cause__ is native_error


@pytest.mark.parametrize(
    "status_code,capability_reason",
    [("unsupported", None), ("run_failed", "backend_unavailable")],
)
def test_native_status_and_capability_reason_must_be_consistent(status_code, capability_reason):
    native_error = _native_error(
        status_code=status_code,
        capability_reason=capability_reason,
    )
    native = FakeNativeModule(factory_error=native_error)

    with (
        pytest.raises(StaExecutionContractError) as raised,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert raised.value.__cause__ is native_error


def test_native_error_request_must_match_immutable_request():
    native_error = _native_error(request=_request(StaUpdateStrategy.INCREMENTAL))
    native = FakeNativeModule(factory_error=native_error)

    with (
        pytest.raises(StaExecutionContractError, match="immutable session request") as raised,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert raised.value.__cause__ is native_error


def test_enter_init_failure_closes_handle():
    native = FakeNativeModule(init_error=ValueError("init failed"))

    with (
        pytest.raises(ValueError, match="init failed"),
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert native.session.calls == [("initialize", "", {}), ("close",)]


def test_factory_value_error_is_not_converted():
    factory_error = ValueError("factory failed")
    native = FakeNativeModule(factory_error=factory_error)

    with (
        pytest.raises(ValueError, match="factory failed") as raised,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert raised.value is factory_error


def test_run_runtime_error_is_not_converted():
    run_error = RuntimeError("run failed")
    native = FakeNativeModule(run_error=run_error)

    with (
        pytest.raises(RuntimeError, match="run failed") as raised,
        IncrementalStaSession(native, _request(), _CONTEXT) as session,
    ):
        session.run_full_baseline()

    assert raised.value is run_error
    assert native.session.calls == [
        ("initialize", "", {}),
        ("run_full_baseline",),
        ("close",),
    ]


def test_enter_false_status_is_contract_error_and_closes_handle():
    native = FakeNativeModule(init_result=False)

    with (
        pytest.raises(StaExecutionContractError, match="initialize must return None"),
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert native.session.calls == [
        ("initialize", "", {}),
        ("close",),
    ]


def test_enter_preserves_init_error_and_chains_close_error():
    init_error = ValueError("init failed")
    close_error = RuntimeError("close failed")
    native = FakeNativeModule(init_error=init_error, close_error=close_error)

    with (
        pytest.raises(ValueError, match="init failed") as error,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        pytest.fail("body must not execute")

    assert error.value is init_error
    assert error.value.__cause__ is close_error
    assert native.session.calls == [("initialize", "", {}), ("close",)]


def test_exit_preserves_body_error_and_chains_close_error():
    body_error = ValueError("body failed")
    close_error = RuntimeError("close failed")
    native = FakeNativeModule(close_error=close_error)

    with (
        pytest.raises(ValueError, match="body failed") as error,
        IncrementalStaSession(native, _request(), _CONTEXT),
    ):
        raise body_error

    assert error.value is body_error
    assert error.value.__cause__ is close_error


def test_close_failure_without_primary_error_propagates_once():
    native = FakeNativeModule(close_error=RuntimeError("close failed"))
    session = IncrementalStaSession(native, _request(), _CONTEXT)

    with pytest.raises(RuntimeError, match="close failed"), session:
        pass

    session.close()
    assert native.session.calls == [("initialize", "", {}), ("close",)]


def test_close_false_status_is_contract_error_and_is_not_retried():
    native = FakeNativeModule(close_result=False)
    session = IncrementalStaSession(native, _request(), _CONTEXT)

    with pytest.raises(StaExecutionContractError, match="close must return None"), session:
        pass

    session.close()
    assert native.session.calls == [
        ("initialize", "", {}),
        ("close",),
    ]


def test_native_record_mismatch_is_a_contract_error():
    native = FakeNativeModule()
    request = _request()

    with (
        pytest.raises(StaExecutionContractError, match="differs"),
        IncrementalStaSession(native, request, _CONTEXT) as session,
    ):
        native.session.request = replace(
            _request(), fallback_policy=StaFallbackPolicy.FULL_WITH_RECORD
        )
        session.run_full_baseline()

    assert native.session.calls[-1] == ("close",)


def _cuda_request():
    return replace(_request(StaUpdateStrategy.INCREMENTAL), backend=StaBackend.CUDA)


def _cuda_record_mapping():
    return {
        **_record_mapping(_request()),
        "requested_backend": "cuda",
        "executed_backend": "cuda",
        "requested_update_strategy": "incremental",
        "execution_kind": "baseline_only",
        "fallback_reason": "not_applicable_no_mutation",
    }


def test_cuda_preflight_uses_native_resolution_and_preserves_session_lifecycle():
    request = _cuda_request()
    raw_record = _cuda_record_mapping()
    native_session = FakeNativeSession(request)
    native_session.run_full_baseline = Mock(return_value=raw_record)
    native = SimpleNamespace(
        incregpusta_debug_checks_enabled=False,
        StaSessionError=FakeNativeStaSessionError,
        resolve_sta_execution=Mock(return_value=raw_record),
        create_incremental_sta_session=Mock(return_value=native_session),
    )

    with IncrementalStaSession(native, request, _CONTEXT) as session:
        result = session.run_full_baseline()

    expected = execution_record_from_mapping(raw_record)
    assert result == expected
    native.resolve_sta_execution.assert_called_once_with(
        {"backend": "cuda", "update_strategy": "incremental", "fallback_policy": "error"}
    )
    native.create_incremental_sta_session.assert_called_once_with(
        {"backend": "cuda", "update_strategy": "incremental", "fallback_policy": "error"}
    )
    native_session.run_full_baseline.assert_called_once_with()
    assert native_session.calls == [("initialize", "", {}), ("close",)]


@pytest.mark.parametrize("status", ["unsupported", "quarantined"])
def test_cuda_preflight_preserves_native_capability_and_lifecycle_failures(status):
    request = _cuda_request()
    error = _native_error(
        request=request,
        status_code=status,
        state="created",
        capability_reason="backend_unavailable" if status == "unsupported" else None,
    )
    native = SimpleNamespace(
        StaSessionError=FakeNativeStaSessionError,
        resolve_sta_execution=Mock(side_effect=error),
    )
    with pytest.raises(StaSessionError) as raised:
        preflight_sta_request(request, native)
    assert raised.value.status_code.value == status
    assert raised.value.request == request
    assert raised.value.__cause__ is error


@pytest.mark.parametrize(
    "raw_record",
    [
        {**_cuda_record_mapping(), "fallback_policy": "full_with_record"},
        {**_cuda_record_mapping(), "unexpected": 1},
        {**_cuda_record_mapping(), "executed_backend": "cpu"},
    ],
)
def test_cuda_preflight_rejects_mismatched_or_invalid_native_records(raw_record):
    native = SimpleNamespace(
        StaSessionError=FakeNativeStaSessionError,
        resolve_sta_execution=Mock(return_value=raw_record),
    )
    with pytest.raises(StaExecutionContractError):
        preflight_sta_request(_cuda_request(), native)


@pytest.mark.parametrize("debug_checks", [False, True])
def test_cuda_incremental_baseline_uses_native_record_without_cpu_snapshot(debug_checks):
    request = _cuda_request()
    raw_record = _cuda_record_mapping()
    native_session = FakeNativeSession(request)
    native = Mock(
        incregpusta_debug_checks_enabled=debug_checks,
        StaSessionError=FakeNativeStaSessionError,
        resolve_sta_execution=Mock(return_value=raw_record),
        create_incremental_sta_session=Mock(return_value=native_session),
    )
    with (
        patch.object(native_session, "run_full_baseline", return_value=raw_record),
        IncrementalStaSession(native, request, _CONTEXT) as session,
    ):
        result = session.run_full_baseline()
        assert session.snapshot_observation is None
    assert result == execution_record_from_mapping(raw_record)
    native.resolve_sta_execution.assert_called_once_with(
        {"backend": "cuda", "update_strategy": "incremental", "fallback_policy": "error"}
    )
    assert native_session.calls == [("initialize", "", {}), ("close",)]


def test_physical_artifact_generation_rejects_non_integer_and_out_of_range():
    native = FakeNativeModule()
    with IncrementalStaSession(native, _request(), _CONTEXT) as session:
        for method in (session.publish_physical_artifacts, session.read_physical_artifacts):
            for value in (True, False, 1.0, -1, 1 << 64):
                with pytest.raises(ValueError, match="generation"):
                    method(expected_generation=value)
