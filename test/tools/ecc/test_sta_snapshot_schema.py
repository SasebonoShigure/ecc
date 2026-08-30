import json
import re
from dataclasses import fields
from pathlib import Path

from chipcompiler.tools.ecc import sta_snapshot as snapshot

REPO_ROOT = Path(__file__).parents[3]
SCHEMA_PATH = (
    REPO_ROOT / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema/"
    "csr_snapshot_observation_v1.schema.json"
)
CPP_OBSERVATION_HEADER = (
    REPO_ROOT / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/source/module/"
    "timing_csr_snapshot/CsrSnapshotObservation.hpp"
)

# Each pair is explicit even when both spellings match.  JSON names are never
# inferred from dataclass fields.
SCHEMA_PARENT_FIELD_MAP = (
    (
        "identitySyntax",
        snapshot.StaSnapshotIdentity,
        (
            ("fingerprint_schema_version", "fingerprint_schema_version"),
            ("session_token", "session_token"),
            ("graph_generation", "graph_generation"),
            ("topology_fingerprint", "topology_fingerprint"),
            ("clock_constraint_fingerprint", "clock_constraint_fingerprint"),
            ("library_fingerprint", "library_fingerprint"),
            ("corner_fingerprint", "corner_fingerprint"),
            ("parasitic_fingerprint", "parasitic_fingerprint"),
            ("timing_input_fingerprint", "timing_input_fingerprint"),
        ),
    ),
    (
        "counts",
        snapshot.StaSnapshotCounts,
        (("nodes", "nodes"), ("arcs", "arcs"), ("levels", "levels")),
    ),
    (
        "extent",
        snapshot.StaBufferExtent,
        (("logical_size", "logical_size"), ("capacity", "capacity")),
    ),
    (
        "buffers",
        snapshot.StaSnapshotBuffers,
        (
            ("node_keys", "node_keys"),
            ("arc_keys", "arc_keys"),
            ("out_row_offsets", "out_row_offsets"),
            ("out_arc_ids", "out_arc_ids"),
            ("in_row_offsets", "in_row_offsets"),
            ("in_arc_ids", "in_arc_ids"),
            ("level_offsets", "level_offsets"),
            ("level_nodes", "level_nodes"),
            ("node_to_level", "node_to_level"),
        ),
    ),
    (
        "capacity",
        snapshot.StaCapacityObservation,
        (("last_action", "last_action"), ("event_count", "event_count")),
    ),
    (
        "support",
        snapshot.StaSupportObservation,
        (
            ("reference_supported", "reference_supported"),
            ("unsupported_reasons", "unsupported_reasons"),
        ),
    ),
    (
        "timing",
        snapshot.StaTimingObservation,
        (("export", "export"), ("reference", "reference"), ("scatter", "scatter")),
    ),
    (
        "hostBytes",
        snapshot.StaModeledHostBytes,
        (("logical", "logical"), ("capacity", "capacity")),
    ),
    (
        "currentFingerprints",
        snapshot.StaCurrentFingerprints,
        (
            ("topology_fingerprint", "topology_fingerprint"),
            ("clock_constraint_fingerprint", "clock_constraint_fingerprint"),
            ("library_fingerprint", "library_fingerprint"),
            ("corner_fingerprint", "corner_fingerprint"),
            ("parasitic_fingerprint", "parasitic_fingerprint"),
            ("timing_input_fingerprint", "timing_input_fingerprint"),
        ),
    ),
    (
        "rejection",
        snapshot.StaScatterRejectionEvent,
        (
            ("reason", "reason"),
            ("writes_applied", "writes_applied"),
            ("source", "source"),
            ("current", "current"),
        ),
    ),
    (
        "invalidation",
        snapshot.StaInvalidationEvent,
        (
            ("reason", "reason"),
            ("writes_applied", "writes_applied"),
            ("previous_identity", "previous_identity"),
            ("current_fingerprints", "current_fingerprints"),
        ),
    ),
    (
        "observation",
        snapshot.StaSnapshotObservation,
        (
            ("schema_version", "schema_version"),
            ("state", "state"),
            ("identity", "identity"),
            ("counts", "counts"),
            ("buffers", "buffers"),
            ("capacity", "capacity"),
            ("support", "support"),
            ("timing_ms", "timing_ms"),
            ("host_bytes", "host_bytes"),
            ("last_rejection", "last_rejection"),
            ("last_invalidation", "last_invalidation"),
        ),
    ),
)

CPP_TIMING_TO_JSON_FIELDS = (
    ("export_ms", "export"),
    ("reference_ms", "reference"),
    ("scatter_ms", "scatter"),
)
CPP_TIMING_FIELD_DECLARATIONS = (
    "double export_ms{0.0};",
    "std::optional<double> reference_ms;",
    "std::optional<double> scatter_ms;",
)


def _schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_objects_and_parent_dataclasses_match_explicit_field_inventory():
    definitions = _schema()["$defs"]
    object_definitions = tuple(
        name
        for name, definition in definitions.items()
        if isinstance(definition, dict) and "properties" in definition
    )
    assert object_definitions == tuple(name for name, _, _ in SCHEMA_PARENT_FIELD_MAP)

    for schema_name, parent_type, field_map in SCHEMA_PARENT_FIELD_MAP:
        definition = definitions[schema_name]
        expected_json = tuple(json_name for json_name, _ in field_map)
        expected_parent = tuple(parent_name for _, parent_name in field_map)
        assert definition["type"] == "object"
        assert definition["additionalProperties"] is False
        assert tuple(definition["required"]) == expected_json
        assert tuple(definition["properties"]) == expected_json
        assert tuple(field.name for field in fields(parent_type)) == expected_parent


def test_cpp_timing_fields_use_explicit_json_mapping_inventory():
    header = CPP_OBSERVATION_HEADER.read_text(encoding="utf-8")
    match = re.search(
        r"struct CsrTimingObservation\s*\{(?P<body>.*?)\n\};",
        header,
        flags=re.DOTALL,
    )
    assert match is not None
    declarations = tuple(
        line.strip()
        for line in match.group("body").splitlines()
        if line.strip() and not line.strip().startswith("friend bool operator==")
    )
    assert declarations == CPP_TIMING_FIELD_DECLARATIONS
    assert tuple(cpp_name for cpp_name, _ in CPP_TIMING_TO_JSON_FIELDS) == (
        "export_ms",
        "reference_ms",
        "scatter_ms",
    )

    timing_map = next(
        field_map
        for schema_name, _, field_map in SCHEMA_PARENT_FIELD_MAP
        if schema_name == "timing"
    )
    mapped_json = tuple(json_name for _, json_name in CPP_TIMING_TO_JSON_FIELDS)
    assert mapped_json == tuple(json_name for json_name, _ in timing_map)
    assert mapped_json == tuple(parent_name for _, parent_name in timing_map)
