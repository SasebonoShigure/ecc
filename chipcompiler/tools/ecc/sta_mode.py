"""Typed execution-mode contract for STA backends.

This module is intentionally independent of Workspace and native bindings.  It
owns parsing, stage capability checks, and validation of execution telemetry at
the Python boundary.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar


class StaBackend(str, Enum):
    CPU = "cpu"
    CUDA = "cuda"


class StaUpdateStrategy(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class StaFallbackPolicy(str, Enum):
    ERROR = "error"
    FULL_WITH_RECORD = "full_with_record"


class StaExecutionKind(str, Enum):
    BASELINE_ONLY = "baseline_only"
    FULL_UPDATE = "full_update"
    INCREMENTAL_UPDATE = "incremental_update"
    FALLBACK_FULL = "fallback_full"


class StaPropagationScope(str, Enum):
    NONE = "none"
    FULL_GRAPH = "full_graph"
    AFFECTED_CONE = "affected_cone"


class StaFallbackReason(str, Enum):
    NOT_APPLICABLE_NO_MUTATION = "not_applicable_no_mutation"
    SAME_BATCH_INSERT_REMOVE_UNSUPPORTED = "same_batch_insert_remove_unsupported"
    CELL_MASTER_REPLACEMENT_UNSUPPORTED = "cell_master_replacement_unsupported"
    UNSUPPORTED_EDIT = "unsupported_edit"
    REVERSE_SLOT_NOT_REPLACEABLE = "reverse_slot_not_replaceable"
    NODE_DELETION_UNSUPPORTED = "node_deletion_unsupported"
    CAPACITY_FALLBACK = "capacity_fallback"
    CLOCK_CHANGED = "clock_changed"
    CONSTRAINT_CHANGED = "constraint_changed"
    LIBRARY_CHANGED = "library_changed"
    CORNER_CHANGED = "corner_changed"
    PARASITIC_CHANGED = "parasitic_changed"
    SEQUENTIAL_EDIT_UNSUPPORTED = "sequential_edit_unsupported"
    BACKEND_UNAVAILABLE = "backend_unavailable"
    CONTRACT_VIOLATION = "contract_violation"
    OLD_LEVEL_ORDER_CONFLICT = "old_level_order_conflict"


class StaCapabilityReason(str, Enum):
    BACKEND_UNAVAILABLE = "backend_unavailable"
    UNSUPPORTED_ANALYSIS_FEATURES = "unsupported_analysis_features"


class StaSessionStatusCode(str, Enum):
    UNSUPPORTED = "unsupported"
    INVALID_STATE = "invalid_state"
    OWNER_CONFLICT = "owner_conflict"
    INIT_FAILED = "init_failed"
    RUN_FAILED = "run_failed"
    CLEANUP_FAILED = "cleanup_failed"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class StaExecutionRequest:
    backend: StaBackend
    update_strategy: StaUpdateStrategy
    fallback_policy: StaFallbackPolicy

    def __post_init__(self) -> None:
        _require_type("backend", self.backend, StaBackend)
        _require_type("update_strategy", self.update_strategy, StaUpdateStrategy)
        _require_type("fallback_policy", self.fallback_policy, StaFallbackPolicy)


@dataclass(frozen=True)
class StaExecutionRecord:
    requested_backend: StaBackend
    requested_update_strategy: StaUpdateStrategy
    fallback_policy: StaFallbackPolicy
    executed_backend: StaBackend
    executed_update_strategy: StaUpdateStrategy
    execution_kind: StaExecutionKind
    propagation_scope: StaPropagationScope
    incremental_batch_executed: bool
    fallback_to_full: bool
    fallback_reason: StaFallbackReason | None

    def __post_init__(self) -> None:
        enum_fields = (
            ("requested_backend", self.requested_backend, StaBackend),
            ("requested_update_strategy", self.requested_update_strategy, StaUpdateStrategy),
            ("fallback_policy", self.fallback_policy, StaFallbackPolicy),
            ("executed_backend", self.executed_backend, StaBackend),
            ("executed_update_strategy", self.executed_update_strategy, StaUpdateStrategy),
            ("execution_kind", self.execution_kind, StaExecutionKind),
            ("propagation_scope", self.propagation_scope, StaPropagationScope),
        )
        for name, value, expected_type in enum_fields:
            _require_type(name, value, expected_type)
        _require_type("incremental_batch_executed", self.incremental_batch_executed, bool)
        _require_type("fallback_to_full", self.fallback_to_full, bool)
        if self.fallback_reason is not None:
            _require_type("fallback_reason", self.fallback_reason, StaFallbackReason)


class StaExecutionContractError(ValueError):
    """Raised when an execution record violates the frozen mode contract."""


class StaSessionError(RuntimeError):
    """Typed capability or lifecycle error returned by an STA session."""

    def __init__(
        self,
        *,
        request: StaExecutionRequest,
        status_code: StaSessionStatusCode,
        state: str,
        message: str,
        capability_reason: StaCapabilityReason | None = None,
    ) -> None:
        _require_type("request", request, StaExecutionRequest)
        _require_type("status_code", status_code, StaSessionStatusCode)
        _require_type("state", state, str)
        _require_type("message", message, str)
        if capability_reason is not None:
            _require_type("capability_reason", capability_reason, StaCapabilityReason)
        if (status_code is StaSessionStatusCode.UNSUPPORTED) != (capability_reason is not None):
            raise ValueError("unsupported status and capability_reason must be present together")

        self.request = request
        self.status_code = status_code
        self.message = message
        self.state = state
        self.capability_reason = capability_reason
        super().__init__(message)


class StaUnsupportedError(StaSessionError):
    """Raised when a valid request is unavailable in the current stage."""

    def __init__(
        self,
        *,
        request: StaExecutionRequest,
        state: str = "created",
        message: str | None = None,
        capability_reason: StaCapabilityReason = StaCapabilityReason.BACKEND_UNAVAILABLE,
    ) -> None:
        if message is None:
            message = (
                f"STA backend {request.backend.value!r} is unavailable for "
                f"update strategy {request.update_strategy.value!r}"
            )
        super().__init__(
            request=request,
            status_code=StaSessionStatusCode.UNSUPPORTED,
            state=state,
            message=message,
            capability_reason=capability_reason,
        )


_STA_BACKEND_KEY = "STA backend"
_STA_UPDATE_STRATEGY_KEY = "STA update strategy"
_STA_FALLBACK_POLICY_KEY = "STA fallback policy"

_EXECUTION_RECORD_KEYS = frozenset(
    {
        "requested_backend",
        "requested_update_strategy",
        "fallback_policy",
        "executed_backend",
        "executed_update_strategy",
        "execution_kind",
        "propagation_scope",
        "incremental_batch_executed",
        "fallback_to_full",
        "fallback_reason",
    }
)

_EnumT = TypeVar("_EnumT", bound=Enum)


def request_from_mapping(parameters: Mapping[str, object]) -> StaExecutionRequest:
    """Resolve an immutable request from Workspace-style internal parameters."""
    if not isinstance(parameters, Mapping):
        raise TypeError("parameters must be a mapping")
    return StaExecutionRequest(
        backend=_parse_enum(
            _STA_BACKEND_KEY,
            parameters.get(_STA_BACKEND_KEY, _DEFAULT_REQUEST.backend),
            StaBackend,
        ),
        update_strategy=_parse_enum(
            _STA_UPDATE_STRATEGY_KEY,
            parameters.get(_STA_UPDATE_STRATEGY_KEY, _DEFAULT_REQUEST.update_strategy),
            StaUpdateStrategy,
        ),
        fallback_policy=_parse_enum(
            _STA_FALLBACK_POLICY_KEY,
            parameters.get(_STA_FALLBACK_POLICY_KEY, _DEFAULT_REQUEST.fallback_policy),
            StaFallbackPolicy,
        ),
    )


def preflight_stage1_request(request: StaExecutionRequest) -> StaExecutionRecord:
    """Resolve a stage-1 request before any artifact or native side effect."""
    _require_type("request", request, StaExecutionRequest)
    if request.backend is StaBackend.CUDA:
        raise StaUnsupportedError(request=request)

    if request.update_strategy is StaUpdateStrategy.FULL:
        record = StaExecutionRecord(
            requested_backend=request.backend,
            requested_update_strategy=request.update_strategy,
            fallback_policy=request.fallback_policy,
            executed_backend=StaBackend.CPU,
            executed_update_strategy=StaUpdateStrategy.FULL,
            execution_kind=StaExecutionKind.FULL_UPDATE,
            propagation_scope=StaPropagationScope.FULL_GRAPH,
            incremental_batch_executed=False,
            fallback_to_full=False,
            fallback_reason=None,
        )
    else:
        record = StaExecutionRecord(
            requested_backend=request.backend,
            requested_update_strategy=request.update_strategy,
            fallback_policy=request.fallback_policy,
            executed_backend=StaBackend.CPU,
            executed_update_strategy=StaUpdateStrategy.FULL,
            execution_kind=StaExecutionKind.BASELINE_ONLY,
            propagation_scope=StaPropagationScope.FULL_GRAPH,
            incremental_batch_executed=False,
            fallback_to_full=False,
            fallback_reason=StaFallbackReason.NOT_APPLICABLE_NO_MUTATION,
        )
    validate_execution_record(record)
    return record


def execution_record_from_mapping(record: Mapping[str, object]) -> StaExecutionRecord:
    """Parse and validate a record returned through the native boundary."""
    if not isinstance(record, Mapping):
        raise TypeError("execution record must be a mapping")
    actual_keys = set(record)
    if actual_keys != _EXECUTION_RECORD_KEYS:
        missing = sorted(_EXECUTION_RECORD_KEYS - actual_keys)
        extra = sorted(actual_keys - _EXECUTION_RECORD_KEYS)
        raise StaExecutionContractError(
            f"execution record keys differ from contract: missing={missing}, extra={extra}"
        )

    fallback_reason_value = record["fallback_reason"]
    fallback_reason = (
        None
        if fallback_reason_value is None
        else _parse_record_enum("fallback_reason", fallback_reason_value, StaFallbackReason)
    )
    parsed = StaExecutionRecord(
        requested_backend=_parse_record_enum(
            "requested_backend", record["requested_backend"], StaBackend
        ),
        requested_update_strategy=_parse_record_enum(
            "requested_update_strategy",
            record["requested_update_strategy"],
            StaUpdateStrategy,
        ),
        fallback_policy=_parse_record_enum(
            "fallback_policy", record["fallback_policy"], StaFallbackPolicy
        ),
        executed_backend=_parse_record_enum(
            "executed_backend", record["executed_backend"], StaBackend
        ),
        executed_update_strategy=_parse_record_enum(
            "executed_update_strategy",
            record["executed_update_strategy"],
            StaUpdateStrategy,
        ),
        execution_kind=_parse_record_enum(
            "execution_kind", record["execution_kind"], StaExecutionKind
        ),
        propagation_scope=_parse_record_enum(
            "propagation_scope", record["propagation_scope"], StaPropagationScope
        ),
        incremental_batch_executed=_parse_bool(
            "incremental_batch_executed", record["incremental_batch_executed"]
        ),
        fallback_to_full=_parse_bool("fallback_to_full", record["fallback_to_full"]),
        fallback_reason=fallback_reason,
    )
    validate_execution_record(parsed)
    return parsed


def validate_execution_record(record: StaExecutionRecord) -> None:
    """Validate all cross-field invariants for the four frozen execution kinds."""
    _require_type("record", record, StaExecutionRecord)
    common_rules: dict[StaExecutionKind, tuple[tuple[str, object], ...]] = {
        StaExecutionKind.FULL_UPDATE: (
            ("requested_update_strategy", StaUpdateStrategy.FULL),
            ("executed_update_strategy", StaUpdateStrategy.FULL),
            ("propagation_scope", StaPropagationScope.FULL_GRAPH),
            ("incremental_batch_executed", False),
            ("fallback_to_full", False),
            ("fallback_reason", None),
        ),
        StaExecutionKind.BASELINE_ONLY: (
            ("requested_update_strategy", StaUpdateStrategy.INCREMENTAL),
            ("executed_update_strategy", StaUpdateStrategy.FULL),
            ("propagation_scope", StaPropagationScope.FULL_GRAPH),
            ("incremental_batch_executed", False),
            ("fallback_to_full", False),
            ("fallback_reason", StaFallbackReason.NOT_APPLICABLE_NO_MUTATION),
        ),
        StaExecutionKind.INCREMENTAL_UPDATE: (
            ("requested_update_strategy", StaUpdateStrategy.INCREMENTAL),
            ("executed_update_strategy", StaUpdateStrategy.INCREMENTAL),
            ("propagation_scope", StaPropagationScope.FULL_GRAPH),
            ("incremental_batch_executed", True),
            ("fallback_to_full", False),
            ("fallback_reason", None),
        ),
        StaExecutionKind.FALLBACK_FULL: (
            ("requested_update_strategy", StaUpdateStrategy.INCREMENTAL),
            ("executed_update_strategy", StaUpdateStrategy.FULL),
            ("fallback_policy", StaFallbackPolicy.FULL_WITH_RECORD),
            ("propagation_scope", StaPropagationScope.FULL_GRAPH),
            ("incremental_batch_executed", False),
            ("fallback_to_full", True),
        ),
    }
    for field_name, expected in common_rules[record.execution_kind]:
        actual = getattr(record, field_name)
        if actual != expected:
            raise StaExecutionContractError(
                f"{record.execution_kind.value} requires {field_name}={expected!r}; got {actual!r}"
            )

    if (
        record.execution_kind is not StaExecutionKind.FALLBACK_FULL
        and record.requested_backend is not record.executed_backend
    ):
        raise StaExecutionContractError("backend mismatch requires execution_kind='fallback_full'")
    if record.execution_kind is StaExecutionKind.FALLBACK_FULL and record.fallback_reason is None:
        raise StaExecutionContractError("fallback_full requires a non-null fallback_reason")


def _parse_enum(name: str, value: object, enum_type: type[_EnumT]) -> _EnumT:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string; got {type(value).__name__}")
    try:
        return enum_type(value)
    except ValueError as exc:
        choices = ", ".join(member.value for member in enum_type)
        raise ValueError(f"{name} must be one of ({choices}); got {value!r}") from exc


def _parse_record_enum(name: str, value: object, enum_type: type[_EnumT]) -> _EnumT:
    try:
        return _parse_enum(name, value, enum_type)
    except ValueError as exc:
        raise StaExecutionContractError(str(exc)) from exc


def _parse_bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise StaExecutionContractError(f"{name} must be a bool; got {type(value).__name__}")
    return value


def _require_type(name: str, value: object, expected_type: type[object]) -> None:
    if not isinstance(value, expected_type):
        raise TypeError(f"{name} must be {expected_type.__name__}; got {type(value).__name__}")


_DEFAULT_REQUEST = StaExecutionRequest(
    backend=StaBackend.CPU,
    update_strategy=StaUpdateStrategy.FULL,
    fallback_policy=StaFallbackPolicy.ERROR,
)
