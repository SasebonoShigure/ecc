import copy
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from chipcompiler.tools.ecc.sta_snapshot import (
    StaInvalidationReason,
    StaScatterRejectionReason,
    StaSnapshotContractError,
    StaSnapshotObservation,
    StaSnapshotState,
    snapshot_observation_from_mapping,
    validate_snapshot_observation,
)

SCHEMA_ROOT = (
    Path(__file__).parents[3]
    / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema"
)
CORPUS_ROOT = SCHEMA_ROOT / "csr_snapshot_corpus_v1"
READY_PATH = CORPUS_ROOT / "baselines/ready_empty.json"
MAPPING_CASES = json.loads((CORPUS_ROOT / "mapping_cases.json").read_text(encoding="utf-8"))


def _ready_mapping():
    return json.loads(READY_PATH.read_text(encoding="utf-8"))


def _target_parent(document, target):
    parts = target[2:].split(".")
    current = document
    for part in parts[:-1]:
        current = current[part]
    return current, parts[-1]


def _rejection_fixture(document, *, with_source):
    identity = copy.deepcopy(document["identity"])
    return {
        "reason": "schema_mismatch",
        "writes_applied": 0,
        "source": copy.deepcopy(identity) if with_source else None,
        "current": copy.deepcopy(identity),
    }


def _apply_mapping_recipe(document, recipe):
    operation, target = recipe["op"], recipe["target"]
    if target == "$fixture.empty_graph_with_arc":
        document["counts"]["arcs"] = 1
        for key in ("arc_keys", "out_arc_ids", "in_arc_ids"):
            document["buffers"][key] = {"logical_size": 1, "capacity": 1}
        return document
    if operation == "add_non_string_key":
        document[recipe["operand"]] = 1
        return document
    if target == "$":
        return copy.deepcopy(recipe["operand"])
    parent, key = _target_parent(document, target)
    if operation == "delete_key":
        del parent[key]
        return document
    operand = recipe["operand"]
    if operand == "fixture:schema_mismatch_rejection":
        operand = _rejection_fixture(document, with_source=False)
    elif operand == "fixture:schema_mismatch_with_source":
        operand = _rejection_fixture(document, with_source=True)
    elif operation == "nan":
        operand = math.nan
    elif operation == "positive_infinity":
        operand = math.inf
    elif operation == "negative_infinity":
        operand = -math.inf
    parent[key] = copy.deepcopy(operand)
    return document


def _mapping_baseline(name):
    baseline = MAPPING_CASES["baselines"][name]
    return (
        copy.deepcopy(baseline)
        if not isinstance(baseline, str)
        else json.loads((CORPUS_ROOT / baseline).read_text(encoding="utf-8"))
    )


def test_parser_returns_frozen_typed_observation_and_preserves_json_mapping():
    mapping = _ready_mapping()
    observation = snapshot_observation_from_mapping(mapping)
    assert isinstance(observation, StaSnapshotObservation)
    assert observation.state is StaSnapshotState.READY
    assert observation.identity.session_token == 1
    assert observation.timing_ms.export == 0.0
    assert observation.buffers.out_row_offsets.logical_size == 1
    assert observation.support.unsupported_reasons == ()
    mapping["identity"]["session_token"] = 2
    assert observation.identity.session_token == 1
    assert snapshot_observation_from_mapping(None) is None


@pytest.mark.parametrize("case", MAPPING_CASES["cases"], ids=lambda case: case["case_id"])
def test_parent_parser_matches_normative_mapping_corpus_field_and_category(case):
    baseline = _mapping_baseline(case["baseline"])
    snapshot_observation_from_mapping(baseline)
    mutated = _apply_mapping_recipe(copy.deepcopy(baseline), case["recipe"])
    expected = case["expected"]
    if expected["validity"] == "valid":
        snapshot_observation_from_mapping(mutated)
        return
    with pytest.raises(StaSnapshotContractError) as raised:
        snapshot_observation_from_mapping(mutated)
    assert (raised.value.field, raised.value.category) == (
        expected["field"],
        expected["category"],
    )


def _event_mapping():
    mapping = _ready_mapping()
    mapping["timing_ms"]["scatter"] = 1.0
    return mapping


@pytest.mark.parametrize(
    ("reason", "source_mutation"),
    [
        ("schema_mismatch", None),
        ("session_mismatch", ("session_token", 2)),
        ("generation_mismatch", ("graph_generation", 1)),
        ("source_identity_mismatch", ("library_fingerprint", "a" * 64)),
        ("shape_mismatch", "equal"),
        ("result_numeric_invalid", "equal"),
        ("id_mapping_mismatch", "equal"),
        ("predecessor_mismatch", "equal"),
    ],
)
def test_all_rejection_reason_source_relations(reason, source_mutation):
    mapping = _event_mapping()
    identity = copy.deepcopy(mapping["identity"])
    source = None if source_mutation is None else copy.deepcopy(identity)
    if isinstance(source_mutation, tuple):
        source[source_mutation[0]] = source_mutation[1]
    mapping["last_rejection"] = {
        "reason": reason,
        "writes_applied": 0,
        "source": source,
        "current": copy.deepcopy(identity),
    }
    observation = snapshot_observation_from_mapping(mapping)
    assert observation.last_rejection.reason is StaScatterRejectionReason(reason)
    if reason == "generation_mismatch":
        assert observation.last_rejection.source.graph_generation == 1


