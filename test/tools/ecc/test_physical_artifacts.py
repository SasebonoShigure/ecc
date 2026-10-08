import fcntl
import hashlib
import json

import pytest

from chipcompiler.tools.ecc.physical_artifacts import read_physical_artifacts


def test_current_artifacts_reject_stale_partial_and_active_owner(tmp_path):
    journal = tmp_path / "journal"
    journal.mkdir()
    (journal / "owner.lock").touch()
    (journal / "baseline.json").write_text("{}")
    baseline_id = hashlib.sha256(b"{}").hexdigest()
    record = {"baseline_id": baseline_id, "generation": 1}
    (journal / "committed-1.json").write_text(json.dumps(record))
    root = journal / "artifacts"
    directory = root / "generation-1-fixture"
    directory.mkdir(parents=True)
    files = {}
    for name in (
        "design.def",
        "design.v",
        "design.sdf",
        "timing/qor_summary.json",
        "timing/timing_paths.json",
        "power/power.rpt",
        "power/instance_power.bin",
    ):
        path = directory / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(name.encode())
        files[name] = {"size": len(name), "sha256": hashlib.sha256(name.encode()).hexdigest()}
    manifest = {
        "schema_version": "physical-sta-artifacts/1.0.0",
        "generation": 1,
        "baseline_id": baseline_id,
        "directory": directory.name,
        "report_request": {},
        "files": files,
    }
    pointer = root / "manifest.json"
    pointer.write_text(json.dumps(manifest))
    actual = read_physical_artifacts(journal)
    assert actual.generation == 1
    assert actual.files == {name: directory / name for name in files}
    with (journal / "owner.lock").open("rb") as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            read_physical_artifacts(journal)
    target = directory / "design.v"
    target.write_bytes(b"partial")
    with pytest.raises(ValueError, match="identity"):
        read_physical_artifacts(journal)
    target.write_bytes(b"design.v")
    (journal / "committed-2.json").write_text(json.dumps(dict(record, generation=2)))
    with pytest.raises(ValueError, match="stale"):
        read_physical_artifacts(journal)
    manifest["generation"] = 2
    manifest["directory"] = "../escape"
    pointer.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="directory"):
        read_physical_artifacts(journal)
