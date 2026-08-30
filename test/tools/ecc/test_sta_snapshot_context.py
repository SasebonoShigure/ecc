import hashlib
import struct
from decimal import Decimal

import pytest

from chipcompiler.tools.ecc.sta_mode import StaExecutionContractError
from chipcompiler.tools.ecc.sta_snapshot import (
    StaAnalysisContext,
    StaSnapshotContractError,
    canonical_analysis_context_bytes,
    corner_fingerprint,
    normalize_sta_analysis_context,
    validate_sta_analysis_context,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (25, "25"),
        (25.0, "25"),
        ("25.000", "25"),
        ("2.5e1", "25"),
        (Decimal("25.000"), "25"),
        (-0.0, "0"),
        ("-0.000", "0"),
        ("__unspecified_temperature__", "__unspecified_temperature__"),
    ],
)
def test_temperature_normalization(value, expected):
    assert normalize_sta_analysis_context(
        liberty_corner="slow", temperature=value, rc_corner="rc_worst"
    ) == StaAnalysisContext("slow", expected, "rc_worst")


@pytest.mark.parametrize(
    ("field", "value", "category"),
    [
        ("liberty_corner", "", "range"),
        ("liberty_corner", " slow", "format"),
        ("liberty_corner", 1, "value_type"),
        ("rc_corner", "rc ", "format"),
        ("rc_corner", True, "value_type"),
        ("temperature", True, "value_type"),
        ("temperature", object(), "value_type"),
        ("temperature", " 25", "format"),
        ("temperature", "not-a-number", "format"),
        ("temperature", float("nan"), "non_finite"),
        ("temperature", float("inf"), "non_finite"),
        ("temperature", Decimal("-Infinity"), "non_finite"),
    ],
)
def test_context_normalizer_rejects_nonexact_inputs(field, value, category):
    arguments = {
        "liberty_corner": "slow",
        "temperature": 25,
        "rc_corner": "rc_worst",
    }
    arguments[field] = value
    with pytest.raises(StaSnapshotContractError) as raised:
        normalize_sta_analysis_context(**arguments)
    assert raised.value.field == f"$.{field}"
    assert raised.value.category == category
    assert isinstance(raised.value, StaExecutionContractError)


def test_validator_requires_an_already_canonical_frozen_context():
    validate_sta_analysis_context(StaAnalysisContext("slow", "25", "rc"))
    with pytest.raises(StaSnapshotContractError) as raised:
        validate_sta_analysis_context(StaAnalysisContext("slow", "25.0", "rc"))
    assert (raised.value.field, raised.value.category) == ("$.temperature", "format")
    with pytest.raises(StaSnapshotContractError) as raised:
        validate_sta_analysis_context(("slow", "25", "rc"))
    assert (raised.value.field, raised.value.category) == ("$", "value_type")


@pytest.mark.parametrize(
    ("corner", "payload_sha", "component_sha", "encoded_length"),
    [
        (
            "slow",
            "9d72757619bf1225c9888aa02b1f9917c8ea54a475754a8aae5939a7a96a1b83",
            "095aeaf315c1c903fb0d166788cf05aa90af0055e41a25ae86e3458ce5f62a2a",
            4,
        ),
        (
            "慢",
            "06402d67b192a27d7caef43a34054c58938df1e20fd5b9aefaffc5bc8486b8dd",
            "e3bafb5e252ccc546ba306fd33f30122773840f1bc37a616752ebb96da26eec2",
            3,
        ),
    ],
)
def test_analysis_context_double_layer_known_answers(
    corner, payload_sha, component_sha, encoded_length
):
    context = normalize_sta_analysis_context(
        liberty_corner=corner,
        temperature=25,
        rc_corner="__no_rc_corner__",
    )
    payload = canonical_analysis_context_bytes(context)
    encoded_corner = corner.encode("utf-8")
    position = payload.index(encoded_corner)
    assert struct.unpack(">Q", payload[position - 8 : position])[0] == encoded_length
    assert hashlib.sha256(payload).hexdigest() == payload_sha
    assert corner_fingerprint(context) == component_sha


def test_raw_context_changes_component_fingerprint_without_sanitization():
    slow = normalize_sta_analysis_context(liberty_corner="slow/a", temperature=25, rc_corner="rc/a")
    other = normalize_sta_analysis_context(
        liberty_corner="slow_a", temperature=25, rc_corner="rc_a"
    )
    assert canonical_analysis_context_bytes(slow) != canonical_analysis_context_bytes(other)
    assert corner_fingerprint(slow) != corner_fingerprint(other)
