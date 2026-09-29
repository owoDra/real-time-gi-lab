#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-g-transient-lbvh-hardening"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
CONFIG = (
    ROOT / "research/lanes/lane-g-transient-lbvh-hardening/experiments"
    / "005-final-deterministic-replay-config.json"
)
ZERO_FIELDS = (
    "visibility_mismatches",
    "producer_semantic_errors",
    "hit_mismatches",
    "traversal_runtime_errors",
    "missing_probes",
    "leaked_probes",
    "stale_storage_slots",
    "resolved_output_mismatches",
    "storage_failures",
    "overflow",
)
WORKLOAD_FIELDS = (
    "work_items",
    "outputs",
    "requested_work_items",
    "requested_outputs",
    "visible_owners",
    "moved_primitives",
    "segment_membership_changes",
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True,
        capture_output=True, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def read_one(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise RuntimeError(f"expected one row in {path}")
    return rows[0]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def row_failures(row: dict[str, str]) -> list[str]:
    failures: list[str] = []
    if row["quality_passed"] != "1":
        failures.append("quality_passed")
    for field in ZERO_FIELDS:
        if int(row[field]) != 0:
            failures.append(field)
    return failures


def assert_same_workload(
    scenario: str,
    rows: list[dict[str, str]],
) -> None:
    for field in WORKLOAD_FIELDS:
        values = {row[field] for row in rows}
        if len(values) != 1:
            raise RuntimeError(
                f"G005 {scenario} workload diverged for {field}: "
                f"{sorted(values)}"
            )


def run_case(
    executable: Path,
    scene: Path,
    variant: str,
    scenario: str,
    output: Path,
) -> tuple[dict[str, str], dict[str, object]]:
    output.mkdir(parents=True, exist_ok=False)
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene", str(scene),
        "--variant", variant,
        "--scenario", scenario,
        "--validation",
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(output)
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    (output / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (output / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"G005 {scenario}/{variant} failed with {proc.returncode}"
        )

    row = read_one(output / "g005-frame.csv")
    device = json.loads((output / "g005-device.json").read_text(encoding="utf-8"))
    if row["variant"] != variant or row["scenario"] != scenario:
        raise RuntimeError(f"G005 {scenario}/{variant} identity mismatch")
    if row["device"] != EXPECTED_GPU or device["device"] != EXPECTED_GPU:
        raise RuntimeError(f"G005 {scenario}/{variant} wrong GPU")
    failures = row_failures(row)
    if failures:
        raise RuntimeError(
            f"G005 {scenario}/{variant} correctness failed: "
            + ", ".join(failures)
        )
    return row, device


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
        raise RuntimeError(f"G005 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("G005 requires a clean worktree")

    commit = git("rev-parse", "HEAD")
    executable = args.build_dir / "phos-lane-g-g005"
    if not executable.is_file():
        raise RuntimeError(f"missing G005 executable: {executable}")
    if not args.scene.is_file():
        raise RuntimeError(f"missing scene: {args.scene}")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    variants = cfg["variants"]
    scenarios = cfg["scenarios"]
    if len(variants) != 5 or len(scenarios) != 12:
        raise RuntimeError("G005 frozen matrix shape changed")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or (
        ROOT / "out/research/lane-g-transient-lbvh-hardening"
        / "005-final-deterministic-replay" / stamp
    )
    root.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, str]] = []
    devices: list[dict[str, object]] = []
    scenario_rows: dict[str, list[dict[str, str]]] = {}

    for scenario in scenarios:
        current: list[dict[str, str]] = []
        for variant in variants:
            row, device = run_case(
                executable,
                args.scene,
                variant,
                scenario,
                root / scenario / variant,
            )
            rows.append(row)
            devices.append(device)
            current.append(row)
        assert_same_workload(scenario, current)
        scenario_rows[scenario] = current

    by_key = {(row["scenario"], row["variant"]): row for row in rows}
    memory: dict[str, object] = {}
    all_memory = True
    sparse_memory = True
    no_regression = True

    for scenario in scenarios:
        hardened = int(
            by_key[(scenario, "hardened-transient-lbvh")]["peak_resident_bytes"]
        )
        baseline = int(
            by_key[(scenario, "transient-lbvh")]["peak_resident_bytes"]
        )
        vanilla = int(
            by_key[(scenario, "vanilla-software")]["peak_resident_bytes"]
        )
        ratio = hardened / vanilla
        regression = (hardened - baseline) / baseline
        ratio_pass = ratio <= 3.0
        regression_pass = regression <= 0.10
        all_memory = all_memory and ratio_pass
        no_regression = no_regression and regression_pass
        if scenario in {"sparse-stress", "sparse-moving"}:
            sparse_memory = sparse_memory and ratio_pass

        memory[scenario] = {
            "hardened_peak_bytes": hardened,
            "unchanged_lbvh_peak_bytes": baseline,
            "vanilla_peak_bytes": vanilla,
            "hardened_ratio_vs_vanilla": ratio,
            "hardened_regression_vs_unchanged_lbvh": regression,
            "ratio_lte_3_passed": ratio_pass,
            "regression_lte_10pct_passed": regression_pass,
            "combined_hwrt_peak_bytes": int(
                by_key[(scenario, "combined-hwrt")]["peak_resident_bytes"]
            ),
            "combined_software_peak_bytes": int(
                by_key[(scenario, "combined-software")]["peak_resident_bytes"]
            ),
        }

    correctness = all(not row_failures(row) for row in rows)
    same_workload = True  # assert_same_workload already aborts on divergence.
    deterministic_pass = (
        correctness
        and same_workload
        and all_memory
        and sparse_memory
        and no_regression
    )

    summary = {
        "schema_version": 1,
        "plan_version": cfg["plan_version"],
        "git_commit": commit,
        "target_gpu": EXPECTED_GPU,
        "row_count": len(rows),
        "all_runs_retained": True,
        "all_devices_exact": all(
            device["device"] == EXPECTED_GPU for device in devices
        ),
        "correctness_passed": correctness,
        "same_workload_passed": same_workload,
        "all_memory_ratio_lte_3_passed": all_memory,
        "sparse_memory_gates_passed": sparse_memory,
        "no_gt_10pct_memory_regression_passed": no_regression,
        "deterministic_g005_passed": deterministic_pass,
        "formal_timing_gate": "inconclusive-g002-no-safe-decision-valid-protocol",
        "timing_used_for_decision": False,
        "power_clock_manipulation": False,
        "lane_e_comparator_included": False,
        "lane_e_replacement_claim_permitted": False,
        "final_disposition_if_pass": (
            "mechanism-retained-memory-correctness-pass-"
            "production-promotion-measurement-limited"
        ),
        "memory": memory,
    }

    write_csv(root / "g005-raw.csv", rows)
    (root / "g005-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "g005-device.json").write_text(
        json.dumps(
            {"target_gpu": EXPECTED_GPU, "devices": devices},
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (root / "g005-config.json").write_text(
        json.dumps(cfg, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "git_commit": commit,
                "branch": EXPECTED_BRANCH,
                "artifact_root": str(root.relative_to(ROOT)),
                "validation": True,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    print(f"G005 artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
