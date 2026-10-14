"""Private strict parsing and transition rules for :mod:`sta_snapshot`."""

import math
import re
from collections.abc import Mapping
from dataclasses import replace
from enum import Enum
from typing import TYPE_CHECKING, NoReturn, TypeVar

if TYPE_CHECKING:
    from . import sta_snapshot as model_types

_EnumT = TypeVar("_EnumT", bound=Enum)
_ValueT = TypeVar("_ValueT")

_U64_MAX = (1 << 64) - 1
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTITY_KEYS = (
    "fingerprint_schema_version",
    "session_token",
    "graph_generation",
    "topology_fingerprint",
    "clock_constraint_fingerprint",
    "library_fingerprint",
    "corner_fingerprint",
    "parasitic_fingerprint",
    "timing_input_fingerprint",
)
_FINGERPRINT_KEYS = _IDENTITY_KEYS[3:]
_BUFFER_KEYS = (
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
_OBSERVATION_KEYS = (
    "schema_version",
    "state",
    "identity",
    "counts",
    "buffers",
    "capacity",
    "support",
    "timing_ms",
    "host_bytes",
    "last_rejection",
    "last_invalidation",
)


class SnapshotValidationIssue(ValueError):
    """Internal structured issue translated by the public facade."""

    def __init__(self, message: str, *, field: str, category: str) -> None:
        super().__init__(f"{field}: {message}")
        self.message = message
        self.field = field
        self.category = category


def _fail(field: str, category: str, message: str) -> NoReturn:
    raise SnapshotValidationIssue(message, field=field, category=category)


def _mapping(value: object, field: str, keys: tuple[str, ...]) -> dict[str, object]:
    if not isinstance(value, Mapping):
        _fail(field, "value_type", "must be a mapping")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str) or type(key) is not str:
            _fail(field, "key_type", "mapping keys must be exact strings")
        result[key] = item
    for key in keys:
        if key not in result:
            _fail(f"{field}.{key}", "missing_key", "required key is missing")
    extra = sorted(set(result) - set(keys))
    if extra:
        _fail(f"{field}.{extra[0]}", "extra_key", "unexpected key")
    return result


def _exact_type(value: object, expected: type[_ValueT], field: str) -> _ValueT:
    if not isinstance(value, expected) or type(value) is not expected:
        _fail(field, "value_type", f"must be an exact {expected.__name__}")
    return value


def _u64(value: object, field: str, *, positive: bool = False) -> int:
    if type(value) is not int:
        _fail(field, "value_type", "must be an integer")
    minimum = 1 if positive else 0
    if value < minimum or value > _U64_MAX:
        _fail(field, "range", f"must be in [{minimum}, {_U64_MAX}]")
    return value


def _const(value: object, expected: str, field: str) -> str:
    if type(value) is not str:
        _fail(field, "value_type", "must be a string")
    if value != expected:
        _fail(field, "enum", f"must equal {expected!r}")
    return value


def _hash(value: object, field: str) -> str:
    if type(value) is not str:
        _fail(field, "value_type", "must be a string")
    if _SHA256.fullmatch(value) is None:
        _fail(field, "format", "must be a lowercase SHA-256 hex digest")
    return value


def _optional_hash(value: object, field: str) -> str | None:
    return None if value is None else _hash(value, field)


def _duration(value: object, field: str) -> float:
    if type(value) is not int and type(value) is not float:
        _fail(field, "value_type", "must be a number")
    try:
        result = float(value)
    except OverflowError:
        _fail(field, "non_finite", "must convert to a finite float")
    if not math.isfinite(result):
        _fail(field, "non_finite", "must be finite")
    if result < 0:
        _fail(field, "range", "must be nonnegative")
    return result


def _enum(value: object, enum_type: type[_EnumT], field: str) -> _EnumT:
    if type(value) is not str:
        _fail(field, "value_type", "must be a string")
    try:
        return enum_type(value)
    except ValueError:
        _fail(field, "enum", f"unknown {enum_type.__name__} token")


def _parse_identity(
    value: object, field: str, *, committed: bool
) -> "model_types.StaSnapshotIdentity":
    from . import sta_snapshot as model

    raw = _mapping(value, field, _IDENTITY_KEYS)
    schema_version = _const(
        raw["fingerprint_schema_version"], "2.0.0", f"{field}.fingerprint_schema_version"
    )
    session_token = _u64(raw["session_token"], f"{field}.session_token", positive=True)
    generation = _u64(raw["graph_generation"], f"{field}.graph_generation")
    identity = model.StaSnapshotIdentity(
        fingerprint_schema_version=schema_version,
        session_token=session_token,
        graph_generation=generation,
        **{key: _hash(raw[key], f"{field}.{key}") for key in _FINGERPRINT_KEYS},
    )
    if committed and generation != 0:
        _fail(
            f"{field}.graph_generation",
            "enum",
            "committed identity generation must be zero",
        )
    return identity


