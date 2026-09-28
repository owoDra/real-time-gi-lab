#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import re
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINARY = ROOT / "build" / "release" / "phos-gi-lab"
DEFAULT_SCENE = ROOT / "assets" / "Vulkan-Samples-Assets" / "scenes" / "sponza" / "Sponza01.gltf"
GPU_RE = re.compile(r"^GPU:\s*(.+)$", re.MULTILINE)


def parse_counts(value: str) -> list[int]:
    counts = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not counts or any(count <= 0 for count in counts):
        raise argparse.ArgumentTypeError("query counts must be positive comma-separated integers")
    return counts


def git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def parse_rows(stdout: str) -> list[dict[str, str]]:
    rows = list(csv.DictReader(io.StringIO(stdout)))
    if not rows:
        raise RuntimeError("benchmark produced no CSV rows")

    # These are the original artifact columns and remain mandatory. New
    # scheduling metadata is additive so older downstream readers can continue
    # consuming the same core schema.
    required = {
        "variant",
        "queries",
        "pages",
        "bytes",
        "gpu_us_per_dispatch",
        "checksum",
        "expected_checksum",
        "correct",
    }
    missing = required.difference(rows[0])
    if missing:
        raise RuntimeError(f"benchmark CSV is missing columns: {sorted(missing)}")

    for row in rows:
        if row["correct"].lower() != "true":
            raise RuntimeError(
                f"correctness guard failed for {row['variant']}: "
                f"{row['checksum']} != {row['expected_checksum']}"
            )

    checksums = {row["checksum"] for row in rows}
    expected = {row["expected_checksum"] for row in rows}
    if len(checksums) != 1 or len(expected) != 1 or checksums != expected:
        raise RuntimeError("variants did not produce one shared semantic checksum")

    return rows


def run_once(
    binary: Path,
    scene: Path,
    query_count: int,
    iterations: int,
    synthetic: bool,
    validation: bool,
) -> tuple[list[dict[str, str]], str, list[str], str]:
    command = [
        "bash",
        str(ROOT / "scripts" / "run_with_vulkan.sh"),
        str(binary),
    ]
    if synthetic:
        command.append("--synthetic")
    else:
        command.extend(["--scene", str(scene)])
    command.extend(["--queries", str(query_count), "--iterations", str(iterations)])
    if validation:
        command.append("--validation")

    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if proc.stderr:
        sys.stderr.write(proc.stderr)

    if proc.returncode != 0:
        raise RuntimeError(
            f"benchmark failed with exit code {proc.returncode}: {' '.join(command)}"
        )

    rows = parse_rows(proc.stdout)
    match = GPU_RE.search(proc.stderr)
    gpu = match.group(1).strip() if match else "unknown"
    return rows, gpu, command, proc.stderr


def _ordering(row: dict[str, str]) -> str:
    if row.get("ordering"):
        return row["ordering"]
    variant = row["variant"]
    if variant in {"hash", "paged"}:
        return "source"
    if variant == "paged-sorted":
        return "page-grouped"
    return "unknown"


def _representation(row: dict[str, str]) -> str:
    if row.get("representation"):
        return row["representation"]
    return "hash" if row["variant"].startswith("hash") else "paged"


