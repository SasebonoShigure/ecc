import itertools
import json
from dataclasses import fields, replace
from enum import Enum
from pathlib import Path

import pytest

from chipcompiler.tools.ecc.sta_mode import (
    StaBackend,
    StaCapabilityReason,
    StaExecutionContractError,
    StaExecutionKind,
    StaExecutionRecord,
    StaExecutionRequest,
    StaFallbackPolicy,
    StaFallbackReason,
    StaPropagationScope,
    StaSessionError,
    StaSessionStatusCode,
    StaUnsupportedError,
    StaUpdateStrategy,
    execution_record_from_mapping,
    preflight_stage1_request,
    request_from_mapping,
    validate_execution_record,
)

SCHEMA_PATH = (
    Path(__file__).parents[3]
    / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema/"
    "incremental_sta_samples_v1.schema.json"
)


def _record_mapping(record: StaExecutionRecord) -> dict[str, object]:
    result: dict[str, object] = {}
    for field in fields(record):
        value = getattr(record, field.name)
        result[field.name] = value.value if isinstance(value, Enum) else value
    return result


def _incremental_record() -> StaExecutionRecord:
    return StaExecutionRecord(
        requested_backend=StaBackend.CUDA,
        requested_update_strategy=StaUpdateStrategy.INCREMENTAL,
        fallback_policy=StaFallbackPolicy.ERROR,
        executed_backend=StaBackend.CUDA,
        executed_update_strategy=StaUpdateStrategy.INCREMENTAL,
        execution_kind=StaExecutionKind.INCREMENTAL_UPDATE,
        propagation_scope=StaPropagationScope.FULL_GRAPH,
        incremental_batch_executed=True,
        fallback_to_full=False,
        fallback_reason=None,
    )


def _fallback_record() -> StaExecutionRecord:
    return StaExecutionRecord(
        requested_backend=StaBackend.CUDA,
        requested_update_strategy=StaUpdateStrategy.INCREMENTAL,
        fallback_policy=StaFallbackPolicy.FULL_WITH_RECORD,
        executed_backend=StaBackend.CPU,
        executed_update_strategy=StaUpdateStrategy.FULL,
        execution_kind=StaExecutionKind.FALLBACK_FULL,
        propagation_scope=StaPropagationScope.FULL_GRAPH,
        incremental_batch_executed=False,
        fallback_to_full=True,
        fallback_reason=StaFallbackReason.CAPACITY_FALLBACK,
    )


def test_missing_workspace_keys_resolve_to_frozen_default():
    assert request_from_mapping({}) == StaExecutionRequest(
        backend=StaBackend.CPU,
        update_strategy=StaUpdateStrategy.FULL,
        fallback_policy=StaFallbackPolicy.ERROR,
    )


@pytest.mark.parametrize(
    "backend,strategy,policy",
    itertools.product(
        (StaBackend.CPU, StaBackend.CUDA),
        (StaUpdateStrategy.FULL, StaUpdateStrategy.INCREMENTAL),
        (StaFallbackPolicy.ERROR, StaFallbackPolicy.FULL_WITH_RECORD),
    ),
)
def test_all_eight_requests_parse(backend, strategy, policy):
    assert request_from_mapping(
        {
            "STA backend": backend.value,
            "STA update strategy": strategy.value,
            "STA fallback policy": policy.value,
        }
    ) == StaExecutionRequest(backend, strategy, policy)


@pytest.mark.parametrize("policy", list(StaFallbackPolicy))
def test_cpu_full_preflight_returns_exact_full_record(policy):
    request = StaExecutionRequest(StaBackend.CPU, StaUpdateStrategy.FULL, policy)
    assert preflight_stage1_request(request) == StaExecutionRecord(
        requested_backend=StaBackend.CPU,
        requested_update_strategy=StaUpdateStrategy.FULL,
        fallback_policy=policy,
        executed_backend=StaBackend.CPU,
        executed_update_strategy=StaUpdateStrategy.FULL,
        execution_kind=StaExecutionKind.FULL_UPDATE,
        propagation_scope=StaPropagationScope.FULL_GRAPH,
        incremental_batch_executed=False,
        fallback_to_full=False,
        fallback_reason=None,
    )


@pytest.mark.parametrize("policy", list(StaFallbackPolicy))
def test_cpu_incremental_preflight_is_non_fallback_baseline(policy):
    request = StaExecutionRequest(StaBackend.CPU, StaUpdateStrategy.INCREMENTAL, policy)
    assert preflight_stage1_request(request) == StaExecutionRecord(
        requested_backend=StaBackend.CPU,
        requested_update_strategy=StaUpdateStrategy.INCREMENTAL,
        fallback_policy=policy,
        executed_backend=StaBackend.CPU,
        executed_update_strategy=StaUpdateStrategy.FULL,
        execution_kind=StaExecutionKind.BASELINE_ONLY,
        propagation_scope=StaPropagationScope.FULL_GRAPH,
        incremental_batch_executed=False,
        fallback_to_full=False,
        fallback_reason=StaFallbackReason.NOT_APPLICABLE_NO_MUTATION,
    )