def _parse_counts(value: object, field: str) -> "model_types.StaSnapshotCounts":
    from . import sta_snapshot as model

    raw = _mapping(value, field, ("nodes", "arcs", "levels"))
    return model.StaSnapshotCounts(
        nodes=_u64(raw["nodes"], f"{field}.nodes"),
        arcs=_u64(raw["arcs"], f"{field}.arcs"),
        levels=_u64(raw["levels"], f"{field}.levels"),
    )


def _parse_extent(value: object, field: str) -> "model_types.StaBufferExtent":
    from . import sta_snapshot as model

    raw = _mapping(value, field, ("logical_size", "capacity"))
    logical = _u64(raw["logical_size"], f"{field}.logical_size")
    capacity = _u64(raw["capacity"], f"{field}.capacity")
    return model.StaBufferExtent(logical_size=logical, capacity=capacity)


def _parse_buffers(value: object, field: str) -> "model_types.StaSnapshotBuffers":
    from . import sta_snapshot as model

    raw = _mapping(value, field, _BUFFER_KEYS)
    return model.StaSnapshotBuffers(
        **{key: _parse_extent(raw[key], f"{field}.{key}") for key in _BUFFER_KEYS}
    )


def _parse_capacity(value: object, field: str) -> "model_types.StaCapacityObservation":
    from . import sta_snapshot as model

    raw = _mapping(value, field, ("last_action", "event_count"))
    action = _enum(raw["last_action"], model.StaCapacityAction, f"{field}.last_action")
    count = _u64(raw["event_count"], f"{field}.event_count")
    if action is not model.StaCapacityAction.INITIAL_ALLOCATE:
        _fail(f"{field}.last_action", "enum", "must be initial_allocate")
    if count != 1:
        _fail(f"{field}.event_count", "enum", "must equal 1")
    return model.StaCapacityObservation(last_action=action, event_count=count)


def _parse_support(value: object, field: str) -> "model_types.StaSupportObservation":
    from . import sta_snapshot as model

    raw = _mapping(value, field, ("reference_supported", "unsupported_reasons"))
    supported = _exact_type(raw["reference_supported"], bool, f"{field}.reference_supported")
    reasons_raw = _exact_type(raw["unsupported_reasons"], list, f"{field}.unsupported_reasons")
    reasons = tuple(
        _enum(item, model.StaReferenceUnsupportedReason, f"{field}.unsupported_reasons[{index}]")
        for index, item in enumerate(reasons_raw)
    )
    return model.StaSupportObservation(reference_supported=supported, unsupported_reasons=reasons)


def _parse_timing(value: object, field: str) -> "model_types.StaTimingObservation":
    from . import sta_snapshot as model

    raw = _mapping(value, field, ("export", "reference", "scatter"))
    return model.StaTimingObservation(
        export=_duration(raw["export"], f"{field}.export"),
        reference=(
            None if raw["reference"] is None else _duration(raw["reference"], f"{field}.reference")
        ),
        scatter=(None if raw["scatter"] is None else _duration(raw["scatter"], f"{field}.scatter")),
    )


def _parse_host_bytes(value: object, field: str) -> "model_types.StaModeledHostBytes":
    from . import sta_snapshot as model

    raw = _mapping(value, field, ("logical", "capacity"))
    logical = _u64(raw["logical"], f"{field}.logical", positive=True)
    capacity = _u64(raw["capacity"], f"{field}.capacity", positive=True)
    return model.StaModeledHostBytes(logical=logical, capacity=capacity)


def _parse_current_fingerprints(value: object, field: str) -> "model_types.StaCurrentFingerprints":
    from . import sta_snapshot as model

    raw = _mapping(value, field, _FINGERPRINT_KEYS)
    return model.StaCurrentFingerprints(
        **{key: _optional_hash(raw[key], f"{field}.{key}") for key in _FINGERPRINT_KEYS}
    )


