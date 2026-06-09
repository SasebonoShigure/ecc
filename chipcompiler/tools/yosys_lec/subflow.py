#!/usr/bin/env python
import os
import time

from chipcompiler.data import StateEnum, Workspace, WorkspaceStep


class YosysLecSubFlow:
    def __init__(self, workspace: Workspace, workspace_step: WorkspaceStep):
        self.workspace = workspace
        self.workspace_step = workspace_step
        self.init_sub_flow()
        self.start_time = time.time()
        self.start_memory = self.get_peak_memory()

    def init_sub_flow(self):
        from chipcompiler.utility import json_read

        data = json_read(self.workspace_step.subflow.get("path", ""))
        if len(data) > 0:
            self.workspace_step.subflow["steps"] = data.get("steps", [])
        else:
            self.build_sub_flow()

    def build_sub_flow(self) -> list:
        def subflow_template(step_name: str):
            return {
                "name": step_name,
                "state": StateEnum.Unstart.value,
                "runtime": "",
                "peak memory (mb)": 0,
                "info": {},
            }

        self.workspace_step.subflow["steps"] = [
            subflow_template("run lec"),
            subflow_template("analysis"),
        ]
        self.save()
        return self.workspace_step.subflow["steps"]

    def save(self) -> bool:
        from chipcompiler.utility import json_write

        return json_write(
            file_path=self.workspace_step.subflow.get("path", ""),
            data=self.workspace_step.subflow,
        )

    def get_runtime(self):
        end_time = time.time()
        elapsed_time = end_time - self.start_time
        runtime = "{}:{}:{}".format(
            int(elapsed_time // 3600),
            int((elapsed_time % 3600) // 60),
            int(elapsed_time % 60),
        )
        self.start_time = end_time
        return runtime

    def get_peak_memory(self):
        peak_memory = 0
        try:
            with open(f"/proc/{os.getpid()}/status") as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        peak_memory = int(line.split()[1]) / 1024
                        break
        except Exception:
            pass
        return peak_memory

    def update_step(self, step_name: str, state: str | StateEnum, info: dict | None = None):
        state = state.value if isinstance(state, StateEnum) else state
        runtime = self.get_runtime()
        peak_memory = self.get_peak_memory() - self.start_memory
        peak_memory = 0 if peak_memory < 0 else round(peak_memory, 3)
        info = info or {}

        for step_dict in self.workspace_step.subflow.get("steps", []):
            if step_dict.get("name") == step_name:
                step_dict["state"] = state
                step_dict["runtime"] = runtime
                step_dict["peak memory (mb)"] = peak_memory
                step_dict["info"] = info
                self.save()
                self.workspace.home.update_monitor(
                    step=self.workspace_step.name,
                    sub_step=step_name,
                    memory=str(peak_memory),
                    runtime=runtime,
                )
                break
