#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
CASES = ("static", "camera-motion", "light-motion")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Replay Lane A stream-v1 artifacts through retained C001 storage candidates."
    )
    ap.add_argument("--lane-a-artifact", type=Path, required=True)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--iterations", type=int, default=100)
    ap.add_argument("--validation", action="store_true")
    args = ap.parse_args()
    if args.repeats <= 0 or args.iterations <= 0:
        ap.error("--repeats and --iterations must be positive")

    streams = {
        case: args.lane_a_artifact / case / "stream-v1.bin"
        for case in CASES
    }
    missing = [str(path) for path in streams.values() if not path.is_file()]
    if missing:
        raise SystemExit("missing Lane A replay stream(s):\n  " + "\n  ".join(missing))

    artifact_env = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if not artifact_env:
        raise SystemExit(
            "c001c_matrix.py must run through research:record so "
            "PHOS_RESEARCH_ARTIFACT_DIR is set"
        )
    artifact_root = Path(artifact_env)
    artifact_root.mkdir(parents=True, exist_ok=True)

    rows_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for case in CASES:
        for repeat in range(1, args.repeats + 1):
            repeat_dir = artifact_root / case / f"repeat-{repeat:02d}"
            repeat_dir.mkdir(parents=True, exist_ok=False)
            env = os.environ.copy()
            env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(repeat_dir)
            command = [
                "bash",
                "scripts/research/lane_c_storage_locality/run_c001c.sh",
                "--stream",
                str(streams[case]),
                "--iterations",
                str(args.iterations),
            ]
            if args.validation:
                command.append("--validation")

            proc = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            sys.stdout.write(proc.stdout)
            sys.stderr.write(proc.stderr)
            sys.stdout.flush()
            sys.stderr.flush()
            if proc.returncode != 0:
                return proc.returncode

            csv_path = repeat_dir / "c001c.csv"
            with csv_path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    key = (case, row["representation"], row["phase"])
                    rows_by_key.setdefault(key, []).append(row)

    summary_path = artifact_root / "c001c_summary.csv"
    invariant_fields = [
        "workload_id",
        "items",
        "writes",
        "bricks",
        "persistent_bytes",
        "scratch_bytes",
        "producer_input_bytes",
    ]
    fieldnames = [
        "case",
        "representation",
        "workload_id",
        "phase",
        "repeats",
        "items",
        "writes",
        "bricks",
        "persistent_bytes",
        "scratch_bytes",
        "producer_input_bytes",
        "gpu_us_median",
        "gpu_us_min",
        "gpu_us_max",
        "all_correct",
    ]
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key in sorted(rows_by_key):
            rows = rows_by_key[key]
            if len(rows) != args.repeats:
                raise SystemExit(
                    f"incomplete repeat set for {key}: {len(rows)}/{args.repeats}"
                )
            for field in invariant_fields:
                values = {row[field] for row in rows}
                if len(values) != 1:
                    raise SystemExit(
                        f"{key}: non-timing field changed across repeats: "
                        f"{field}={values}"
                    )
            times = [float(row["gpu_us"]) for row in rows]
            writer.writerow(
                {
                    "case": key[0],
                    "representation": key[1],
                    "workload_id": rows[0]["workload_id"],
                    "phase": key[2],
                    "repeats": args.repeats,
                    "items": rows[0]["items"],
                    "writes": rows[0]["writes"],
                    "bricks": rows[0]["bricks"],
                    "persistent_bytes": rows[0]["persistent_bytes"],
                    "scratch_bytes": rows[0]["scratch_bytes"],
                    "producer_input_bytes": rows[0]["producer_input_bytes"],
                    "gpu_us_median": statistics.median(times),
                    "gpu_us_min": min(times),
                    "gpu_us_max": max(times),
                    "all_correct": str(
                        all(row["correct"] == "true" for row in rows)
                    ).lower(),
                }
            )

    if any(
        row["correct"] != "true"
        for rows in rows_by_key.values()
        for row in rows
    ):
        print("fatal: at least one C001c repeat failed correctness", file=sys.stderr)
        return 2

    print(f"C001c summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
