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
    / "002c-power-isolated-config.json"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def discover_amdgpu_sysfs(explicit: Path | None) -> Path:
    if explicit is not None:
        path = explicit.resolve()
        if not (path / "power_dpm_force_performance_level").is_file():
            raise RuntimeError(
                f"missing power_dpm_force_performance_level under {path}"
            )
        return path

    candidates = sorted({
        path.parent.resolve()
        for path in Path("/sys/class/drm").glob(
            "card*/device/power_dpm_force_performance_level"
        )
        if read_text(path.parent / "vendor") in {"0x1002", "1002"}
    })
    if len(candidates) != 1:
        rendered = ", ".join(str(path) for path in candidates) or "none"
        raise RuntimeError(
            "G002c needs exactly one AMDGPU sysfs device or --amdgpu-sysfs; "
            f"found: {rendered}"
        )
    return candidates[0]


def power_snapshot(device: Path) -> dict[str, str | None]:
    names = (
        "power_dpm_force_performance_level",
        "pp_dpm_sclk",
        "pp_dpm_mclk",
        "pp_dpm_fclk",
        "pp_dpm_socclk",
        "pp_power_profile_mode",
        "gpu_busy_percent",
        "mem_busy_percent",
    )
    return {name: read_text(device / name) for name in names}


def require_profile_peak(device: Path) -> dict[str, str | None]:
    snapshot = power_snapshot(device)
    actual = snapshot["power_dpm_force_performance_level"]
    if actual != "profile_peak":
        raise RuntimeError(
            "G002c requires power_dpm_force_performance_level=profile_peak; "
            f"got {actual!r}. The runner is intentionally read-only."
        )
    return snapshot


def read_one_csv(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one row in {path}")
    return rows[0]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def robust(values: list[float]) -> dict[str, float]:
    median = statistics.median(values)
    mad = statistics.median(abs(value - median) for value in values)
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
    device: Path,
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
    before = require_profile_peak(device)

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
    after = require_profile_peak(device)

    (case / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (case / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    (case / "power-before.json").write_text(
        json.dumps(before, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (case / "power-after.json").write_text(
        json.dumps(after, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    if proc.returncode != 0:
        raise RuntimeError(
            f"G002c comparison={comparison_id} block={block} slot={slot} failed"
        )

    device_json = json.loads(
        (case / "g002-device.json").read_text(encoding="utf-8")
    )
    if device_json.get("device") != EXPECTED_GPU:
        raise RuntimeError(f"wrong GPU: {device_json.get('device')!r}")

    row = read_one_csv(case / "g002-frames.csv")
    result: dict[str, object] = dict(row)
    result.update({
        "comparison_id": comparison_id,
        "block": block,
        "slot": slot,
        "role": role,
        "power_level_before": before["power_dpm_force_performance_level"],
        "power_level_after": after["power_dpm_force_performance_level"],
        "sclk_before": before["pp_dpm_sclk"],
        "sclk_after": after["pp_dpm_sclk"],
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
    parser.add_argument("--amdgpu-sysfs", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"G002c must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("G002c requires a clean worktree")

    commit = git("rev-parse", "HEAD")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    device = discover_amdgpu_sysfs(args.amdgpu_sysfs)
    initial_power = require_profile_peak(device)

    executable = args.build_dir / "phos-lane-g-g002"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or (
        ROOT / "out/research/lane-g-transient-lbvh-hardening"
        / "002-timing-repeatability-diagnosis" / f"{stamp}-profile-peak"
    )
    root.mkdir(parents=True, exist_ok=False)

    raw: list[dict[str, object]] = []
    block_rows: list[dict[str, object]] = []

    for comparison_id, cmp in enumerate(cfg["comparisons"]):
        for block, order in enumerate(cfg["block_orders"]):
            measurements: dict[str, list[float]] = {"A": [], "B": []}
            for slot, role in enumerate(orientation(order)):
                variant = cmp["a"] if role == "A" else cmp["b"]
                row = run_one(
                    executable, args.scene, root, device,
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
        rows = [row for row in block_rows if row["comparison_id"] == comparison_id]
        ratios = [float(row["ratio"]) for row in rows]
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

    final_power = require_profile_peak(device)
    write_csv(root / "g002c-raw.csv", raw)
    write_csv(root / "g002c-block-ratios.csv", block_rows)
    (root / "g002c-summary.json").write_text(
        json.dumps({
            "schema_version": 1,
            "plan_version": cfg["plan_version"],
            "git_commit": commit,
            "target_gpu": EXPECTED_GPU,
            "amdgpu_sysfs": str(device),
            "initial_power": initial_power,
            "final_power": final_power,
            "all_runs_retained": True,
            "repeatability_criteria": criteria,
            "comparisons": comparisons,
            "freeze_ready": all_pass,
            "next_step": (
                "freeze-power-isolated-paired-protocol"
                if all_pass else "continue-g002-system-load-isolation"
            ),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "g002c-config.json").write_text(
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
    print(f"G002c artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
