"""Pure immutable preflight models for direct and all-corner STA runs."""

import os
from dataclasses import dataclass
from pathlib import Path

from chipcompiler.data import EccStep, StepEnum, Workspace, WorkspaceStep, workspace_config_path
from chipcompiler.tools.ecc.sta_qor import (
    POST_SYNTHESIS_STA_CORNER,
    sta_artifact_directory,
    temperature_token,
)
from chipcompiler.tools.ecc.sta_snapshot import (
    StaAnalysisContext,
    make_direct_sta_analysis_context,
    normalize_sta_analysis_context,
    validate_sta_spef_rc_consistency,
)
from chipcompiler.utility import json_read_strict


@dataclass(frozen=True)
class StaSignoffRunItem:
    config: str
    work_dir: str
    report_dir: Path
    feature_dir: Path
    liberty_files: tuple[str, ...]
    sdc_path: str
    spef_path: str
    max_paths: int
    artifact_corner: str
    analysis_context: StaAnalysisContext


def _exact_nonempty_string(value: object, field: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{field} must be an exact str")
    if not value:
        raise ValueError(f"{field} must not be empty")
    if value != value.strip():
        raise ValueError(f"{field} must not have leading or trailing whitespace")
    return value


def _configured_path(value: object, field: str) -> Path:
    if isinstance(value, Path):
        return value
    if type(value) is str:
        if not value:
            raise ValueError(f"{field} is not configured")
        return Path(value)
    if value is None:
        raise ValueError(f"{field} is not configured")
    raise ValueError(f"{field} must be a filesystem path")


def _regular_file(value: object, field: str) -> str:
    path = _configured_path(value, field)
    if not path.is_file():
        raise FileNotFoundError(f"{field} is not a regular file: {path}")
    return os.fspath(path)


def _positive_max_paths(workspace: Workspace) -> int:
    value = workspace.parameters.data.get("STA max paths", 1000)
    if type(value) is not int or value <= 0:
        raise ValueError("STA max paths must be a positive nonbool integer")
    return value


def _sta_config_path(workspace: Workspace) -> str:
    if workspace.directory is None:
        raise ValueError("workspace directory is not configured")
    config_path = workspace_config_path(workspace.directory, StepEnum.STA.value)
    return _regular_file(config_path, "STA config")


def _resolved_destination(path: Path, field: str) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError as error:
        raise ValueError(f"{field} cannot be resolved: {path}") from error


def _require_distinct_destinations(report_dir: Path, feature_dir: Path) -> None:
    if _resolved_destination(report_dir, "STA report destination") == _resolved_destination(
        feature_dir, "STA feature destination"
    ):
        raise ValueError("STA report and feature destinations must not alias")


def _design_token(workspace: Workspace) -> str:
    return _exact_nonempty_string(
        workspace.design.top_module or workspace.design.name,
        "STA SPEF design name",
    )


def _liberty_items(
    data: dict[object, object],
) -> dict[str, tuple[str, tuple[str, ...]]]:
    liberty_outer = data.get("liberty")
    if type(liberty_outer) is not list or not liberty_outer:
        raise ValueError("STA liberty outer container must be a non-empty exact list")

    liberty_by_corner: dict[str, tuple[str, tuple[str, ...]]] = {}
    for index, raw_item in enumerate(liberty_outer):
        field = f"STA liberty[{index}]"
        if type(raw_item) is not dict:
            raise ValueError(f"{field} must be an exact dict")
        corner = _exact_nonempty_string(raw_item.get("corner"), f"{field}.corner")
        if corner in liberty_by_corner:
            raise ValueError(f"duplicate STA liberty corner: {corner}")

        raw_paths = raw_item.get("path")
        if type(raw_paths) is not list:
            raise ValueError(f"{field}.path must be an exact list")
        liberty_files = tuple(
            _regular_file(
                _exact_nonempty_string(path, f"{field}.path[{path_index}]"),
                f"{field}.path[{path_index}]",
            )
            for path_index, path in enumerate(raw_paths)
        )

        validation_context = normalize_sta_analysis_context(
            liberty_corner=corner,
            temperature=raw_item.get("temperature"),
            rc_corner=corner,
        )
        liberty_by_corner[corner] = (
            validation_context.temperature,
            liberty_files,
        )
    return liberty_by_corner


def preflight_sta_signoff_run(workspace: Workspace, step: EccStep) -> tuple[StaSignoffRunItem, ...]:
    config_path = _sta_config_path(workspace)
    data = json_read_strict(config_path)
    if type(data) is not dict:
        raise ValueError("STA config root must be an exact dict")
    liberty_by_corner = _liberty_items(data)
    signoff_outer = data.get("signoff")
    if type(signoff_outer) is not list or not signoff_outer:
        raise ValueError("STA signoff outer container must be a non-empty exact list")

    sdc_path = _regular_file(workspace.pdk.sdc, "STA SDC")
    work_dir = _configured_path(
        (step.data.steps or {}).get(StepEnum.STA.value),
        "STA work directory",
    )
    report_root = _configured_path(step.report.dir, "STA report root")
    feature_root = _configured_path(step.feature.dir, "STA feature root")
    max_paths = _positive_max_paths(workspace)
    if workspace.directory is None:
        raise ValueError("workspace directory is not configured")
    rcx_output_dir = workspace.directory / f"{StepEnum.RCX.value}_ecc" / "output"
    design_name = _design_token(workspace)
    raw_pairs: set[tuple[str, str]] = set()
    candidates: list[StaSignoffRunItem] = []

    for group_index, raw_group in enumerate(signoff_outer):
        group_field = f"STA signoff[{group_index}]"
        if type(raw_group) is not dict or not raw_group:
            raise ValueError(f"{group_field} must be a non-empty exact dict")

        for raw_corner, raw_rc_corners in raw_group.items():
            corner = _exact_nonempty_string(raw_corner, f"{group_field}.corner")
            liberty = liberty_by_corner.get(corner)
            if liberty is None:
                raise ValueError(f"STA signoff references unknown liberty corner: {corner}")
            if type(raw_rc_corners) is not list or not raw_rc_corners:
                raise ValueError(f"{group_field}.{corner} must be a non-empty exact RC list")

            temperature, liberty_files = liberty
            if not liberty_files:
                raise ValueError(f"referenced STA liberty corner {corner!r} must have files")
            for rc_index, raw_rc_corner in enumerate(raw_rc_corners):
                rc_corner = _exact_nonempty_string(
                    raw_rc_corner,
                    f"{group_field}.{corner}[{rc_index}]",
                )
                raw_pair = (corner, rc_corner)
                if raw_pair in raw_pairs:
                    raise ValueError(f"duplicate STA signoff pair: {raw_pair!r}")
                raw_pairs.add(raw_pair)

                context = normalize_sta_analysis_context(
                    liberty_corner=corner,
                    temperature=temperature,
                    rc_corner=rc_corner,
                )
                spef_path = os.fspath(
                    rcx_output_dir
                    / f"{design_name}_{rc_corner}_{temperature_token(temperature)}C.spef"
                )
                validate_sta_spef_rc_consistency(context, spef_path)
                spef_path = _regular_file(spef_path, f"STA SPEF for {corner}/{rc_corner}")
                report_dir = sta_artifact_directory(report_root, corner, temperature, rc_corner)
                feature_dir = sta_artifact_directory(feature_root, corner, temperature, rc_corner)
                if report_dir is None or feature_dir is None:
                    raise ValueError("STA report or feature destination is not configured")
                candidates.append(
                    StaSignoffRunItem(
                        config=config_path,
                        work_dir=os.fspath(work_dir),
                        report_dir=report_dir,
                        feature_dir=feature_dir,
                        liberty_files=liberty_files,
                        sdc_path=sdc_path,
                        spef_path=spef_path,
                        max_paths=max_paths,
                        artifact_corner=f"{report_dir.parent.name}/{report_dir.name}",
                        analysis_context=context,
                    )
                )

    artifact_corners = [item.artifact_corner for item in candidates]
    if len(set(artifact_corners)) != len(artifact_corners):
        raise ValueError("STA artifact corner names must be globally unique")

    resolved_destinations = [
        _resolved_destination(path, field)
        for item in candidates
        for path, field in (
            (item.report_dir, "STA report destination"),
            (item.feature_dir, "STA feature destination"),
        )
    ]
    if len(set(resolved_destinations)) != len(resolved_destinations):
        raise ValueError("STA report and feature destinations must be globally unique")
    return tuple(candidates)


def preflight_sta_direct_run(workspace: Workspace, step: WorkspaceStep) -> StaSignoffRunItem:
    context = make_direct_sta_analysis_context()
    validate_sta_spef_rc_consistency(context, "")

    config_path = _sta_config_path(workspace)
    _regular_file(step.output.verilog, "synthesis netlist")
    liberty_files = tuple(
        _regular_file(path, f"STA liberty[{index}]")
        for index, path in enumerate(workspace.pdk.libs)
    )
    if not liberty_files:
        raise ValueError("STA liberty list must not be empty")
    sdc_path = _regular_file(workspace.pdk.sdc, "STA SDC")
    data_root = _configured_path(step.data.dir, "synthesis STA data root")
    report_root = _configured_path(step.report.dir, "synthesis STA report root")
    feature_root = _configured_path(step.feature.dir, "synthesis STA feature root")
    report_dir = report_root / POST_SYNTHESIS_STA_CORNER
    feature_dir = feature_root / POST_SYNTHESIS_STA_CORNER
    _require_distinct_destinations(report_dir, feature_dir)

    return StaSignoffRunItem(
        config=config_path,
        work_dir=os.fspath(data_root / "sta"),
        report_dir=report_dir,
        feature_dir=feature_dir,
        liberty_files=liberty_files,
        sdc_path=sdc_path,
        spef_path="",
        max_paths=_positive_max_paths(workspace),
        artifact_corner=POST_SYNTHESIS_STA_CORNER,
        analysis_context=context,
    )