def add_speedups(rows: list[dict[str, str]]) -> None:
    hash_rows = [
        row
        for row in rows
        if _representation(row) == "hash" and _ordering(row) == "source"
    ]
    if len(hash_rows) != 1:
        raise RuntimeError("each run must contain exactly one hash/source baseline")

    hash_us = float(hash_rows[0]["gpu_us_per_dispatch"])
    by_axis = {
        (_representation(row), _ordering(row)): row
        for row in rows
    }

    for row in rows:
        us = float(row["gpu_us_per_dispatch"])
        representation = _representation(row)
        ordering = _ordering(row)

        row["representation"] = representation
        row["ordering"] = ordering
        row["speedup_vs_hash"] = f"{hash_us / us:.6f}"

        same_order_hash = by_axis.get(("hash", ordering))
        row["speedup_vs_same_order_hash"] = (
            f"{float(same_order_hash['gpu_us_per_dispatch']) / us:.6f}"
            if same_order_hash is not None
            else ""
        )

        source_same_rep = by_axis.get((representation, "source"))
        ordering_speedup = (
            float(source_same_rep["gpu_us_per_dispatch"]) / us
            if source_same_rep is not None
            else None
        )
        row["ordering_speedup_vs_source"] = (
            f"{ordering_speedup:.6f}" if ordering_speedup is not None else ""
        )

        hash_source = by_axis.get(("hash", "source"))
        hash_same_order = by_axis.get(("hash", ordering))
        hash_ordering_speedup = (
            float(hash_source["gpu_us_per_dispatch"])
            / float(hash_same_order["gpu_us_per_dispatch"])
            if hash_source is not None and hash_same_order is not None
            else None
        )
        row["ordering_interaction_ratio_vs_hash"] = (
            f"{ordering_speedup / hash_ordering_speedup:.6f}"
            if ordering_speedup is not None
            and hash_ordering_speedup is not None
            and hash_ordering_speedup != 0
            else ""
        )

        end_to_end = row.get("end_to_end_gpu_us_per_dispatch", "")
        row["end_to_end_speedup_vs_hash"] = (
            f"{hash_us / float(end_to_end):.6f}" if end_to_end else ""
        )


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _median_optional(values: list[dict[str, object]], field: str) -> str:
    samples = [
        float(value[field])
        for value in values
        if str(value.get(field, "")).strip()
    ]
    if not samples:
        return ""
    return f"{statistics.median(samples):.6f}"


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[int, str], list[dict[str, object]]] = {}
    for row in rows:
        key = (int(row["query_count"]), str(row["variant"]))
        grouped.setdefault(key, []).append(row)

    medians: dict[tuple[int, str], float] = {}
    axis_medians: dict[tuple[int, str, str], float] = {}
    for key, values in grouped.items():
        median = statistics.median(
            float(value["gpu_us_per_dispatch"]) for value in values
        )
        medians[key] = median
        first = values[0]
        axis_medians[
            (
                int(first["query_count"]),
                str(first["representation"]),
                str(first["ordering"]),
            )
        ] = median

    summary: list[dict[str, object]] = []
    for (query_count, variant), values in sorted(grouped.items()):
        median_us = medians[(query_count, variant)]
        hash_us = axis_medians[(query_count, "hash", "source")]
        bytes_values = {int(value["bytes"]) for value in values}
        scheduling_bytes_values = {
            int(value.get("scheduling_bytes", 0) or 0) for value in values
        }
        if len(bytes_values) != 1 or len(scheduling_bytes_values) != 1:
            raise RuntimeError("memory byte counts changed between repeats")

        representation = str(values[0]["representation"])
        ordering = str(values[0]["ordering"])
        same_order_hash = axis_medians.get((query_count, "hash", ordering))
        source_same_rep = axis_medians.get((query_count, representation, "source"))
        hash_same_order = axis_medians.get((query_count, "hash", ordering))
        hash_ordering_speedup = (
            hash_us / hash_same_order if hash_same_order is not None else None
        )
        ordering_speedup = (
            source_same_rep / median_us if source_same_rep is not None else None
        )

        median_schedule = _median_optional(
            values, "scheduling_gpu_us_per_dispatch"
        )
        median_end_to_end = _median_optional(
            values, "end_to_end_gpu_us_per_dispatch"
        )

        summary.append(
            {
                "query_count": query_count,
                "variant": variant,
                "representation": representation,
                "ordering": ordering,
                "repeats": len(values),
                "median_gpu_us_per_dispatch": f"{median_us:.6f}",
                "speedup_vs_hash": f"{hash_us / median_us:.6f}",
                "speedup_vs_same_order_hash": (
                    f"{same_order_hash / median_us:.6f}"
                    if same_order_hash is not None
                    else ""
                ),
                "ordering_speedup_vs_source": (
                    f"{ordering_speedup:.6f}" if ordering_speedup is not None else ""
                ),
                "ordering_interaction_ratio_vs_hash": (
                    f"{ordering_speedup / hash_ordering_speedup:.6f}"
                    if ordering_speedup is not None
                    and hash_ordering_speedup is not None
                    and hash_ordering_speedup != 0
                    else ""
                ),
                "bytes": next(iter(bytes_values)),
                "scheduling_bytes": next(iter(scheduling_bytes_values)),
                "median_scheduling_gpu_us_per_dispatch": median_schedule,
                "median_end_to_end_gpu_us_per_dispatch": median_end_to_end,
                "end_to_end_speedup_vs_hash": (
                    f"{hash_us / float(median_end_to_end):.6f}"
                    if median_end_to_end
                    else ""
                ),
            }
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the reproducible M0 layout-vs-scheduling benchmark matrix."
    )
    parser.add_argument(
        "--query-counts",
        type=parse_counts,
        default=parse_counts("100000,500000,1000000,4000000,8000000"),
    )
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--validation", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.iterations <= 0 or args.repeats <= 0:
        parser.error("--iterations and --repeats must be positive")

    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    output = args.output or (ROOT / "out" / "benchmarks" / stamp)
    output = output if output.is_absolute() else ROOT / output
    logs_dir = output / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, object]] = []
    commands: list[list[str]] = []
    gpus: set[str] = set()

    for query_count in args.query_counts:
        for repeat in range(1, args.repeats + 1):
            rows, gpu, command, stderr = run_once(
                args.binary,
                args.scene,
                query_count,
                args.iterations,
                args.synthetic,
                args.validation,
            )
            add_speedups(rows)
            commands.append(command)
            gpus.add(gpu)

            log_path = logs_dir / f"q{query_count}-r{repeat}.log"
            log_path.write_text(stderr, encoding="utf-8")

            for row in rows:
                row["query_count"] = query_count
                row["repeat"] = repeat
                all_rows.append(row)

    raw_fields = [
        "query_count",
        "repeat",
        "variant",
        "queries",
        "pages",
        "bytes",
        "gpu_us_per_dispatch",
        "speedup_vs_hash",
        "speedup_vs_same_order_hash",
        "ordering_speedup_vs_source",
        "ordering_interaction_ratio_vs_hash",
        "end_to_end_speedup_vs_hash",
        "checksum",
        "expected_checksum",
        "correct",
        "representation",
        "ordering",
        "scheduling_bytes",
        "scheduling_gpu_us_per_dispatch",
        "end_to_end_gpu_us_per_dispatch",
    ]
    write_csv(output / "results.csv", all_rows, raw_fields)

    summary_rows = summarize(all_rows)
    write_csv(
        output / "summary.csv",
        summary_rows,
        [
            "query_count",
            "variant",
            "representation",
            "ordering",
            "repeats",
            "median_gpu_us_per_dispatch",
            "speedup_vs_hash",
            "speedup_vs_same_order_hash",
            "ordering_speedup_vs_source",
            "ordering_interaction_ratio_vs_hash",
            "bytes",
            "scheduling_bytes",
            "median_scheduling_gpu_us_per_dispatch",
            "median_end_to_end_gpu_us_per_dispatch",
            "end_to_end_speedup_vs_hash",
        ],
    )

    metadata = {
        "schema_version": 2,
        "experiment": "000-page-local-cache",
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "gpu": sorted(gpus),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "query_counts": args.query_counts,
        "iterations": args.iterations,
        "repeats": args.repeats,
        "synthetic": args.synthetic,
        "validation": args.validation,
        "scene": str(args.scene),
        "binary": str(args.binary),
        "ordering_regimes": [
            "source",
            "randomized",
            "page-grouped",
            "gpu-page-grouped",
        ],
        "gpu_scheduling": "dense-page histogram + single-workgroup prefix + scatter",
        "commands": commands,
        "environment": {
            "VK_DRIVER_FILES": os.environ.get("VK_DRIVER_FILES"),
            "AMD_VULKAN_ICD": os.environ.get("AMD_VULKAN_ICD"),
        },
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Benchmark artifacts: {output}")
    print("query_count,variant,median_gpu_us_per_dispatch,speedup_vs_hash,bytes")
    for row in summary_rows:
        print(
            f"{row['query_count']},{row['variant']},"
            f"{row['median_gpu_us_per_dispatch']},"
            f"{row['speedup_vs_hash']},{row['bytes']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