def _first_invalidation(
    identity: "model_types.StaSnapshotIdentity", current: "model_types.StaCurrentFingerprints"
) -> "model_types.StaInvalidationReason | None":
    from . import sta_snapshot as model

    reasons = (
        model.StaInvalidationReason.TOPOLOGY_CHANGED,
        model.StaInvalidationReason.CLOCK_CONSTRAINT_CHANGED,
        model.StaInvalidationReason.LIBRARY_CHANGED,
        model.StaInvalidationReason.CORNER_CHANGED,
        model.StaInvalidationReason.PARASITIC_CHANGED,
        model.StaInvalidationReason.TIMING_INPUT_CHANGED,
    )
    for key, reason in zip(_FINGERPRINT_KEYS, reasons, strict=True):
        if getattr(current, key) != getattr(identity, key):
            return reason
    return None


def _parse_rejection(value: object, field: str) -> "model_types.StaScatterRejectionEvent | None":
    from . import sta_snapshot as model

    if value is None:
        return None
    raw = _mapping(value, field, ("reason", "writes_applied", "source", "current"))
    reason = _enum(raw["reason"], model.StaScatterRejectionReason, f"{field}.reason")
    writes = _u64(raw["writes_applied"], f"{field}.writes_applied")
    if writes != 0:
        _fail(f"{field}.writes_applied", "enum", "must equal 0")
    source = (
        None
        if raw["source"] is None
        else _parse_identity(raw["source"], f"{field}.source", committed=False)
    )
    current = _parse_identity(raw["current"], f"{field}.current", committed=True)
    return model.StaScatterRejectionEvent(
        reason=reason, writes_applied=writes, source=source, current=current
    )


def _parse_invalidation(value: object, field: str) -> "model_types.StaInvalidationEvent | None":
    from . import sta_snapshot as model

    if value is None:
        return None
    raw = _mapping(
        value,
        field,
        ("reason", "writes_applied", "previous_identity", "current_fingerprints"),
    )
    reason = _enum(raw["reason"], model.StaInvalidationReason, f"{field}.reason")
    writes = _u64(raw["writes_applied"], f"{field}.writes_applied")
    if writes != 0:
        _fail(f"{field}.writes_applied", "enum", "must equal 0")
    previous = _parse_identity(
        raw["previous_identity"], f"{field}.previous_identity", committed=True
    )
    current = _parse_current_fingerprints(
        raw["current_fingerprints"], f"{field}.current_fingerprints"
    )
    return model.StaInvalidationEvent(
        reason=reason,
        writes_applied=writes,
        previous_identity=previous,
        current_fingerprints=current,
    )


def _validate_buffer_equations(
    counts: "model_types.StaSnapshotCounts", buffers: "model_types.StaSnapshotBuffers"
) -> None:
    expected = {
        "node_keys": counts.nodes,
        "arc_keys": counts.arcs,
        "out_row_offsets": counts.nodes + 1,
        "out_arc_ids": counts.arcs,
        "in_row_offsets": counts.nodes + 1,
        "in_arc_ids": counts.arcs,
        "level_offsets": counts.levels + 1,
        "level_nodes": counts.nodes,
        "node_to_level": counts.nodes,
    }
    for key in _BUFFER_KEYS:
        if expected[key] > _U64_MAX:
            _fail(f"$.buffers.{key}.logical_size", "overflow", "derived size overflows u64")
        if getattr(buffers, key).logical_size != expected[key]:
            _fail(
                f"$.buffers.{key}.logical_size",
                "relationship",
                "does not match the count-derived logical size",
            )


def _validate_rejection_relation(
    event: "model_types.StaScatterRejectionEvent",
    identity: "model_types.StaSnapshotIdentity",
) -> None:
    from . import sta_snapshot as model

    if event.current != identity:
        _fail("$.last_rejection.current", "relationship", "must equal the outer identity")
    source = event.source
    if event.reason is model.StaScatterRejectionReason.SCHEMA_MISMATCH:
        valid = source is None
    elif source is None:
        valid = False
    elif event.reason is model.StaScatterRejectionReason.SESSION_MISMATCH:
        valid = source.session_token != event.current.session_token
    elif event.reason is model.StaScatterRejectionReason.GENERATION_MISMATCH:
        valid = (
            source.session_token == event.current.session_token
            and source.graph_generation != event.current.graph_generation
        )
    elif event.reason is model.StaScatterRejectionReason.SOURCE_IDENTITY_MISMATCH:
        valid = (
            source.session_token == event.current.session_token
            and source.graph_generation == event.current.graph_generation
            and source != event.current
        )
    else:
        valid = source == event.current
    if not valid:
        _fail("$.last_rejection", "relationship", "reason/source identity relationship is invalid")


