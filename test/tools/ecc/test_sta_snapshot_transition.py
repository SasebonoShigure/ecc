import json
from dataclasses import replace
from pathlib import Path

import pytest

from chipcompiler.tools.ecc.sta_snapshot import (
    StaCurrentFingerprints,
    StaInvalidationAction,
    StaObservationActionKind,
    StaReadObservationAction,
    StaReferenceMeasurementAction,
    StaReleaseObservationAction,
    StaScatterRejectionAction,
    StaScatterRejectionReason,
    StaScatterSuccessAction,
    StaSnapshotContractError,
    StaSnapshotState,
    reduce_snapshot_observation,
    snapshot_observation_from_mapping,
    validate_snapshot_observation_transition,
)

CORPUS_ROOT = (
    Path(__file__).parents[3]
    / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema/"
    "csr_snapshot_corpus_v1"
)
READY_MAPPING = json.loads((CORPUS_ROOT / "baselines/ready_empty.json").read_text(encoding="utf-8"))
TRANSITION_CASES = json.loads((CORPUS_ROOT / "transition_cases.json").read_text(encoding="utf-8"))[
    "cases"
]


def _ready():
    return snapshot_observation_from_mapping(READY_MAPPING)


def _fingerprints(observation, *, topology_null=False):
    identity = observation.identity
    return StaCurrentFingerprints(
        topology_fingerprint=None if topology_null else identity.topology_fingerprint,
        clock_constraint_fingerprint=identity.clock_constraint_fingerprint,
        library_fingerprint=identity.library_fingerprint,
        corner_fingerprint=identity.corner_fingerprint,
        parasitic_fingerprint=identity.parasitic_fingerprint,
        timing_input_fingerprint=identity.timing_input_fingerprint,
    )


def _baseline(name):
    ready = _ready()
    rejected = reduce_snapshot_observation(
        ready,
        StaScatterRejectionAction(
            reason=StaScatterRejectionReason.SCHEMA_MISMATCH,
            source=None,
            duration_ms=1.0,
        ),
    )
    invalidated = reduce_snapshot_observation(
        ready,
        StaInvalidationAction(
            current_fingerprints=_fingerprints(ready, topology_null=True),
            duration_ms=1.0,
        ),
    )
    values = {
        "absent": None,
        "ready": ready,
        "ready_rejected": rejected,
        "invalidated": invalidated,
        "released": reduce_snapshot_observation(ready, StaReleaseObservationAction()),
    }
    return values[name]


def _action(specification, before):
    token = specification["token"]
    duration = specification.get("duration_ms")
    if duration == "NaN":
        duration = float("nan")
    if token == "read":
        return StaReadObservationAction()
    if token == "release":
        return StaReleaseObservationAction()
    if token == "reference_measurement":
        return StaReferenceMeasurementAction(duration)
    if token == "scatter_success":
        return StaScatterSuccessAction(duration)
    if token == "scatter_rejection":
        return StaScatterRejectionAction(
            reason=StaScatterRejectionReason(specification["reason"]),
            source=specification["source"],
            duration_ms=duration,
        )
    if token == "invalidation":
        reference = before if before is not None else _ready()
        current = _fingerprints(
            reference,
            topology_null=specification["current_fingerprints"] == "topology_null",
        )
        return StaInvalidationAction(current, duration)
    raise AssertionError(f"unknown action token {token!r}")


@pytest.mark.parametrize("case", TRANSITION_CASES, ids=lambda case: case["case_id"])
def test_parent_reducer_matches_normative_transition_corpus(case):
    before = _baseline(case["baseline"])
    action = _action(case["action"], before)
    expected = case["expected"]
    if expected["validity"] == "invalid":
        with pytest.raises(StaSnapshotContractError) as raised:
            if isinstance(case["after"], dict):
                correct = reduce_snapshot_observation(before, action)
                wrong = replace(
                    correct,
                    timing_ms=replace(correct.timing_ms, reference=case["after"]["operand"]),
                )
                validate_snapshot_observation_transition(before, wrong, action)
            else:
                reduce_snapshot_observation(before, action)
        assert (raised.value.field, raised.value.category, raised.value.detail) == (
            expected["field"],
            expected["category"],
            expected["message"],
        )
        return
    after = reduce_snapshot_observation(before, action)
    validate_snapshot_observation_transition(before, after, action)


