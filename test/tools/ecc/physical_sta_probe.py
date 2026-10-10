#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import traceback
from dataclasses import replace
from fnmatch import fnmatchcase
from pathlib import Path
from time import perf_counter

from physical_sta_performance import run_sample

from chipcompiler.data.workspace import load_workspace
from chipcompiler.tools.ecc.module import ECCToolsModule
from chipcompiler.tools.ecc.physical_placement import PhysicalBufferLegalizer
from chipcompiler.tools.ecc.sta_snapshot import (
    make_direct_sta_analysis_context,
    sta_analysis_context_to_native_mapping,
)


def input_identity(path):
    with Path(path).open("rb") as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        after = os.fstat(stream.fileno())
        if stream.tell() != before.st_size or (before.st_size, before.st_mtime_ns) != (
            after.st_size,
            after.st_mtime_ns,
        ):
            raise RuntimeError(f"input changed while hashing: {path}")
    return {"path": str(path), "size_bytes": before.st_size, "sha256": digest}


def main():
    started = perf_counter()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace", type=Path, required=True, help="Existing post-CTS legalized workspace"
    )
    parser.add_argument(
        "--binding-dir",
        type=Path,
        required=True,
        help="Directory containing the isolated ecc_py module",
    )
    parser.add_argument("--def-file", type=Path, required=True)
    parser.add_argument("--verilog-file", type=Path, required=True)
    parser.add_argument("--sdc", type=Path, required=True)
    parser.add_argument("--mode", choices=("OFF", "ON"), required=True)
    parser.add_argument("--backend", choices=("cpu", "cuda"), required=True)
    parser.add_argument("--strategy", choices=("full", "incremental"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=128)
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="OFF fixed trace: candidate reads per round, one final report/artifact publication",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-from", type=Path)
    group.add_argument("--physical-trace", type=Path)
    group.add_argument(
        "--closed-loop", action="store_true", help="Run the production physical greedy flow"
    )
    group.add_argument(
        "--fresh",
        action="store_true",
        help="Independent native CPU/full of the supplied DEF/netlist",
    )
    args = parser.parse_args()
    if args.threads <= 0:
        parser.error("--threads must be positive")
    if args.fresh and ((args.mode, args.backend, args.strategy) != ("ON", "cpu", "full")):
        parser.error("--fresh requires ON cpu/full and explicit --def-file/--verilog-file")
    if args.benchmark and (args.mode != "OFF" or args.physical_trace is None):
        parser.error("--benchmark requires OFF and --physical-trace")
    module = ECCToolsModule()
    loaded = Path(module.ecc.__file__).resolve()
    if args.benchmark and module.ecc.incregpusta_debug_checks_enabled:
        raise RuntimeError("physical performance requires debug checks OFF")
    if (
        loaded.parent != args.binding_dir.resolve()
        or module.ecc.incregpusta_debug_checks_enabled != (args.mode == "ON")
    ):
        raise RuntimeError("binding mode mismatch")
    binding_identity = input_identity(loaded) if args.benchmark else None
    workspace_dir = args.workspace.resolve()
    workspace = load_workspace(workspace_dir)
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    def_file = args.def_file.resolve()
    verilog = args.verilog_file.resolve()
    sdc = args.sdc.resolve()
    routing = json.loads(Path(workspace.config["route"]).read_text())["RT"]
    checkpoint = {
        "def": str(def_file),
        "verilog": str(verilog),
        "sdc": str(sdc),
        "tech_lef": str(workspace.pdk.tech),
    }
    checkpoint.update({f"cell_lef_{i}": str(p) for i, p in enumerate(workspace.pdk.lefs)})
    checkpoint.update({f"liberty_{i}": str(p) for i, p in enumerate(workspace.pdk.libs)})
    if any(not Path(path).is_file() for path in checkpoint.values()):
        raise ValueError("physical checkpoint input is missing")
    input_identities = {name: input_identity(path) for name, path in checkpoint.items()}
    module.init_config(str(workspace.config["flow"]), str(workspace.config["db"]), out, out)
    module.init_techlef(str(workspace.pdk.tech))
    module.init_lefs(workspace.pdk.lefs)
    if not module.read_def(str(def_file)):
        raise RuntimeError("post-CTS DEF loader rejected input")
    module.ecc.lib_init(lib_paths=[str(x) for x in workspace.pdk.libs])
    module.ecc.sdc_init(sdc_path=str(sdc))
    module.ecc.spef_init(spef_path="")
    print(
        json.dumps(
            {
                "binding": str(loaded),
                "debug_checks": module.ecc.incregpusta_debug_checks_enabled,
                "cuda_enabled": module.ecc.incregpusta_cuda_enabled,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    (out / "build.json").write_text(
        json.dumps(
            {
                "binding": str(loaded),
                "debug_checks": module.ecc.incregpusta_debug_checks_enabled,
                "cuda_enabled": module.ecc.incregpusta_cuda_enabled,
                "inputs": input_identities,
            }
        )
        + "\n"
    )
    request = {
        "backend": args.backend,
        "update_strategy": args.strategy,
        "fallback_policy": "error",
    }
    print(json.dumps({"requested": request}), flush=True)
    if args.closed_loop:
        from chipcompiler.data import StepEnum
        from chipcompiler.rtl2gds import get_flow_builders
        from chipcompiler.tools.ecc.builder import build_step, build_step_space
        from chipcompiler.tools.ecc.physical_runner import run_physical_timing_opt

        workspace.flow.data["steps"] = [
            {"name": step.value, "tool": tool}
            for step, tool, _ in get_flow_builders()["incregpusta_experimental"]()
        ]
        workspace.parameters.data.update(
            {
                "STA backend": args.backend,
                "STA update strategy": args.strategy,
                "STA fallback policy": "error",
            }
        )
        workspace.parameters.data["STA max paths"] = 20
        workspace.pdk.sdc = sdc
        step = build_step(
            workspace,
            StepEnum.TIMING_OPT.value,
            def_file,
            verilog,
            step_directory=out / "timing_opt",
        )
        build_step_space(step)
        try:
            if not run_physical_timing_opt(workspace, step, module):
                raise RuntimeError("physical production flow did not complete")
        finally:
            module.close()
        return
    loaded_at = perf_counter()
    measurement = None
    session = module.ecc.create_incremental_sta_session(request)
    try:
        session.initialize(
            analysis_context=sta_analysis_context_to_native_mapping(
                replace(make_direct_sta_analysis_context(), rc_corner="pre_route")
            ),
            config="",
            config_dict={
                "-temp_directory_path": str(out),
                "-thread_number": str(args.threads),
                "-output_timing_reports": "0",
                "-output_timing_features": "0",
                "-timing_path_limit": "20",
                "-max_paths": "20",
                "-nworst": "20" if args.benchmark else "1",
            },
        )
        baseline = session.run_physical_baseline(
            bottom_layer=routing["-bottom_routing_layer"],
            top_layer=routing["-top_routing_layer"],
            horizontal_layer="",
            vertical_layer="",
            recovery_directory=str(out / "journal"),
            checkpoint_files=checkpoint,
        )
        if args.benchmark:
            baseline_done = perf_counter()
            cells = sorted(
                {
                    cell
                    for cell in workspace.pdk.buffers
                    if not any(fnmatchcase(cell, pattern) for pattern in workspace.pdk.dont_use)
                }
            )
            trace_bytes = args.physical_trace.read_bytes()
            trace_identity = {
                "path": str(args.physical_trace),
                "size_bytes": len(trace_bytes),
                "sha256": hashlib.sha256(trace_bytes).hexdigest(),
            }
            measurement = run_sample(
                session,
                json.loads(trace_bytes),
                cells,
                request,
                json.loads((out / "journal/baseline.json").read_text())["build"],
            )
            measurement.update(
                trace=trace_identity,
                binding=binding_identity,
                threads_requested=args.threads,
                cpu_affinity=sorted(os.sched_getaffinity(0)),
                thread_activity="external_profile",
                inputs=input_identities,
                load_ms=(loaded_at - started) * 1000,
                initialize_baseline_ms=(baseline_done - loaded_at) * 1000,
            )
            return
        current = session.read_physical_result()
        (out / "baseline.json").write_text(
            json.dumps({"execution": baseline, "current": current}) + "\n"
        )
        if args.fresh:
            session.publish_physical_artifacts(expected_generation=current["generation"])
            (out / "diagnostic.json").write_text(
                module.ecc.read_physical_diagnostic(session) + "\n"
            )
            (out / "result.json").write_text(
                json.dumps({"baseline": baseline, "current": current}) + "\n"
            )
            return
        geometry = None
        legalizer = None
        if args.prepare_from:
            if (args.backend, args.strategy) != ("cpu", "full"):
                raise RuntimeError("freeze physical positions with native CPU/full only")
            source = json.loads(args.prepare_from.read_text())
            batches = source["workload"]["batches"]
            if not isinstance(batches, list) or not batches or any(not b["edits"] for b in batches):
                raise ValueError("physical acceptance requires nonempty batches and edits")
            cell_names = sorted(
                {e["library_cell"]["cell_name"] for b in batches for e in b["edits"]}
            )
            geometry = session.read_physical_placement(expected_generation=0, cell_names=cell_names)
            (out / "geometry.json").write_text(json.dumps(geometry) + "\n")
            legalizer = PhysicalBufferLegalizer(
                geometry,
                batch_capacity=max(len(b["edits"]) for b in batches),
                total_capacity=sum(len(b["edits"]) for b in batches),
            )
            frozen: dict = {
                "schema_version": "physical-sta-trace/1.0.0",
                "source": str(args.prepare_from),
                "source_sha256": input_identity(args.prepare_from)["sha256"],
                "batches": [],
            }
        else:
            frozen = json.loads(args.physical_trace.read_text())
            if frozen["schema_version"] != "physical-sta-trace/1.0.0":
                raise RuntimeError("invalid physical trace")
            batches = frozen["batches"]
            if not isinstance(batches, list) or not batches or any(not b["edits"] for b in batches):
                raise ValueError("physical acceptance requires nonempty batches and edits")
        if args.mode == "OFF" and hasattr(module.ecc, "read_physical_diagnostic"):
            raise RuntimeError("OFF binding contains full diagnostic entry")
        for index, batch in enumerate(batches):
            if batch["expected_generation"] != index:
                raise RuntimeError("noncontiguous frozen trace")
            if args.prepare_from:
                assert geometry is not None and legalizer is not None
                bounds = geometry["bounds"]
                targets = [((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)] * len(
                    batch["edits"]
                )
                locations = legalizer.prepare(
                    [e["library_cell"]["cell_name"] for e in batch["edits"]], targets
                )
                edits = []
                for source_edit, location in zip(batch["edits"], locations, strict=True):
                    edit = dict(source_edit)
                    edit["placement_inputs"] = {
                        "kind": "placed",
                        "x_microns": location.x_dbu / legalizer.dbu_per_um,
                        "y_microns": location.y_dbu / legalizer.dbu_per_um,
                    }
                    edit["rc_inputs"] = {"kind": "parasitic", "policy": "pre_route_tree"}
                    edits.append(
                        {
                            "edit": edit,
                            "physical": {
                                "x_dbu": location.x_dbu,
                                "y_dbu": location.y_dbu,
                                "orientation": location.orientation,
                            },
                        }
                    )
                request_batch = {
                    "schema_version": "physical-sta-batch/1.0.0",
                    "expected_generation": index,
                    "edits": edits,
                }
            else:
                request_batch = batch
            (out / f"request-{index + 1}.json").write_text(
                json.dumps(request_batch, allow_nan=False) + "\n"
            )
            applied = session.apply_physical_batch(
                batch_json=json.dumps(request_batch, allow_nan=False)
            )
            if applied["generation"] != index + 1 or applied["execution"]["fallback_to_full"]:
                raise RuntimeError("physical trace did not commit the requested generation/mode")
            if (
                applied["execution"]["executed_backend"] != args.backend
                or applied["execution"]["executed_update_strategy"] != args.strategy
            ):
                raise RuntimeError("physical batch ran a different backend/strategy")
            if (
                args.strategy == "incremental"
                and not applied["execution"]["incremental_batch_executed"]
            ):
                raise RuntimeError("baseline/full result counted as incremental")
            if args.prepare_from:
                assert legalizer is not None
                legalizer.committed(applied["generation"])
                frozen["batches"].append(request_batch)
            current = session.read_physical_result()
            if current["generation"] != applied["generation"]:
                raise RuntimeError("physical query returned a stale generation")
            if current != session.read_physical_result():
                raise RuntimeError("repeated physical query changed current results")
            (out / f"result-{index + 1}.json").write_text(
                json.dumps({"execution": applied, "current": current}) + "\n"
            )
            if args.mode == "ON":
                (out / f"diagnostic-{index + 1}.json").write_text(
                    module.ecc.read_physical_diagnostic(session) + "\n"
                )
            module.def_save(out / f"generation-{index + 1}.def")
            module.verilog_save(out / f"generation-{index + 1}.v")
            print(
                json.dumps(
                    {"generation": current["generation"], "execution": applied["execution"]}
                ),
                flush=True,
            )
        session.publish_physical_artifacts(expected_generation=len(batches))
        if args.prepare_from:
            (out / "physical-trace.json").write_text(json.dumps(frozen, sort_keys=True) + "\n")

    except Exception as error:
        failure: dict[str, object] = {"type": type(error).__name__, "message": str(error)}
        for field in ("status_code", "capability_reason", "state", "request"):
            failure[field] = getattr(error, field, None)
        (out / "failure.json").write_text(json.dumps(failure, sort_keys=True) + chr(10))
        print(json.dumps({"failure": failure}), flush=True)
        raise
    finally:
        failed = sys.exc_info()[0] is not None
        cleanup_started = perf_counter()
        try:
            session.close()
            if args.benchmark:
                module.close()
        except Exception:
            if not failed:
                raise
            traceback.print_exc()
        else:
            if measurement is not None:
                completed = perf_counter()
                if (
                    input_identity(loaded) != binding_identity
                    or input_identity(args.physical_trace) != measurement["trace"]
                    or any(
                        input_identity(source["path"]) != source
                        for source in measurement["inputs"].values()
                    )
                ):
                    raise RuntimeError("physical performance input or binding changed")
                verified = perf_counter()
                measurement.update(
                    evidence_verification_ms=(verified - completed) * 1000,
                    cleanup_ms=(completed - cleanup_started) * 1000,
                    session_end_to_end_ms=(completed - started) * 1000,
                    lifecycle_cleanup_completed=True,
                )
                (out / "sample.json").write_text(json.dumps(measurement, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