def _validate_invalidation_relation(
    event: "model_types.StaInvalidationEvent",
    identity: "model_types.StaSnapshotIdentity",
) -> None:
    if event.previous_identity != identity:
        _fail(
            "$.last_invalidation.previous_identity",
            "relationship",
            "must equal the outer identity",
        )
    inferred = _first_invalidation(identity, event.current_fingerprints)
    if inferred is None:
        _fail(
            "$.last_invalidation",
            "relationship",
            "at least one current fingerprint must differ or be null",
        )
    if event.reason is not inferred:
        _fail(
            "$.last_invalidation.reason",
            "relationship",
            "must identify the first changed fingerprint",
        )


def _validate_observation_relations(
    observation: "model_types.StaSnapshotObservation",
) -> None:
    from . import sta_snapshot as model

    counts, buffers = observation.counts, observation.buffers
    for key in _BUFFER_KEYS:
        extent = getattr(buffers, key)
        if extent.capacity < extent.logical_size:
            _fail(f"$.buffers.{key}", "relationship", "capacity must be at least logical_size")
    _validate_buffer_equations(counts, buffers)
    if (counts.nodes == 0) != (counts.levels == 0):
        _fail("$.counts", "relationship", "nodes are empty exactly when levels are empty")
    if counts.nodes == 0 and counts.arcs != 0:
        _fail("$.counts.arcs", "relationship", "an empty graph cannot contain arcs")
    if counts.nodes and not 1 <= counts.levels <= counts.nodes:
        _fail("$.counts.levels", "relationship", "must be in [1, nodes] for a nonempty graph")
    reasons = observation.support.unsupported_reasons
    order = {reason: index for index, reason in enumerate(model.StaReferenceUnsupportedReason)}
    if list(reasons) != sorted(set(reasons), key=order.__getitem__):
        _fail(
            "$.support.unsupported_reasons",
            "relationship",
            "reasons must be unique and in stable enum order",
        )
    if observation.support.reference_supported != (not reasons):
        _fail("$.support", "relationship", "reference_supported must equal reasons.empty")
    if observation.host_bytes.capacity < observation.host_bytes.logical:
        _fail("$.host_bytes", "relationship", "capacity must be at least logical")
    if observation.last_rejection is not None:
        _validate_rejection_relation(observation.last_rejection, observation.identity)
    if observation.last_invalidation is not None:
        _validate_invalidation_relation(observation.last_invalidation, observation.identity)
    if (
        observation.last_rejection is not None or observation.last_invalidation is not None
    ) and observation.timing_ms.scatter is None:
        _fail("$.timing_ms.scatter", "relationship", "an event requires scatter timing")
    if observation.state is model.StaSnapshotState.READY:
        valid_events = observation.last_invalidation is None
    elif observation.state is model.StaSnapshotState.INVALIDATED:
        valid_events = (
            observation.last_rejection is None and observation.last_invalidation is not None
        )
    else:
        valid_events = (
            observation.last_invalidation is None
            or observation.last_rejection is None
            and observation.last_invalidation is not None
        )
    if not valid_events:
        _fail("$.state", "relationship", "state and event combination is invalid")


def parse_snapshot_observation(value: object) -> "model_types.StaSnapshotObservation | None":
    from . import sta_snapshot as model

    if value is None:
        return None
    raw = _mapping(value, "$", _OBSERVATION_KEYS)
    schema_version = _const(raw["schema_version"], "1.0.0", "$.schema_version")
    state = _enum(raw["state"], model.StaSnapshotState, "$.state")
    identity = _parse_identity(raw["identity"], "$.identity", committed=True)
    counts = _parse_counts(raw["counts"], "$.counts")
    buffers = _parse_buffers(raw["buffers"], "$.buffers")
    capacity = _parse_capacity(raw["capacity"], "$.capacity")
    support = _parse_support(raw["support"], "$.support")
    timing = _parse_timing(raw["timing_ms"], "$.timing_ms")
    host = _parse_host_bytes(raw["host_bytes"], "$.host_bytes")
    rejection = _parse_rejection(raw["last_rejection"], "$.last_rejection")
    invalidation = _parse_invalidation(raw["last_invalidation"], "$.last_invalidation")
    observation = model.StaSnapshotObservation(
        schema_version=schema_version,
        state=state,
        identity=identity,
        counts=counts,
        buffers=buffers,
        capacity=capacity,
        support=support,
        timing_ms=timing,
        host_bytes=host,
        last_rejection=rejection,
        last_invalidation=invalidation,
    )
    _validate_observation_relations(observation)
    return observation


def validate_typed_observation(value: "model_types.StaSnapshotObservation | None") -> None:
    from . import sta_snapshot as model

    if value is None:
        return
    parsed = parse_snapshot_observation(model._snapshot_observation_to_mapping(value))
    if parsed != value:
        _fail("$", "value_type", "typed observation contains noncanonical scalar types")