@pytest.mark.parametrize(
    "strategy,policy",
    itertools.product(StaUpdateStrategy, StaFallbackPolicy),
)
def test_cuda_preflight_is_typed_unsupported(strategy, policy):
    request = StaExecutionRequest(StaBackend.CUDA, strategy, policy)
    with pytest.raises(StaUnsupportedError) as raised:
        preflight_stage1_request(request)

    assert isinstance(raised.value, StaSessionError)
    assert raised.value.request == request
    assert raised.value.status_code is StaSessionStatusCode.UNSUPPORTED
    assert raised.value.capability_reason is StaCapabilityReason.BACKEND_UNAVAILABLE
    assert raised.value.state == "created"


def test_mode_enums_and_record_keys_match_frozen_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    mode = schema["$defs"]["mode"]
    properties = mode["properties"]

    assert {field.name for field in fields(StaExecutionRecord)} == set(mode["required"])
    assert {item.value for item in StaBackend} == set(properties["requested_backend"]["enum"])
    assert {item.value for item in StaBackend} == set(properties["executed_backend"]["enum"])
    assert {item.value for item in StaUpdateStrategy} == set(
        properties["requested_update_strategy"]["enum"]
    )
    assert {item.value for item in StaUpdateStrategy} == set(
        properties["executed_update_strategy"]["enum"]
    )
    assert {item.value for item in StaFallbackPolicy} == set(properties["fallback_policy"]["enum"])
    assert {item.value for item in StaExecutionKind} == set(properties["execution_kind"]["enum"])
    assert {item.value for item in StaPropagationScope} == set(
        properties["propagation_scope"]["enum"]
    )
    assert {item.value for item in StaFallbackReason} | {None} == set(
        properties["fallback_reason"]["enum"]
    )


def test_all_four_execution_kinds_validate_and_round_trip_from_mapping():
    full = preflight_stage1_request(
        StaExecutionRequest(
            StaBackend.CPU,
            StaUpdateStrategy.FULL,
            StaFallbackPolicy.ERROR,
        )
    )
    baseline = preflight_stage1_request(
        StaExecutionRequest(
            StaBackend.CPU,
            StaUpdateStrategy.INCREMENTAL,
            StaFallbackPolicy.FULL_WITH_RECORD,
        )
    )
    for record in (full, baseline, _incremental_record(), _fallback_record()):
        validate_execution_record(record)
        assert execution_record_from_mapping(_record_mapping(record)) == record


@pytest.mark.parametrize(
    "record",
    [
        replace(
            preflight_stage1_request(
                StaExecutionRequest(
                    StaBackend.CPU,
                    StaUpdateStrategy.FULL,
                    StaFallbackPolicy.ERROR,
                )
            ),
            fallback_to_full=True,
        ),
        replace(
            preflight_stage1_request(
                StaExecutionRequest(
                    StaBackend.CPU,
                    StaUpdateStrategy.INCREMENTAL,
                    StaFallbackPolicy.ERROR,
                )
            ),
            fallback_reason=None,
        ),
        replace(_incremental_record(), incremental_batch_executed=False),
        replace(_fallback_record(), fallback_policy=StaFallbackPolicy.ERROR),
        replace(_fallback_record(), fallback_reason=None),
        replace(
            preflight_stage1_request(
                StaExecutionRequest(
                    StaBackend.CPU,
                    StaUpdateStrategy.FULL,
                    StaFallbackPolicy.ERROR,
                )
            ),
            executed_backend=StaBackend.CUDA,
        ),
    ],
)
def test_cross_field_contract_violations_are_rejected(record):
    with pytest.raises(StaExecutionContractError):
        validate_execution_record(record)


def test_fallback_full_allows_same_backend():
    validate_execution_record(replace(_fallback_record(), executed_backend=StaBackend.CUDA))


def test_native_record_parser_rejects_missing_or_extra_keys():
    record = _record_mapping(_incremental_record())
    missing = dict(record)
    missing.pop("fallback_reason")
    with pytest.raises(StaExecutionContractError, match="missing=.*fallback_reason"):
        execution_record_from_mapping(missing)

    with pytest.raises(StaExecutionContractError, match="extra=.*unexpected"):
        execution_record_from_mapping({**record, "unexpected": 1})


@pytest.mark.parametrize(
    "field,value",
    [
        ("requested_backend", "CPU"),
        ("execution_kind", "unknown"),
        ("incremental_batch_executed", 1),
        ("fallback_to_full", "false"),
    ],
)
def test_native_record_parser_rejects_invalid_tokens_and_types(field, value):
    record = _record_mapping(_incremental_record())
    record[field] = value
    with pytest.raises(StaExecutionContractError):
        execution_record_from_mapping(record)


@pytest.mark.parametrize(
    "parameters",
    [
        {"STA backend": "CPU"},
        {"STA update strategy": "partial"},
        {"STA fallback policy": "silent"},
        {"STA backend": 1},
    ],
)
def test_request_parser_rejects_invalid_values(parameters):
    with pytest.raises(ValueError):
        request_from_mapping(parameters)


def test_capability_reason_is_not_accepted_for_lifecycle_failure():
    request = request_from_mapping({})
    with pytest.raises(ValueError, match="present together"):
        StaSessionError(
            request=request,
            status_code=StaSessionStatusCode.RUN_FAILED,
            state="poisoned",
            message="run failed",
            capability_reason=StaCapabilityReason.BACKEND_UNAVAILABLE,
        )


def test_unsupported_status_requires_capability_reason():
    request = request_from_mapping({})
    with pytest.raises(ValueError, match="present together"):
        StaSessionError(
            request=request,
            status_code=StaSessionStatusCode.UNSUPPORTED,
            state="created",
            message="unsupported",
        )
