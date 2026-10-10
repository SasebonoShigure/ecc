#!/usr/bin/env python3
"""Interleave four fresh-process physical traces, including final artifacts."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

REPOSITORY = Path(__file__).resolve().parents[3]
SCHEMA = REPOSITORY / "chipcompiler/thirdparty/ecc-tools/src/operation/iSTA/benchmark/schema"


def main():
    sys.path.insert(0, str(SCHEMA))
    from validate_incremental_sta_samples import (
        BOOTSTRAP_RESAMPLES,
        BOOTSTRAP_SEED,
        MODES,
        consumer_statistics,
    )
    from validate_physical_sta_samples import validate_document, validate_sample

    parser = argparse.ArgumentParser(description=__doc__)
    inputs = ("workspace", "binding-dir", "def-file", "verilog-file", "sdc", "physical-trace")
    for name in inputs:
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=128)
    parser.add_argument("--warmup-runs", type=int, default=5)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.threads <= 0 or args.warmup_runs < 0 or args.samples <= 0 or args.timeout_seconds <= 0:
        parser.error("threads, samples and timeout must be positive; warmups nonnegative")
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    probe = Path(__file__).with_name("physical_sta_probe.py")
    command = [
        sys.executable,
        str(probe),
        "--mode",
        "OFF",
        "--benchmark",
        "--threads",
        str(args.threads),
    ]
    for name in inputs:
        command += [f"--{name}", str(getattr(args, name.replace("-", "_")).resolve(strict=True))]
    environment = dict(os.environ, PYTHONPATH=f"{args.binding_dir.resolve().parent}:{REPOSITORY}")
    protocol = {
        "mode_order": list(MODES),
        "warmups": args.warmup_runs,
        "repetitions": args.samples,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "pairing_unit": "fresh_process_complete_physical_loop",
    }
    (root / "experiment.json").write_text(
        json.dumps(
            {
                "command": command,
                "protocol": protocol,
                "cpu_affinity": sorted(os.sched_getaffinity(0)),
                "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            },
            indent=2,
        )
        + "\n"
    )
    samples = []
    for warmup, count in ((True, args.warmup_runs), (False, args.samples)):
        for repetition in range(1, count + 1):
            for mode in MODES:
                backend, strategy = mode.split("/")
                directory = root / f"{'warmup' if warmup else 'sample'}-{repetition}"
                directory.mkdir(exist_ok=True)
                output = directory / f"{backend}-{strategy}"
                child = [
                    *command,
                    "--backend",
                    backend,
                    "--strategy",
                    strategy,
                    "--output",
                    str(output),
                ]
                (directory / f"{output.name}.command.json").write_text(json.dumps(child) + "\n")
                with (directory / f"{output.name}.log").open("x") as log:
                    started = perf_counter()
                    try:
                        completed = subprocess.run(
                            child,
                            cwd=REPOSITORY,
                            env=environment,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            timeout=args.timeout_seconds,
                        )
                    except subprocess.TimeoutExpired:
                        (directory / f"{output.name}.exit").write_text("124\n")
                        raise
                    wall_ms = (perf_counter() - started) * 1000
                (directory / f"{output.name}.exit").write_text(str(completed.returncode) + "\n")
                completed.check_returncode()
                raw = json.loads((output / "sample.json").read_text())
                validate_sample(raw)
                samples.append(
                    {
                        "mode": mode,
                        "warmup": warmup,
                        "repetition": repetition,
                        "process_wall_ms": wall_ms,
                        "raw_file": str(output / "sample.json"),
                        "measurement": raw,
                    }
                )
                (root / "completed-samples.json").write_text(
                    json.dumps(samples, allow_nan=False) + "\n"
                )
                print(
                    json.dumps(
                        {
                            "mode": mode,
                            "warmup": warmup,
                            "repetition": repetition,
                            "optimization_end_to_end_ms": raw["optimization_end_to_end_ms"],
                        }
                    ),
                    flush=True,
                )
    document = {
        "schema_version": "physical-sta-samples/2.0.0",
        "protocol": protocol,
        "sampling_kind": (
            "engineering" if args.warmup_runs >= 5 and args.samples >= 30 else "short_smoke"
        ),
        "samples": samples,
        "stage15_acceptance": "not_run",
    }
    summaries, comparisons = consumer_statistics(
        [
            {
                "mode": sample["mode"],
                "warmup": sample["warmup"],
                "optimization_end_to_end_ms": sample["measurement"]["optimization_end_to_end_ms"],
            }
            for sample in samples
        ],
        metric="optimization_end_to_end_ms",
    )
    document.update(summaries=summaries, comparisons=comparisons)
    validate_document(document)
    (root / "incremental_sta_samples.json").write_text(
        json.dumps(document, allow_nan=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
