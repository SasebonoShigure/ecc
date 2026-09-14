"""Exercise a selected real native build through the public Python timing wrapper.

Select its isolated ecc_tools_bin package with PYTHONPATH. This is a development
acceptance entry, separate from normal pytest and performance sampling.
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from chipcompiler.tools.ecc.module import ECCToolsModule
from chipcompiler.tools.ecc.sta_mode import (
    StaBackend,
    StaCapabilityReason,
    StaExecutionRequest,
    StaFallbackPolicy,
    StaSessionStatusCode,
    StaUnsupportedError,
    StaUpdateStrategy,
)
from chipcompiler.tools.ecc.sta_session import preflight_sta_request
from chipcompiler.tools.ecc.sta_snapshot import StaSnapshotState


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=[item.value for item in StaBackend], required=True)
    parser.add_argument("--case", choices=("chain", "diamond"), default="chain")
    parser.add_argument(
        "--strategy", choices=[item.value for item in StaUpdateStrategy], default="full"
    )
    parser.add_argument("--output-root", type=Path, required=True)
    expectation = parser.add_mutually_exclusive_group()
    expectation.add_argument("--expect-unavailable", action="store_true")
    expectation.add_argument("--expect-unsupported-analysis", action="store_true")
    args = parser.parse_args()

    module = ECCToolsModule()
    native = module.ecc
    build = {}
    for name in ("incregpusta_cuda_enabled", "incregpusta_debug_checks_enabled"):
        value = getattr(native, name)
        if type(value) is not bool:
            raise RuntimeError(f"native {name} is not a bool")
        try:
            setattr(native, name, not value)
        except AttributeError:
            pass
        else:
            raise RuntimeError(f"native {name} must be read-only")
        build[name] = value
    build["module_path"] = native.__file__
    request = StaExecutionRequest(
        StaBackend(args.backend), StaUpdateStrategy(args.strategy), StaFallbackPolicy.ERROR
    )
    if args.expect_unavailable:
        try:
            preflight_sta_request(request)
        except StaUnsupportedError as error:
            if (
                error.request != request
                or error.status_code is not StaSessionStatusCode.UNSUPPORTED
                or error.capability_reason is not StaCapabilityReason.BACKEND_UNAVAILABLE
                or error.state != "created"
            ):
                raise RuntimeError("unexpected native unavailable outcome") from error
            print(json.dumps({"build": build, "unavailable": str(error)}, sort_keys=True))
            return
        raise RuntimeError("unavailable-device request unexpectedly passed preflight")

    expected = preflight_sta_request(request)
    if expected.executed_backend is not request.backend or expected.fallback_to_full:
        raise RuntimeError("native preflight silently changed the requested backend")
    fixtures = (
        Path(__file__).resolve().parents[3]
        / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/test/baseline/fixtures"
    )
    args.output_root.mkdir(parents=True, exist_ok=False)
    module.init_techlef(str(fixtures / "stage0_tech.lef"))
    module.init_lefs([fixtures / "stage0_cells.lef"])
    module.read_verilog(fixtures / f"{args.case}.v", f"stage0_{args.case}")
    runs = []
    analysis_rejection = None
    try:
        if args.expect_unsupported_analysis:
            sdc = args.output_root / "case-analysis.sdc"
            sdc.write_text(
                (fixtures / f"{args.case}.sdc").read_text()
                + "\nset_case_analysis 0 [get_ports data_in]\n"
            )
            rejected_root = args.output_root / "unsupported"
            try:
                module.run_timing(
                    work_dir=rejected_root / "work",
                    report_dir=rejected_root / "report",
                    feature_dir=rejected_root / "feature",
                    lib_paths=[fixtures / "stage0.lib"],
                    sdc_path=str(sdc),
                    execution_request=request,
                )
            except StaUnsupportedError as error:
                if (
                    error.request != request
                    or error.capability_reason
                    is not StaCapabilityReason.UNSUPPORTED_ANALYSIS_FEATURES
                    or error.state != "poisoned"
                ):
                    raise RuntimeError("unexpected unsupported-analysis outcome") from error
                analysis_rejection = str(error)
            else:
                raise RuntimeError("unsupported case analysis unexpectedly completed")
            if (rejected_root / "feature/qor_summary.json").exists():
                raise RuntimeError("unsupported analysis published successful timing artifacts")
        for index in range(2):
            root = args.output_root / f"run-{index}"
            observations = []
            record = module.run_timing(
                work_dir=root / "work",
                report_dir=root / "report",
                feature_dir=root / "feature",
                lib_paths=[fixtures / "stage0.lib"],
                sdc_path=str(fixtures / f"{args.case}.sdc"),
                output_modes=("report", "structured"),
                execution_request=request,
                snapshot_observation_sink=lambda _context,
                observation,
                sink=observations: sink.append(observation),
            )
            [observation] = observations
            expect_snapshot = (
                native.incregpusta_debug_checks_enabled
                and request.backend is StaBackend.CPU
                and request.update_strategy is StaUpdateStrategy.INCREMENTAL
            )
            if expect_snapshot:
                if observation is None or observation.state is not StaSnapshotState.RELEASED:
                    raise RuntimeError("CPU incremental snapshot was not released")
            elif observation is not None:
                raise RuntimeError("unexpected diagnostic snapshot")
            if record != expected:
                raise RuntimeError("real native run differs from preflight")
            qor = json.loads((root / "feature/qor_summary.json").read_text())
            paths = json.loads((root / "feature/timing_paths.json").read_text())
            if not qor or not paths:
                raise RuntimeError("real native timing artifacts are empty")
            for name in ("qor_summary.rpt", "power.rpt", f"stage0_{args.case}.sdf"):
                if not (root / "report" / name).stat().st_size:
                    raise RuntimeError(f"missing native artifact: {name}")
            runs.append(
                {
                    "record": asdict(record),
                    "qor": qor,
                    "paths": paths,
                    "snapshot": asdict(observation) if observation is not None else None,
                }
            )
    finally:
        module.close()
    result = {
        "build": build,
        "case": args.case,
        "runs": runs,
        "analysis_rejection": analysis_rejection,
    }
    (args.output_root / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"build": build, "case": args.case, "runs_completed": len(runs)}))


if __name__ == "__main__":
    main()
