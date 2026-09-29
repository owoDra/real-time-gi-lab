#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-g-transient-lbvh-hardening"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
CONFIG = (
    ROOT / "research/lanes/lane-g-transient-lbvh-hardening/experiments"
    / "002b-paired-counterbalanced-config.json"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def read_one_csv(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one row in {path}")
    return rows[0]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def robust(values: list[float]) -> dict[str, float]:
    median = statistics.median(values)
    mad = statistics.median(abs(x - median) for x in values)
    return {
        "min": min(values),
        "median": median,
        "max": max(values),
        "max_min_ratio": max(values) / min(values),
        "mad": mad,
        "mad_over_median": mad / median,
    }


def orientation(order: str) -> list[str]:
    if order not in {"ABBA", "BAAB"}:
        raise ValueError(order)
    return list(order)


def run_one(
    executable: Path,
    scene: Path,
    root: Path,
    comparison_id: int,
    block: int,
    slot: int,
    role: str,
    variant: str,
    scenario: str,
    warmup: int,
    settle: float,
) -> dict[str, object]:
    if settle > 0.0:
        time.sleep(settle)
    case = (
        root / f"cmp-{comparison_id:02d}" / f"block-{block:02d}"
        / f"{slot}-{role}-{variant}"
    )
    case.mkdir(parents=True, exist_ok=False)
    command = [
        "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(executable),
        "--scene", str(scene),
        "--variant", variant,
        "--scenario", scenario,
        "--warmup-frames", str(warmup),
        "--measured-frames", "1",
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(case)
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    (case / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (case / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"G002b comparison={comparison_id} block={block} slot={slot} failed"
        )

    device = json.loads((case / "g002-device.json").read_text(encoding="utf-8"))
    if device.get("device") != EXPECTED_GPU:
        raise RuntimeError(f"wrong GPU: {device.get('device')!r}")

    row = read_one_csv(case / "g002-frames.csv")
    result: dict[str, object] = dict(row)
    result.update({
        "comparison_id": comparison_id,
        "block": block,
        "slot": slot,
        "role": role,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    parser.add_argument(
        "--scene",
        type=Path,
        default=ROOT / "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf",
    )
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"G002b must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("G002b requires a clean worktree")

    commit = git("rev-parse", "HEAD")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    executable = args.build_dir / "phos-lane-g-g002"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or (
        ROOT / "out/research/lane-g-transient-lbvh-hardening"
        / "002-timing-repeatability-diagnosis" / f"{stamp}-paired"
    )
    root.mkdir(parents=True, exist_ok=False)

    raw: list[dict[str, object]] = []
    block_rows: list[dict[str, object]] = []
    orders = cfg["block_orders"]

    for comparison_id, cmp in enumerate(cfg["comparisons"]):
        for block, order in enumerate(orders):
            measurements: dict[str, list[float]] = {"A": [], "B": []}
            for slot, role in enumerate(orientation(order)):
                variant = cmp["a"] if role == "A" else cmp["b"]
                row = run_one(
                    executable, args.scene, root,
                    comparison_id, block, slot, role, variant, cmp["scenario"],
                    int(cfg["warmup_frames"]), float(cfg["settle_seconds"]),
                )
                raw.append(row)
                measurements[role].append(float(row["complete_gpu_us"]))

            a = math.sqrt(measurements["A"][0] * measurements["A"][1])
            b = math.sqrt(measurements["B"][0] * measurements["B"][1])
            block_rows.append({
                "comparison_id": comparison_id,
                "kind": cmp["kind"],
                "scenario": cmp["scenario"],
                "a": cmp["a"],
                "b": cmp["b"],
                "block": block,
                "order": order,
                "a_geomean_us": a,
                "b_geomean_us": b,
                "ratio": a / b,
            })

    criteria = cfg["repeatability_criteria"]
    comparisons: list[dict[str, object]] = []
    all_pass = True

    for comparison_id, cmp in enumerate(cfg["comparisons"]):
        rows = [r for r in block_rows if r["comparison_id"] == comparison_id]
        ratios = [float(r["ratio"]) for r in rows]
        ratio_stats = robust(ratios)

        by_order: dict[str, list[float]] = {}
        for row in rows:
            by_order.setdefault(str(row["order"]), []).append(float(row["ratio"]))
        orientation_medians = {
            order: statistics.median(values) for order, values in by_order.items()
        }
        orientation_ratio = (
            max(orientation_medians.values()) / min(orientation_medians.values())
        )

        passed = (
            ratio_stats["max_min_ratio"]
            <= float(criteria["block_ratio_max_min"])
            and ratio_stats["mad_over_median"]
            <= float(criteria["block_ratio_mad_over_median"])
            and orientation_ratio
            <= float(criteria["orientation_median_ratio"])
        )
        all_pass = all_pass and passed
        comparisons.append({
            "comparison_id": comparison_id,
            **cmp,
            "block_ratio": ratio_stats,
            "orientation_medians": orientation_medians,
            "orientation_median_ratio": orientation_ratio,
            "repeatability_passed": passed,
        })

    write_csv(root / "g002b-raw.csv", raw)
    write_csv(root / "g002b-block-ratios.csv", block_rows)
    (root / "g002b-summary.json").write_text(
        json.dumps({
            "schema_version": 1,
            "plan_version": cfg["plan_version"],
            "git_commit": commit,
            "target_gpu": EXPECTED_GPU,
            "all_runs_retained": True,
            "repeatability_criteria": criteria,
            "comparisons": comparisons,
            "freeze_ready": all_pass,
            "next_step": (
                "freeze-paired-protocol"
                if all_pass else "continue-g002-clock-power-isolation"
            ),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "g002b-config.json").write_text(
        json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "metadata.json").write_text(
        json.dumps({
            "git_commit": commit,
            "branch": EXPECTED_BRANCH,
            "artifact_root": str(root.relative_to(ROOT)),
            "command": " ".join(sys.argv),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"G002b artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