def _normalize_action(
    action: "model_types.StaObservationAction",
) -> "model_types.StaObservationAction":
    from . import sta_snapshot as model

    if type(action) is model.StaReadObservationAction:
        return action
    if type(action) is model.StaReleaseObservationAction:
        return action
    if type(action) is model.StaReferenceMeasurementAction:
        return replace(action, duration_ms=_duration(action.duration_ms, "$.action.duration_ms"))
    if type(action) is model.StaScatterSuccessAction:
        return replace(action, duration_ms=_duration(action.duration_ms, "$.action.duration_ms"))
    if type(action) is model.StaScatterRejectionAction:
        _exact_type(action.reason, model.StaScatterRejectionReason, "$.action.reason")
        if action.source is not None:
            _parse_identity(
                model._snapshot_identity_to_mapping(action.source, "$.action.source"),
                "$.action.source",
                committed=False,
            )
        return replace(action, duration_ms=_duration(action.duration_ms, "$.action.duration_ms"))
    if type(action) is model.StaInvalidationAction:
        _parse_current_fingerprints(
            model._current_fingerprints_to_mapping(
                action.current_fingerprints, "$.action.current_fingerprints"
            ),
            "$.action.current_fingerprints",
        )
        return replace(action, duration_ms=_duration(action.duration_ms, "$.action.duration_ms"))
    _fail("$.action", "value_type", "unknown observation action type")


def _require_ready(
    before: "model_types.StaSnapshotObservation | None", action: "model_types.StaObservationAction"
) -> "model_types.StaSnapshotObservation":
    from . import sta_snapshot as model

    if before is None or before.state is not model.StaSnapshotState.READY:
        state = "absent" if before is None else before.state.value
        _fail(
            "$.state",
            "transition",
            f"{action.kind.value} is not allowed for {state} observation",
        )
    return before


def reduce_observation(
    before: "model_types.StaSnapshotObservation | None",
    raw_action: "model_types.StaObservationAction",
) -> "model_types.StaSnapshotObservation | None":
    from . import sta_snapshot as model

    validate_typed_observation(before)
    action = _normalize_action(raw_action)
    if type(action) is model.StaReadObservationAction:
        return before
    if type(action) is model.StaReleaseObservationAction:
        if before is None:
            return None
        if before.state is model.StaSnapshotState.RELEASED:
            _fail("$.state", "transition", "release is not allowed for released observation")
        result = replace(before, state=model.StaSnapshotState.RELEASED)
    elif type(action) is model.StaReferenceMeasurementAction:
        before = _require_ready(before, action)
        result = replace(
            before,
            timing_ms=replace(before.timing_ms, reference=action.duration_ms),
        )
    elif type(action) is model.StaScatterSuccessAction:
        before = _require_ready(before, action)
        result = replace(
            before,
            timing_ms=replace(before.timing_ms, scatter=action.duration_ms),
            last_rejection=None,
        )
    elif type(action) is model.StaScatterRejectionAction:
        before = _require_ready(before, action)
        event = model.StaScatterRejectionEvent(
            reason=action.reason,
            writes_applied=0,
            source=action.source,
            current=before.identity,
        )
        result = replace(
            before,
            timing_ms=replace(before.timing_ms, scatter=action.duration_ms),
            last_rejection=event,
        )
    elif type(action) is model.StaInvalidationAction:
        before = _require_ready(before, action)
        reason = _first_invalidation(before.identity, action.current_fingerprints)
        if reason is None:
            _fail(
                "$.action.current_fingerprints",
                "relationship",
                "invalidation requires a changed or null fingerprint",
            )
        event = model.StaInvalidationEvent(
            reason=reason,
            writes_applied=0,
            previous_identity=before.identity,
            current_fingerprints=action.current_fingerprints,
        )
        result = replace(
            before,
            state=model.StaSnapshotState.INVALIDATED,
            timing_ms=replace(before.timing_ms, scatter=action.duration_ms),
            last_rejection=None,
            last_invalidation=event,
        )
    else:
        _fail("$.action", "value_type", "unknown observation action type")
    validate_typed_observation(result)
    return result


def validate_transition(
    before: "model_types.StaSnapshotObservation | None",
    after: "model_types.StaSnapshotObservation | None",
    action: "model_types.StaObservationAction",
) -> None:
    validate_typed_observation(before)
    validate_typed_observation(after)
    expected = reduce_observation(before, action)
    if after != expected:
        _fail("$", "transition", "after observation must equal the exact reducer result")
