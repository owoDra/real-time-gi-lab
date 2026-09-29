#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LANE = "lane-g-transient-lbvh-hardening"
EXPERIMENT = "001-memory-ownership-lifetime-census"
EXPECTED_BRANCH = "research-lane-g-transient-lbvh-hardening"
EXPECTED_GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
CONFIG_PATH = (
    ROOT / "research/lanes/lane-g-transient-lbvh-hardening/experiments"
    / "001-memory-ownership-lifetime-census-config.json"
)
VARIANTS = (
    "transient-lbvh",
    "vanilla-software",
    "combined-hwrt",
    "combined-software",
)
SCENARIOS = (
    "static",
    "moving-rigid",
    "sparse-stress",
    "sparse-moving",
    "dense-moving",
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def classify(
    row: dict[str, str],
    scenario: str,
    dense_reference: dict[tuple[str, str], dict[str, str]],
) -> tuple[str, str]:
    owner = row["owner"]
    name = row["name"]
    if owner in {"transient-lbvh", "static-hwrt"}:
        classification = "candidate-specific"
        reason = "required by the transient-LBVH/HWRT candidate path"
    elif owner in {"shared-integration", "host-mirror"}:
        classification = "shared integration"
        reason = "shared producer/storage/integration ownership"
    else:
        classification = "unavoidable baseline"
        reason = "run-local software comparator ownership"

    if row["allocation_lifetime"] == "runtime" and row["use_lifetime"] == "setup-only":
        classification = "duplicative/non-overlapping lifetime"
        reason = "allocation remains resident for runtime although this path uses it only during setup"

    if scenario in {"sparse-stress", "sparse-moving"}:
        dense = dense_reference.get((row["variant"], name))
        if dense and row["logical_size_known"] == "1" and dense["logical_size_known"] == "1":
            sparse_logical = int(row["logical_bytes"])
            dense_logical = int(dense["logical_bytes"])
            sparse_alloc = int(row["allocation_bytes"])
            dense_alloc = int(dense["allocation_bytes"])
            if (
                sparse_logical < dense_logical
                and sparse_alloc == dense_alloc
                and sparse_alloc > sparse_logical
            ):
                classification = "dense-only capacity retained in sparse workload"
                reason = (
                    "sparse logical payload is smaller but Vulkan allocation "
                    "remains at dense-moving size"
                )
    return classification, reason


def run_case(
    executable: Path,
    scene: Path,
    variant: str,
    scenario: str,
    out_dir: Path,
    validation: bool,
) -> tuple[dict[str, str], list[dict[str, str]], dict[str, object]]:
    out_dir.mkdir(parents=True, exist_ok=False)
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene", str(scene),
        "--variant", variant,
        "--scenario", scenario,
    ]
    if validation:
        command.append("--validation")
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(out_dir)
    proc = subprocess.run(
        command, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    (out_dir / "process.stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out_dir / "process.stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"G001 {variant}/{scenario} failed with {proc.returncode}")

    frames = read_rows(out_dir / "g001-frame.csv")
    allocations = read_rows(out_dir / "g001-allocations.csv")
    if len(frames) != 1:
        raise RuntimeError("G001 frame artifact must contain exactly one row")
    device = json.loads((out_dir / "g001-device.json").read_text(encoding="utf-8"))
    frame = frames[0]
    if device["device"] != EXPECTED_GPU or frame["device"] != EXPECTED_GPU:
        raise RuntimeError(f"wrong target GPU for {variant}/{scenario}: {device['device']}")
    if frame["quality_passed"] != "1" or int(frame["storage_failures"]) != 0:
        raise RuntimeError(f"correctness failed for {variant}/{scenario}")

    names = [row["name"] for row in allocations if row["vulkan_allocation"] == "1"]
    if len(names) != len(set(names)):
        raise RuntimeError(f"duplicate Vulkan allocation census name for {variant}/{scenario}")

    counted = sum(
        int(row["allocation_bytes"])
        for row in allocations
        if row["counted_in_f007_peak"] == "1"
    )
    peak = int(frame["peak_resident_bytes"])
    if counted != peak:
        raise RuntimeError(
            f"allocation accounting mismatch for {variant}/{scenario}: "
            f"census={counted}, F007-peak={peak}, delta={counted - peak}"
        )
    return frame, allocations, device


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
    parser.add_argument("--validation", action="store_true")
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"G001 must run on {EXPECTED_BRANCH}, got {branch}")
    if git("status", "--porcelain"):
        raise RuntimeError("G001 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    executable = args.build_dir / "phos-lane-g-g001"
    if not executable.is_file():
        raise RuntimeError(f"missing G001 executable: {executable}")
    if not args.scene.is_file():
        raise RuntimeError(f"missing scene: {args.scene}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or ROOT / "out/research" / LANE / EXPERIMENT / stamp
    root.mkdir(parents=True, exist_ok=False)

    frames: list[dict[str, str]] = []
    allocations: list[dict[str, str]] = []
    devices: list[dict[str, object]] = []
    for variant in VARIANTS:
        for scenario in SCENARIOS:
            frame, rows, device = run_case(
                executable,
                args.scene,
                variant,
                scenario,
                root / variant / scenario,
                args.validation,
            )
            frames.append(frame)
            allocations.extend(rows)
            devices.append(device)

    dense_reference = {
        (row["variant"], row["name"]): row
        for row in allocations
        if row["scenario"] == "dense-moving"
    }

    owner_totals: dict[tuple[str, str, str], int] = defaultdict(int)
    role_totals: dict[tuple[str, str, str], int] = defaultdict(int)
    capacity_totals: dict[tuple[str, str, str], int] = defaultdict(int)
    lifetime_totals: dict[tuple[str, str, str], int] = defaultdict(int)
    classified: list[dict[str, object]] = []
    for row in allocations:
        classification, reason = classify(row, row["scenario"], dense_reference)
        logical = int(row["logical_bytes"])
        allocation = int(row["allocation_bytes"])
        enriched: dict[str, object] = dict(row)
        enriched["classification"] = classification
        enriched["classification_reason"] = reason
        enriched["allocation_minus_logical_bytes"] = (
            allocation - logical if row["logical_size_known"] == "1" else ""
        )
        classified.append(enriched)
        if row["counted_in_f007_peak"] == "1":
            owner_totals[(row["variant"], row["scenario"], row["owner"])] += allocation
            role_totals[(row["variant"], row["scenario"], row["role"])] += allocation
            capacity_totals[(row["variant"], row["scenario"], row["capacity_kind"])] += allocation
            lifetime_totals[(row["variant"], row["scenario"], row["use_lifetime"])] += allocation

    ownership_rows: list[dict[str, object]] = []
    for (variant, scenario, owner), bytes_ in sorted(owner_totals.items()):
        ownership_rows.append({
            "variant": variant,
            "scenario": scenario,
            "group_kind": "owner",
            "group": owner,
            "bytes": bytes_,
        })
    for (variant, scenario, role), bytes_ in sorted(role_totals.items()):
        ownership_rows.append({
            "variant": variant,
            "scenario": scenario,
            "group_kind": "role",
            "group": role,
            "bytes": bytes_,
        })
    for (variant, scenario, capacity), bytes_ in sorted(capacity_totals.items()):
        ownership_rows.append({
            "variant": variant,
            "scenario": scenario,
            "group_kind": "capacity-kind",
            "group": capacity,
            "bytes": bytes_,
        })
    for (variant, scenario, lifetime), bytes_ in sorted(lifetime_totals.items()):
        ownership_rows.append({
            "variant": variant,
            "scenario": scenario,
            "group_kind": "use-lifetime",
            "group": lifetime,
            "bytes": bytes_,
        })

    frame_by_key = {(r["variant"], r["scenario"]): r for r in frames}
    ratios: dict[str, float] = {}
    for scenario in SCENARIOS:
        candidate = int(frame_by_key[("transient-lbvh", scenario)]["peak_resident_bytes"])
        vanilla = int(frame_by_key[("vanilla-software", scenario)]["peak_resident_bytes"])
        ratios[scenario] = candidate / vanilla

    anchors = config["frozen_f007_sparse_memory_ratios"]
    tolerance = float(config["anchor_absolute_tolerance"])
    anchor_checks = {
        scenario: {
            "observed": ratios[scenario],
            "f007_anchor": float(anchor),
            "absolute_delta": abs(ratios[scenario] - float(anchor)),
            "passed": abs(ratios[scenario] - float(anchor)) <= tolerance,
        }
        for scenario, anchor in anchors.items()
    }

    summary = {
        "schema_version": 1,
        "plan_version": "lane-g-g001-v1",
        "git_commit": commit,
        "target_gpu": EXPECTED_GPU,
        "validation_enabled": args.validation,
        "case_count": len(frames),
        "allocation_row_count": len(allocations),
        "accounting_identity_passed": True,
        "double_counting_detected": False,
        "candidate_peak_ratio_vs_vanilla": ratios,
        "f007_anchor_checks": anchor_checks,
        "g001_conclusion_ready": all(x["passed"] for x in anchor_checks.values()),
        "note": (
            "G001 is memory-only diagnosis. Timing from these executions is not "
            "decision-valid G002/G003 evidence."
        ),
    }
    validation = {
        "schema_version": 1,
        "git_commit": commit,
        "target_gpu": EXPECTED_GPU,
        "all_quality_passed": all(r["quality_passed"] == "1" for r in frames),
        "all_storage_failures_zero": all(int(r["storage_failures"]) == 0 for r in frames),
        "all_accounting_identities_exact": True,
        "duplicate_vulkan_allocation_names_detected": False,
        "all_devices_exact": all(d["device"] == EXPECTED_GPU for d in devices),
        "f007_sparse_anchor_reproduced": all(x["passed"] for x in anchor_checks.values()),
    }

    write_rows(root / "g001-raw-frames.csv", frames)
    write_rows(root / "g001-raw-allocations.csv", classified)
    write_rows(root / "g001-byte-ownership.csv", ownership_rows)
    write_json(root / "g001-summary.json", summary)
    write_json(root / "g001-validation.json", validation)
    write_json(root / "g001-config.json", config)
    write_json(root / "g001-device.json", {"target_gpu": EXPECTED_GPU, "devices": devices})
    write_json(root / "metadata.json", {
        "git_commit": commit,
        "branch": branch,
        "artifact_root": str(root.relative_to(ROOT)),
        "validation": args.validation,
    })
    print(f"G001 artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
