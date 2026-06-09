#!/usr/bin/env python
import json
import os
import subprocess

from chipcompiler.data import StateEnum, Workspace, WorkspaceStep
from chipcompiler.tools.yosys.utility import get_yosys_runtime
from chipcompiler.tools.yosys_lec.subflow import YosysLecSubFlow


def _status_is_proven(path: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    with open(path, encoding="utf-8", errors="ignore") as handle:
        text = handle.read()
    return (
        "Equivalence successfully proven!" in text
        or "Found a total of 0 unproven $equiv cells." in text
    )


def _write_result(step: WorkspaceStep, proven: bool) -> None:
    payload = {
        "status": "proven" if proven else "incomplete",
        "equiv_status": step.report.get("equiv_status", ""),
        "status_report": step.report.get("status", ""),
    }
    with open(step.output["json"], "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def run_step(workspace: Workspace, step: WorkspaceStep, ecc_module=None) -> bool:
    sub_flow = YosysLecSubFlow(workspace=workspace, workspace_step=step)

    yosys_cmd, yosys_env = get_yosys_runtime()
    if not yosys_cmd:
        sub_flow.update_step(step_name="run lec", state=StateEnum.Invalid)
        with open(step.log["file"], "w", encoding="utf-8") as log_file:
            log_file.write("Error: yosys is not available.\n")
        return False

    for label, path in (
        ("golden netlist", step.input.get("golden_verilog", "")),
        ("gate netlist", step.input.get("gate_verilog", "")),
    ):
        if not path or not os.path.exists(path):
            sub_flow.update_step(step_name="run lec", state=StateEnum.Invalid)
            with open(step.log["file"], "w", encoding="utf-8") as log_file:
                log_file.write(f"Error: missing {label}: {path}\n")
            return False

    cmd = yosys_cmd + ["-Q", "-c", os.path.basename(step.script["main"])]
    with open(step.log["file"], "w", encoding="utf-8") as log_file:
        result = subprocess.run(
            cmd,
            cwd=step.script["dir"],
            env=yosys_env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

    proven = result.returncode == 0 and _status_is_proven(step.report.get("equiv_status", ""))
    if proven:
        _write_result(step, proven=True)
        sub_flow.update_step(step_name="run lec", state=StateEnum.Success)
        sub_flow.update_step(step_name="analysis", state=StateEnum.Success)
        return True

    sub_flow.update_step(step_name="run lec", state=StateEnum.Imcomplete)
    return False
