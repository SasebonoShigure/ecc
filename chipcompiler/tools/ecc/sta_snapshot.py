"""Pure Stage 2 STA snapshot observation contracts.

This module deliberately has no dependency on native bindings, sessions, or
the vendored ecc-tools source tree.  It owns the immutable Python boundary for
analysis context fingerprints and snapshot observations.
"""

import hashlib
import os
import struct
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import NoReturn, TypeAlias, TypeVar, cast

from .sta_mode import StaExecutionContractError

_SCHEMA_VERSION = "1.0.0"
_DIRECT_LIBERTY_CORNER = "__direct__"
_UNSPECIFIED_TEMPERATURE = "__unspecified_temperature__"
_NO_RC_CORNER = "__no_rc_corner__"
_T = TypeVar("_T")


class StaSnapshotContractError(StaExecutionContractError):
    """A structured violation of the frozen snapshot contract."""

    def __init__(self, message: str, *, field: str, category: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.category = category
        self.detail = message


class StaSnapshotState(str, Enum):
    READY = "ready"
    INVALIDATED = "invalidated"
    RELEASED = "released"


class StaCapacityAction(str, Enum):
    INITIAL_ALLOCATE = "initial_allocate"


class StaReferenceUnsupportedReason(str, Enum):
    PARASITIC_NET = "parasitic_net"
    SEQUENTIAL_INSTANCE = "sequential_instance"
    SEQUENTIAL_LAUNCH = "sequential_launch"
    TIMING_CHECK = "timing_check"
    CRPR = "crpr"
    PROPAGATED_CLOCK = "propagated_clock"
    CLOCK_TREE_FANOUT = "clock_tree_fanout"
    CLOCK_GATING_OR_DIVIDER = "clock_gating_or_divider"
    CONDITIONAL_TIMING_ARC = "conditional_timing_arc"
    CASE_ANALYSIS = "case_analysis"


class StaScatterRejectionReason(str, Enum):
    SCHEMA_MISMATCH = "schema_mismatch"
    SESSION_MISMATCH = "session_mismatch"
    GENERATION_MISMATCH = "generation_mismatch"
    SOURCE_IDENTITY_MISMATCH = "source_identity_mismatch"
    SHAPE_MISMATCH = "shape_mismatch"
    RESULT_NUMERIC_INVALID = "result_numeric_invalid"
    ID_MAPPING_MISMATCH = "id_mapping_mismatch"
    PREDECESSOR_MISMATCH = "predecessor_mismatch"


class StaInvalidationReason(str, Enum):
    TOPOLOGY_CHANGED = "topology_changed"
    CLOCK_CONSTRAINT_CHANGED = "clock_constraint_changed"
    LIBRARY_CHANGED = "library_changed"
    CORNER_CHANGED = "corner_changed"
    PARASITIC_CHANGED = "parasitic_changed"
    TIMING_INPUT_CHANGED = "timing_input_changed"


class StaObservationActionKind(str, Enum):
    READ = "read"
    REFERENCE_MEASUREMENT = "reference_measurement"
    SCATTER_REJECTION = "scatter_rejection"
    SCATTER_SUCCESS = "scatter_success"
    INVALIDATION = "invalidation"
    RELEASE = "release"


@dataclass(frozen=True)
class StaAnalysisContext:
    liberty_corner: str
    temperature: str
    rc_corner: str


@dataclass(frozen=True)
class StaSnapshotIdentity:
    fingerprint_schema_version: str
    session_token: int
    graph_generation: int
    topology_fingerprint: str
    clock_constraint_fingerprint: str
    library_fingerprint: str
    corner_fingerprint: str
    parasitic_fingerprint: str
    timing_input_fingerprint: str


@dataclass(frozen=True)
class StaSnapshotCounts:
    nodes: int
    arcs: int
    levels: int


@dataclass(frozen=True)
class StaBufferExtent:
    logical_size: int
    capacity: int


@dataclass(frozen=True)
class StaSnapshotBuffers:
    node_keys: StaBufferExtent
    arc_keys: StaBufferExtent
    out_row_offsets: StaBufferExtent
    out_arc_ids: StaBufferExtent
    in_row_offsets: StaBufferExtent
    in_arc_ids: StaBufferExtent
    level_offsets: StaBufferExtent
    level_nodes: StaBufferExtent
    node_to_level: StaBufferExtent


@dataclass(frozen=True)
class StaCapacityObservation:
    last_action: StaCapacityAction
    event_count: int


@dataclass(frozen=True)
class StaSupportObservation:
    reference_supported: bool
    unsupported_reasons: tuple[StaReferenceUnsupportedReason, ...]


@dataclass(frozen=True)
class StaTimingObservation:
    export: float
    reference: float | None
    scatter: float | None


@dataclass(frozen=True)
class StaModeledHostBytes:
    logical: int
    capacity: int


@dataclass(frozen=True)
class StaCurrentFingerprints:
    topology_fingerprint: str | None
    clock_constraint_fingerprint: str | None
    library_fingerprint: str | None
    corner_fingerprint: str | None
    parasitic_fingerprint: str | None
    timing_input_fingerprint: str | None


@dataclass(frozen=True)
class StaScatterRejectionEvent:
    reason: StaScatterRejectionReason
    writes_applied: int
    source: StaSnapshotIdentity | None
    current: StaSnapshotIdentity


@dataclass(frozen=True)
class StaInvalidationEvent:
    reason: StaInvalidationReason
    writes_applied: int
    previous_identity: StaSnapshotIdentity
    current_fingerprints: StaCurrentFingerprints


@dataclass(frozen=True)
class StaSnapshotObservation:
    schema_version: str
    state: StaSnapshotState
    identity: StaSnapshotIdentity
    counts: StaSnapshotCounts
    buffers: StaSnapshotBuffers
    capacity: StaCapacityObservation
    support: StaSupportObservation
    timing_ms: StaTimingObservation
    host_bytes: StaModeledHostBytes
    last_rejection: StaScatterRejectionEvent | None
    last_invalidation: StaInvalidationEvent | None


@dataclass(frozen=True)
class StaReadObservationAction:
    kind = StaObservationActionKind.READ


@dataclass(frozen=True)
class StaReferenceMeasurementAction:
    duration_ms: float
    kind = StaObservationActionKind.REFERENCE_MEASUREMENT


@dataclass(frozen=True)
class StaScatterRejectionAction:
    reason: StaScatterRejectionReason
    source: StaSnapshotIdentity | None
    duration_ms: float
    kind = StaObservationActionKind.SCATTER_REJECTION


@dataclass(frozen=True)
class StaScatterSuccessAction:
    duration_ms: float
    kind = StaObservationActionKind.SCATTER_SUCCESS


@dataclass(frozen=True)
class StaInvalidationAction:
    current_fingerprints: StaCurrentFingerprints
    duration_ms: float
    kind = StaObservationActionKind.INVALIDATION


@dataclass(frozen=True)
class StaReleaseObservationAction:
    kind = StaObservationActionKind.RELEASE


StaObservationAction: TypeAlias = (
    StaReadObservationAction
    | StaReferenceMeasurementAction
    | StaScatterRejectionAction
    | StaScatterSuccessAction
    | StaInvalidationAction
    | StaReleaseObservationAction
)


def _raise(message: str, field: str, category: str) -> NoReturn:
    raise StaSnapshotContractError(message, field=field, category=category)


def _raw_string(value: object, field: str) -> str:
    if type(value) is not str:
        _raise("must be an exact str", field, "value_type")
    typed_value = cast(str, value)
    if not typed_value:
        _raise("must not be empty", field, "range")
    if typed_value != typed_value.strip():
        _raise("must not have leading or trailing whitespace", field, "format")
    return typed_value


def _canonical_temperature(value: object, field: str) -> str:
    if isinstance(value, str) and type(value) is str:
        raw = _raw_string(value, field)
        if raw == _UNSPECIFIED_TEMPERATURE:
            return raw
    elif isinstance(value, (int, float, Decimal)) and type(value) in (int, float, Decimal):
        raw = str(value)
    else:
        _raise("must be an exact str, int, float, or Decimal", field, "value_type")
    try:
        decimal = Decimal(raw)
    except InvalidOperation:
        _raise("must be a decimal number or the unspecified sentinel", field, "format")
    if not decimal.is_finite():
        _raise("must be finite", field, "non_finite")
    if decimal.is_zero():
        return "0"
    canonical = format(decimal, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    return canonical


def normalize_sta_analysis_context(
    *, liberty_corner: str, temperature: str | int | float | Decimal, rc_corner: str
) -> StaAnalysisContext:
    """Normalize exact raw analysis inputs into their canonical string form."""

    return StaAnalysisContext(
        liberty_corner=_raw_string(liberty_corner, "$.liberty_corner"),
        temperature=_canonical_temperature(temperature, "$.temperature"),
        rc_corner=_raw_string(rc_corner, "$.rc_corner"),
    )


def validate_sta_analysis_context(context: StaAnalysisContext) -> None:
    """Require an already-canonical frozen context."""

    if type(context) is not StaAnalysisContext:
        _raise("must be a StaAnalysisContext", "$", "value_type")
    liberty = _raw_string(context.liberty_corner, "$.liberty_corner")
    temperature = _canonical_temperature(context.temperature, "$.temperature")
    rc_corner = _raw_string(context.rc_corner, "$.rc_corner")
    if (liberty, temperature, rc_corner) != (
        context.liberty_corner,
        context.temperature,
        context.rc_corner,
    ):
        _raise("must already be canonical", "$.temperature", "format")


def make_direct_sta_analysis_context() -> StaAnalysisContext:
    """Return the frozen context for STA runs without semantic corner inputs."""

    return StaAnalysisContext(
        liberty_corner=_DIRECT_LIBERTY_CORNER,
        temperature=_UNSPECIFIED_TEMPERATURE,
        rc_corner=_NO_RC_CORNER,
    )


def sta_analysis_context_to_native_mapping(
    context: StaAnalysisContext,
) -> dict[str, str]:
    """Serialize one canonical context to the native binding's exact mapping."""

    validate_sta_analysis_context(context)
    return {
        "liberty_corner": context.liberty_corner,
        "temperature": context.temperature,
        "rc_corner": context.rc_corner,
    }


def validate_sta_spef_rc_consistency(
    context: StaAnalysisContext, spef_path: str | os.PathLike[str] | None
) -> None:
    """Require SPEF presence and a semantic RC corner to agree in both directions."""

    validate_sta_analysis_context(context)
    has_spef = bool(spef_path)
    has_rc_corner = context.rc_corner != _NO_RC_CORNER
    if has_spef != has_rc_corner:
        _raise(
            "SPEF presence must match a non-sentinel RC corner",
            "$.rc_corner",
            "spef_rc_consistency",
        )


def _append_string(payload: bytearray, value: str) -> None:
    encoded = value.encode("utf-8")
    payload.extend(struct.pack(">Q", len(encoded)))
    payload.extend(encoded)


def _append_domain(payload: bytearray, domain: str) -> None:
    _append_string(payload, "ista-csr")
    _append_string(payload, domain)
    _append_string(payload, _SCHEMA_VERSION)


def canonical_analysis_context_bytes(context: StaAnalysisContext) -> bytes:
    """Encode context exactly like C++ ``canonicalAnalysisContextBytes``."""

    validate_sta_analysis_context(context)
    payload = bytearray()
    _append_domain(payload, "analysis-context")
    _append_string(payload, context.liberty_corner)
    _append_string(payload, context.temperature)
    _append_string(payload, context.rc_corner)
    return bytes(payload)


def corner_fingerprint(context: StaAnalysisContext) -> str:
    """Return the domain-separated component fingerprint used by observations."""

    context_payload = canonical_analysis_context_bytes(context)
    payload = bytearray()
    _append_domain(payload, "corner-fingerprint")
    payload.extend(struct.pack(">Q", len(context_payload)))
    payload.extend(context_payload)
    return hashlib.sha256(payload).hexdigest()


def _require_exact_type(value: object, expected: type[_T], field: str) -> _T:
    if not isinstance(value, expected) or type(value) is not expected:
        _raise(f"must be an exact {expected.__name__}", field, "value_type")
    return cast(_T, value)


def _enum_token(value: Enum, expected: type[_T], field: str) -> str:
    typed = _require_exact_type(value, expected, field)
    typed_enum = cast(Enum, typed)
    token = typed_enum.value
    if type(token) is not str:
        _raise("enum token must be a string", field, "value_type")
    return cast(str, token)


def _snapshot_identity_to_mapping(value: StaSnapshotIdentity, field: str) -> dict[str, object]:
    value = _require_exact_type(value, StaSnapshotIdentity, field)
    return {
        "fingerprint_schema_version": value.fingerprint_schema_version,
        "session_token": value.session_token,
        "graph_generation": value.graph_generation,
        "topology_fingerprint": value.topology_fingerprint,
        "clock_constraint_fingerprint": value.clock_constraint_fingerprint,
        "library_fingerprint": value.library_fingerprint,
        "corner_fingerprint": value.corner_fingerprint,
        "parasitic_fingerprint": value.parasitic_fingerprint,
        "timing_input_fingerprint": value.timing_input_fingerprint,
    }


def _current_fingerprints_to_mapping(
    value: StaCurrentFingerprints, field: str
) -> dict[str, object]:
    value = _require_exact_type(value, StaCurrentFingerprints, field)
    return {
        "topology_fingerprint": value.topology_fingerprint,
        "clock_constraint_fingerprint": value.clock_constraint_fingerprint,
        "library_fingerprint": value.library_fingerprint,
        "corner_fingerprint": value.corner_fingerprint,
        "parasitic_fingerprint": value.parasitic_fingerprint,
        "timing_input_fingerprint": value.timing_input_fingerprint,
    }


def _snapshot_observation_to_mapping(
    value: StaSnapshotObservation,
) -> dict[str, object]:
    value = _require_exact_type(value, StaSnapshotObservation, "$")
    _require_exact_type(value.counts, StaSnapshotCounts, "$.counts")
    _require_exact_type(value.buffers, StaSnapshotBuffers, "$.buffers")
    _require_exact_type(value.capacity, StaCapacityObservation, "$.capacity")
    _require_exact_type(value.support, StaSupportObservation, "$.support")
    _require_exact_type(value.timing_ms, StaTimingObservation, "$.timing_ms")
    _require_exact_type(value.host_bytes, StaModeledHostBytes, "$.host_bytes")
    _require_exact_type(
        value.support.unsupported_reasons,
        tuple,
        "$.support.unsupported_reasons",
    )
    buffer_names = (
        "node_keys",
        "arc_keys",
        "out_row_offsets",
        "out_arc_ids",
        "in_row_offsets",
        "in_arc_ids",
        "level_offsets",
        "level_nodes",
        "node_to_level",
    )
    buffers: dict[str, object] = {}
    for name in buffer_names:
        extent = _require_exact_type(
            getattr(value.buffers, name), StaBufferExtent, f"$.buffers.{name}"
        )
        buffers[name] = {"logical_size": extent.logical_size, "capacity": extent.capacity}
    rejection = value.last_rejection
    rejection_mapping: object = None
    if rejection is not None:
        rejection = _require_exact_type(rejection, StaScatterRejectionEvent, "$.last_rejection")
        rejection_mapping = {
            "reason": _enum_token(
                rejection.reason, StaScatterRejectionReason, "$.last_rejection.reason"
            ),
            "writes_applied": rejection.writes_applied,
            "source": (
                None
                if rejection.source is None
                else _snapshot_identity_to_mapping(rejection.source, "$.last_rejection.source")
            ),
            "current": _snapshot_identity_to_mapping(rejection.current, "$.last_rejection.current"),
        }
    invalidation = value.last_invalidation
    invalidation_mapping: object = None
    if invalidation is not None:
        invalidation = _require_exact_type(
            invalidation, StaInvalidationEvent, "$.last_invalidation"
        )
        invalidation_mapping = {
            "reason": _enum_token(
                invalidation.reason, StaInvalidationReason, "$.last_invalidation.reason"
            ),
            "writes_applied": invalidation.writes_applied,
            "previous_identity": _snapshot_identity_to_mapping(
                invalidation.previous_identity, "$.last_invalidation.previous_identity"
            ),
            "current_fingerprints": _current_fingerprints_to_mapping(
                invalidation.current_fingerprints,
                "$.last_invalidation.current_fingerprints",
            ),
        }
    return {
        "schema_version": value.schema_version,
        "state": _enum_token(value.state, StaSnapshotState, "$.state"),
        "identity": _snapshot_identity_to_mapping(value.identity, "$.identity"),
        "counts": {
            "nodes": value.counts.nodes,
            "arcs": value.counts.arcs,
            "levels": value.counts.levels,
        },
        "buffers": buffers,
        "capacity": {
            "last_action": _enum_token(
                value.capacity.last_action, StaCapacityAction, "$.capacity.last_action"
            ),
            "event_count": value.capacity.event_count,
        },
        "support": {
            "reference_supported": value.support.reference_supported,
            "unsupported_reasons": [
                _enum_token(
                    reason,
                    StaReferenceUnsupportedReason,
                    f"$.support.unsupported_reasons[{index}]",
                )
                for index, reason in enumerate(value.support.unsupported_reasons)
            ],
        },
        "timing_ms": {
            "export": value.timing_ms.export,
            "reference": value.timing_ms.reference,
            "scatter": value.timing_ms.scatter,
        },
        "host_bytes": {
            "logical": value.host_bytes.logical,
            "capacity": value.host_bytes.capacity,
        },
        "last_rejection": rejection_mapping,
        "last_invalidation": invalidation_mapping,
    }


def _translate_validation(action: Callable[[], _T]) -> _T:
    from ._sta_snapshot_validation import SnapshotValidationIssue

    try:
        return action()
    except SnapshotValidationIssue as error:
        raise StaSnapshotContractError(
            error.message, field=error.field, category=error.category
        ) from error


def snapshot_observation_from_mapping(
    value: Mapping[object, object] | None,
) -> StaSnapshotObservation | None:
    """Strictly parse an exact snapshot mapping or ``None``."""

    from ._sta_snapshot_validation import parse_snapshot_observation

    return _translate_validation(lambda: parse_snapshot_observation(value))


def validate_snapshot_observation(value: StaSnapshotObservation | None) -> None:
    """Validate an already-typed optional observation."""

    from ._sta_snapshot_validation import validate_typed_observation

    _translate_validation(lambda: validate_typed_observation(value))


def reduce_snapshot_observation(
    before: StaSnapshotObservation | None, action: StaObservationAction
) -> StaSnapshotObservation | None:
    """Apply one pure typed action without mutating ``before``."""

    from ._sta_snapshot_validation import reduce_observation

    return _translate_validation(lambda: reduce_observation(before, action))


def validate_snapshot_observation_transition(
    before: StaSnapshotObservation | None,
    after: StaSnapshotObservation | None,
    action: StaObservationAction,
) -> None:
    """Require ``after`` to be the exact reducer result for ``before`` and ``action``."""

    from ._sta_snapshot_validation import validate_transition

    _translate_validation(lambda: validate_transition(before, after, action))
