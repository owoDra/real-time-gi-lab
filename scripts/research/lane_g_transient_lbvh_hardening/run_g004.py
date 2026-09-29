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
    / "004-integration-hardening-config.json"
)
DYNAMIC_SCENARIOS = {
    "moving-rigid",
    "sparse-moving",
    "dense-moving",
    "large-world-moving",
    "vertical-world-moving",
}
ZERO_QUALITY_FIELDS = (
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


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True,
        capture_output=True, check=False,
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
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def semantic_failures(
    case: dict[str, str],
    row: dict[str, str],
) -> list[str]:
    failures: list[str] = []
    if row["quality_passed"] != "1":
        failures.append("quality_passed")
    for field in ZERO_QUALITY_FIELDS:
        if int(row[field]) != 0:
            failures.append(field)

    dynamic = case["scenario"] in DYNAMIC_SCENARIOS
    moved = int(row["moved_primitives"])
    groups = int(row["dynamic_groups"])
    deformed = int(row["deformed_primitives"])
    topology = int(row["topology_replaced_primitives"])

    if dynamic:
        if moved <= 0:
            failures.append("moved_primitives")
        if groups <= 0:
            failures.append("dynamic_groups")
    elif moved != 0 or groups != 0:
        failures.append("unexpected_dynamic_work")

    geometry = case["geometry_class"]
    if geometry == "deforming":
        if deformed <= 0:
            failures.append("deformed_primitives")
        if topology != 0:
            failures.append("unexpected_topology_replacement")
    elif geometry == "topology-replace25":
        if topology <= 0:
            failures.append("topology_replaced_primitives")
    else:
        if deformed != 0:
            failures.append("unexpected_deformation")
        if topology != 0:
            failures.append("unexpected_topology_replacement")

    return failures


def run_case(
    executable: Path,
    scene: Path,
    case_id: int,
    case: dict[str, str],
    output: Path,
) -> tuple[dict[str, str], dict[str, object]]:
    output.mkdir(parents=True, exist_ok=False)
    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--scene", str(scene),
        "--scenario", case["scenario"],
        "--geometry-class", case["geometry_class"],
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
            f"G004 case {case_id} {case['scenario']}/"
            f"{case['geometry_class']} failed with {proc.returncode}"
        )

    row = read_one_csv(output / "g004-frame.csv")
    device = json.loads((output / "g004-device.json").read_text(encoding="utf-8"))
    if row["variant"] != "hardened-transient-lbvh":
        raise RuntimeError(f"G004 case {case_id} wrong variant")
    if row["scenario"] != case["scenario"]:
        raise RuntimeError(f"G004 case {case_id} wrong scenario")
    if row["geometry_class"] != case["geometry_class"]:
        raise RuntimeError(f"G004 case {case_id} wrong geometry class")
    if row["device"] != EXPECTED_GPU or device["device"] != EXPECTED_GPU:
        raise RuntimeError(f"G004 case {case_id} wrong GPU")

    failures = semantic_failures(case, row)
    if failures:
        raise RuntimeError(
            f"G004 case {case_id} semantic gates failed: "
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
        raise RuntimeError(f"G004 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("G004 requires a clean worktree")

    commit = git("rev-parse", "HEAD")
    executable = args.build_dir / "phos-lane-g-g004"
    if not executable.is_file():
        raise RuntimeError(f"missing G004 executable: {executable}")
    if not args.scene.is_file():
        raise RuntimeError(f"missing scene: {args.scene}")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cases = cfg["cases"]
    if len(cases) != 16:
        raise RuntimeError("G004 frozen matrix must contain exactly 16 cases")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or (
        ROOT / "out/research/lane-g-transient-lbvh-hardening"
        / "004-integration-hardening" / stamp
    )
    root.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, str]] = []
    devices: list[dict[str, object]] = []
    for case_id, case in enumerate(cases):
        row, device = run_case(
            executable,
            args.scene,
            case_id,
            case,
            root / f"{case_id:02d}-{case['scenario']}-{case['geometry_class']}",
        )
        rows.append(row)
        devices.append(device)

    summary = {
        "schema_version": 1,
        "plan_version": cfg["plan_version"],
        "git_commit": commit,
        "target_gpu": EXPECTED_GPU,
        "candidate": "hardened-transient-lbvh",
        "case_count": len(rows),
        "all_runs_retained": True,
        "validation": True,
        "all_devices_exact": all(
            device["device"] == EXPECTED_GPU for device in devices
        ),
        "all_semantic_gates_passed": all(
            not semantic_failures(case, row)
            for case, row in zip(cases, rows, strict=True)
        ),
        "formal_timing_gate": "inconclusive-g002-no-safe-decision-valid-protocol",
        "timing_used_for_decision": False,
        "power_clock_manipulation": False,
        "next_step": "g005-deterministic-replay",
    }

    write_csv(root / "g004-raw.csv", rows)
    (root / "g004-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "g004-device.json").write_text(
        json.dumps(
            {"target_gpu": EXPECTED_GPU, "devices": devices},
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (root / "g004-config.json").write_text(
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

    print(f"G004 artifacts: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
