"""Read one committed generation's immutable physical/timing artifact set."""

import fcntl
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class PhysicalArtifacts:
    generation: int
    directory: Path
    files: dict[str, Path]


def read_physical_artifacts(journal_directory: Path) -> PhysicalArtifacts:
    """Resolve current products after the producing session has closed."""
    journal = journal_directory.resolve(strict=True)
    with (journal / "owner.lock").open("rb") as owner:
        fcntl.flock(owner, fcntl.LOCK_SH | fcntl.LOCK_NB)
        baseline_id = hashlib.sha256((journal / "baseline.json").read_bytes()).hexdigest()
        records = list(journal.glob("committed-*"))
        generation = len(records)
        expected = {f"committed-{index}.json" for index in range(1, generation + 1)}
        if {path.name for path in records} != expected or any(
            not path.is_file() or path.is_symlink() for path in records
        ):
            raise ValueError("physical journal generations are not contiguous")
        if generation:
            record = json.loads((journal / f"committed-{generation}.json").read_text())
            if (
                record["baseline_id"] != baseline_id
                or type(record["generation"]) is not int
                or record["generation"] != generation
            ):
                raise ValueError("physical journal identity differs")
        root = journal / "artifacts"
        pointer = root / "manifest.json"
        if root.is_symlink() or pointer.is_symlink():
            raise ValueError("physical artifact manifest must not be a symlink")
        manifest = json.loads(pointer.read_text())
        if (
            manifest["schema_version"] != "physical-sta-artifacts/1.0.0"
            or type(manifest["generation"]) is not int
            or manifest["generation"] != generation
            or manifest["baseline_id"] != baseline_id
        ):
            raise ValueError("physical artifact manifest is stale")
        name = manifest["directory"]
        if not isinstance(name, str) or PurePosixPath(name).parts != (name,):
            raise ValueError("invalid physical artifact directory")
        directory = root / name
        if directory.resolve(strict=True) != directory:
            raise ValueError("physical artifact directory escapes its owner")
        files = {}
        for name, identity in manifest["files"].items():
            path = directory / name
            if (
                not isinstance(name, str)
                or not name
                or PurePosixPath(name).is_absolute()
                or ".." in PurePosixPath(name).parts
                or path.resolve(strict=True) != path
                or not path.is_file()
            ):
                raise ValueError("invalid physical artifact file")
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if (
                type(identity["size"]) is not int
                or identity["size"] != path.stat().st_size
                or identity["sha256"] != digest
            ):
                raise ValueError(f"physical artifact identity differs: {name}")
            files[name] = path
        required = {
            "design.def",
            "design.v",
            "design.sdf",
            "timing/qor_summary.json",
            "timing/timing_paths.json",
            "power/power.rpt",
            "power/instance_power.bin",
        }
        if not required <= files.keys():
            raise ValueError("physical artifact set is incomplete")
        return PhysicalArtifacts(generation, directory, files)