def test_action_kind_tokens_and_typed_action_kinds_are_exact():
    ready = _ready()
    expected = (
        (StaObservationActionKind.READ, "read", StaReadObservationAction()),
        (
            StaObservationActionKind.REFERENCE_MEASUREMENT,
            "reference_measurement",
            StaReferenceMeasurementAction(1.0),
        ),
        (
            StaObservationActionKind.SCATTER_REJECTION,
            "scatter_rejection",
            StaScatterRejectionAction(
                StaScatterRejectionReason.SCHEMA_MISMATCH,
                None,
                1.0,
            ),
        ),
        (
            StaObservationActionKind.SCATTER_SUCCESS,
            "scatter_success",
            StaScatterSuccessAction(1.0),
        ),
        (
            StaObservationActionKind.INVALIDATION,
            "invalidation",
            StaInvalidationAction(_fingerprints(ready), 1.0),
        ),
        (StaObservationActionKind.RELEASE, "release", StaReleaseObservationAction()),
    )
    assert tuple(StaObservationActionKind) == tuple(kind for kind, _, _ in expected)
    assert tuple(kind.value for kind in StaObservationActionKind) == tuple(
        token for _, token, _ in expected
    )
    for kind, token, action in expected:
        assert action.kind is kind
        assert action.kind.value == token


class _ForgedObservationAction:
    kind = StaObservationActionKind.READ


@pytest.mark.parametrize(
    "invalid_action",
    [object(), _ForgedObservationAction()],
    ids=["object", "forged_action"],
)
def test_unknown_action_types_have_one_exact_structured_error(invalid_action):
    ready = _ready()
    calls = (
        lambda: reduce_snapshot_observation(ready, invalid_action),
        lambda: validate_snapshot_observation_transition(ready, ready, invalid_action),
    )
    for call in calls:
        with pytest.raises(StaSnapshotContractError) as raised:
            call()
        assert (raised.value.field, raised.value.category, raised.value.detail) == (
            "$.action",
            "value_type",
            "unknown observation action type",
        )


def test_read_is_exact_and_legal_for_every_optional_state():
    states = (
        None,
        _baseline("ready"),
        _baseline("invalidated"),
        _baseline("released"),
    )
    for before in states:
        after = reduce_snapshot_observation(before, StaReadObservationAction())
        assert after is before
        validate_snapshot_observation_transition(before, after, StaReadObservationAction())


def test_reject_success_reject_overwrites_event_and_preserves_identity():
    ready = _ready()
    first = reduce_snapshot_observation(
        ready,
        StaScatterRejectionAction(StaScatterRejectionReason.SCHEMA_MISMATCH, None, 1.0),
    )
    success = reduce_snapshot_observation(first, StaScatterSuccessAction(2.0))
    second = reduce_snapshot_observation(
        success,
        StaScatterRejectionAction(StaScatterRejectionReason.SHAPE_MISMATCH, ready.identity, 3.0),
    )
    assert first.last_rejection.reason is StaScatterRejectionReason.SCHEMA_MISMATCH
    assert success.last_rejection is None
    assert second.last_rejection.reason is StaScatterRejectionReason.SHAPE_MISMATCH
    assert second.timing_ms.scatter == 3.0
    assert second.identity == ready.identity


def test_ready_invalidated_released_preserves_all_fields_except_state_on_release():
    ready = _ready()
    invalidated = reduce_snapshot_observation(
        ready,
        StaInvalidationAction(_fingerprints(ready, topology_null=True), 4.0),
    )
    released = reduce_snapshot_observation(invalidated, StaReleaseObservationAction())
    assert invalidated.state is StaSnapshotState.INVALIDATED
    assert released == replace(invalidated, state=StaSnapshotState.RELEASED)
    assert ready.state is StaSnapshotState.READY


def test_failed_reducer_does_not_modify_input():
    ready = _ready()
    invalidated = _baseline("invalidated")
    before = invalidated
    with pytest.raises(StaSnapshotContractError):
        reduce_snapshot_observation(invalidated, StaReferenceMeasurementAction(1.0))
    assert invalidated == before
    assert ready.state is StaSnapshotState.READY
