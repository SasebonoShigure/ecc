"""Explicit post-CTS physical STA entry and current-generation routing handoff."""

import json
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path
from tempfile import TemporaryDirectory

from chipcompiler.data import EccStep, StepEnum, Workspace, WorkspaceStep
from chipcompiler.tools.ecc.module import ECCToolsModule
from chipcompiler.tools.ecc.physical_artifacts import read_physical_artifacts
from chipcompiler.tools.ecc.physical_greedy import run_physical_greedy
from chipcompiler.tools.ecc.sta_mode import request_from_mapping
from chipcompiler.tools.ecc.sta_session import IncrementalStaSession
from chipcompiler.tools.ecc.sta_snapshot import make_direct_sta_analysis_context


def is_physical_flow(workspace: Workspace) -> bool:
    steps = workspace.flow.data.get("steps", [])
    if not any(
        step["name"] == StepEnum.TIMING_OPT.value and step.get("tool") == "ecc" for step in steps
    ):
        return False
    names = [step["name"] for step in steps]
    if StepEnum.TIMING_OPT.value not in names:
        return False
    index = names.index(StepEnum.TIMING_OPT.value)
    required = [
        StepEnum.CTS.value,
        StepEnum.LEGALIZATION.value,
        StepEnum.TIMING_OPT.value,
        StepEnum.ROUTING.value,
    ]
    if index < 2 or names[index - 2 : index + 2] != required:
        raise ValueError("physical timing optimization requires CTS, legalization, then routing")
    return True


def bind_physical_routing_input(workspace: Workspace, step: WorkspaceStep) -> bool:
    """Resolve the manifest before a caller can load a previous binary DB."""
    if step.name != StepEnum.ROUTING.value or not is_physical_flow(workspace):
        return False
    if step.input.db is None:
        raise ValueError("physical routing handoff has no producing output directory")
    artifacts = read_physical_artifacts(Path(step.input.db).parent / "physical_session")
    step.input.def_ = artifacts.files["design.def"]
    step.input.verilog = artifacts.files["design.v"]
    # The caller skips binary DB loading; keep its path as the producing-directory identity.
    return True