@pytest.mark.parametrize(
    ("fingerprint", "reason"),
    [
        ("topology_fingerprint", "topology_changed"),
        ("clock_constraint_fingerprint", "clock_constraint_changed"),
        ("library_fingerprint", "library_changed"),
        ("corner_fingerprint", "corner_changed"),
        ("parasitic_fingerprint", "parasitic_changed"),
        ("timing_input_fingerprint", "timing_input_changed"),
    ],
)
def test_all_invalidation_first_difference_relations(fingerprint, reason):
    mapping = _event_mapping()
    identity = mapping["identity"]
    current = {
        key: identity[key]
        for key in (
            "topology_fingerprint",
            "clock_constraint_fingerprint",
            "library_fingerprint",
            "corner_fingerprint",
            "parasitic_fingerprint",
            "timing_input_fingerprint",
        )
    }
    current[fingerprint] = None
    mapping.update({"state": "invalidated", "last_rejection": None})
    mapping["last_invalidation"] = {
        "reason": reason,
        "writes_applied": 0,
        "previous_identity": copy.deepcopy(identity),
        "current_fingerprints": current,
    }
    observation = snapshot_observation_from_mapping(mapping)
    assert observation.state is StaSnapshotState.INVALIDATED
    assert observation.last_invalidation.reason is StaInvalidationReason(reason)
    mapping["state"] = "released"
    assert snapshot_observation_from_mapping(mapping).state is StaSnapshotState.RELEASED


def test_identity_generation_layers_do_not_collapse_foreign_source_to_committed():
    mapping = _event_mapping()
    source = copy.deepcopy(mapping["identity"])
    source["graph_generation"] = (1 << 64) - 1
    mapping["last_rejection"] = {
        "reason": "generation_mismatch",
        "writes_applied": 0,
        "source": source,
        "current": copy.deepcopy(mapping["identity"]),
    }
    observation = snapshot_observation_from_mapping(mapping)
    assert observation.last_rejection.source.graph_generation == (1 << 64) - 1


def _assert_mapping_error(mapping, field, category):
    with pytest.raises(StaSnapshotContractError) as raised:
        snapshot_observation_from_mapping(mapping)
    assert (raised.value.field, raised.value.category) == (field, category)


def test_scalar_schema_order_precedes_deferred_cross_field_relations():
    mapping = _ready_mapping()
    mapping["identity"]["fingerprint_schema_version"] = "1.0.0"
    mapping["identity"]["graph_generation"] = -1
    _assert_mapping_error(mapping, "$.identity.fingerprint_schema_version", "enum")

    mapping = _ready_mapping()
    mapping["buffers"]["out_row_offsets"]["capacity"] = 0
    mapping["support"]["reference_supported"] = "yes"
    _assert_mapping_error(mapping, "$.support.reference_supported", "value_type")

    mapping = _event_mapping()
    source = copy.deepcopy(mapping["identity"])
    source["fingerprint_schema_version"] = "1.0.0"
    current = copy.deepcopy(mapping["identity"])
    current["session_token"] = 2
    mapping["last_rejection"] = {
        "reason": "schema_mismatch",
        "writes_applied": 0,
        "source": source,
        "current": current,
    }
    _assert_mapping_error(
        mapping,
        "$.last_rejection.source.fingerprint_schema_version",
        "enum",
    )

    mapping = _event_mapping()
    previous = copy.deepcopy(mapping["identity"])
    previous["session_token"] = 2
    current = {
        key: mapping["identity"][key]
        for key in (
            "topology_fingerprint",
            "clock_constraint_fingerprint",
            "library_fingerprint",
            "corner_fingerprint",
            "parasitic_fingerprint",
            "timing_input_fingerprint",
        )
    }
    current["topology_fingerprint"] = "uppercase"
    mapping.update({"state": "invalidated", "last_rejection": None})
    mapping["last_invalidation"] = {
        "reason": "topology_changed",
        "writes_applied": 0,
        "previous_identity": previous,
        "current_fingerprints": current,
    }
    _assert_mapping_error(
        mapping,
        "$.last_invalidation.current_fingerprints.topology_fingerprint",
        "format",
    )


def test_typed_validator_rejects_non_tuple_support_reasons_structurally():
    observation = snapshot_observation_from_mapping(_ready_mapping())
    malformed = replace(
        observation,
        support=replace(observation.support, unsupported_reasons=[]),
    )
    with pytest.raises(StaSnapshotContractError) as raised:
        validate_snapshot_observation(malformed)
    assert (raised.value.field, raised.value.category) == (
        "$.support.unsupported_reasons",
        "value_type",
    )