def run_physical_timing_opt(
    workspace: Workspace,
    step: EccStep,
    module: ECCToolsModule,
) -> bool:
    if step.name != StepEnum.TIMING_OPT.value or not is_physical_flow(workspace):
        raise ValueError("physical timing optimization must be explicitly selected in the flow")
    if step.output.dir is None or step.data.dir is None:
        raise ValueError("physical timing optimization directories are missing")
    output = Path(step.output.dir)
    output.mkdir(parents=True, exist_ok=True)
    options = workspace.parameters.data.get("incregpusta", {})
    allowed = {"top_k", "max_rounds", "max_buffers", "horizontal_rc_layer", "vertical_rc_layer"}
    if type(options) is not dict or options.keys() - allowed:
        raise ValueError("invalid incregpusta experimental configuration")
    budgets = {
        key: options.get(key, default)
        for key, default in (
            ("top_k", 100),
            ("max_rounds", 10),
            ("max_buffers", 1000),
        )
    }
    if any(type(value) is not int or not 0 < value < 1 << 64 for value in budgets.values()):
        raise ValueError("greedy budgets must be positive uint64 integers")
    layers = {key: options.get(key, "") for key in ("horizontal_rc_layer", "vertical_rc_layer")}
    if any(type(value) is not str for value in layers.values()):
        raise ValueError("RC layer selections must be strings")
    layers = {key: "" if value == "auto" else value for key, value in layers.items()}
    routing = json.loads(workspace.config[StepEnum.ROUTING.value].read_text())["RT"]
    checkpoint = {
        "def": step.input.def_,
        "verilog": step.input.verilog,
        "sdc": workspace.pdk.sdc,
        "tech_lef": workspace.pdk.tech,
    }
    checkpoint.update({f"cell_lef_{index}": path for index, path in enumerate(workspace.pdk.lefs)})
    checkpoint.update({f"liberty_{index}": path for index, path in enumerate(workspace.pdk.libs)})
    if not workspace.pdk.libs or any(
        path is None or not Path(path).is_file() for path in checkpoint.values()
    ):
        raise ValueError("physical checkpoint inputs must be existing files")
    cells = sorted(
        {
            cell
            for cell in workspace.pdk.buffers
            if not any(fnmatchcase(cell, pattern) for pattern in workspace.pdk.dont_use)
        }
    )
    journal = output / "physical_session"
    policy = output / "greedy-config.json"
    policy_value = {"cells": cells, **budgets}
    if policy.exists():
        if json.loads(policy.read_text()) != policy_value:
            raise ValueError("physical greedy configuration differs from the saved run")
    else:
        with TemporaryDirectory(dir=output, prefix=".greedy-config-") as temporary:
            pending = Path(temporary) / policy.name
            pending.write_text(json.dumps(policy_value, sort_keys=True))
            try:
                policy.hardlink_to(pending)
            except FileExistsError as error:
                if json.loads(policy.read_text()) != policy_value:
                    raise ValueError(
                        "physical greedy configuration differs from the saved run"
                    ) from error
    checkpoint["greedy_config"] = policy
    recovering = (journal / "baseline.json").exists()
    if recovering and not module.read_def(str(step.input.def_)):
        raise RuntimeError("physical recovery rejected its baseline DEF")
    module.ecc.lib_init(lib_paths=[str(path) for path in workspace.pdk.libs])
    module.ecc.sdc_init(sdc_path=str(workspace.pdk.sdc))
    module.ecc.spef_init(spef_path="")
    context = replace(make_direct_sta_analysis_context(), rc_corner="pre_route")
    max_paths = workspace.parameters.data.get("STA max paths", 1000)
    if type(max_paths) is not int or max_paths <= 0:
        raise ValueError("STA max paths must be a positive integer")
    with IncrementalStaSession(
        module.ecc,
        request_from_mapping(workspace.parameters.data),
        context,
        config_dict={
            "-temp_directory_path": str(step.data.dir),
            "-output_timing_reports": "0",
            "-output_timing_features": "0",
            "-timing_path_limit": str(max_paths),
            "-max_paths": str(max_paths),
        },
    ) as session:
        baseline_arguments = {
            "bottom_layer": routing["-bottom_routing_layer"],
            "top_layer": routing["-top_routing_layer"],
            "horizontal_layer": layers["horizontal_rc_layer"],
            "vertical_layer": layers["vertical_rc_layer"],
            "recovery_directory": str(journal),
            "checkpoint_files": {key: str(path) for key, path in checkpoint.items()},
        }
        generation = 0
        if recovering:
            generation = session.recover_physical_baseline(**baseline_arguments).generation
        else:
            session.run_physical_baseline(**baseline_arguments)
        # Recovery validates each record while holding the journal owner lock.
        committed_buffers = sum(
            len(json.loads((journal / f"committed-{index}.json").read_text())["edits"])
            for index in range(1, generation + 1)
        )
        completion = output / "greedy-complete.json"
        if completion.exists():
            result = json.loads(completion.read_text())
            if (result["generation"], result["rounds"], result["buffers"]) != (
                generation,
                generation,
                committed_buffers,
            ):
                raise ValueError("greedy completion differs from committed history")
        else:
            result = run_physical_greedy(
                session,
                cells,
                output / "greedy.jsonl",
                committed_buffers=committed_buffers,
                **budgets,
            )
            pending = completion.with_suffix(".pending")
            pending.write_text(json.dumps(result, allow_nan=False) + "\n")
            pending.replace(completion)
        session.publish_physical_artifacts(expected_generation=result["generation"])
        if (
            step.output.geometry is None
            or step.output.geometry_manifest is None
            or not module.geometry_snapshot_save(output_dir=step.output.geometry)
            or not step.output.geometry_manifest.is_file()
        ):
            raise RuntimeError("physical geometry snapshot publication failed")
    artifacts = read_physical_artifacts(output / "physical_session")
    step.output.def_ = artifacts.files["design.def"]
    step.output.verilog = artifacts.files["design.v"]
    workspace.logger.info(
        "Physical STA generation=%s batches=%s buffers=%s stop=%s",
        result["generation"],
        result["rounds"],
        result["buffers"],
        result["stop_reason"],
    )
    return True
