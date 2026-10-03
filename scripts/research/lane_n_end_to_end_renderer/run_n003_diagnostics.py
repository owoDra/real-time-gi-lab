#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import n003_comparison_contract as contract
import run_n003_preflight_v4 as common

ROOT = common.ROOT
EXPECTED_BRANCH = common.EXPECTED_BRANCH
DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-comparison-config.json"
)
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-n-end-to-end-renderer/003-n003-diagnostics"
)
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
PROTOCOL_VERSION = "current-vs-vanilla-diagnostics-v1"
CPU_FIELDS = (
    "dynamic_update_wall",
    "geometry_prepare_cpu",
    "geometry_transfer_wall",
    "instance_transfer_wall",
    "membership_update_cpu",
    "hierarchy_refit_cpu",
    "hierarchy_rebuild_cpu",
    "hierarchy_occupancy_cpu",
    "packing_cpu",
    "software_bvh_rebuild_cpu",
)
HOST_FIELDS = (
    "scene_surface_capacity",
    "scene_triangle_capacity",
    "dynamic_selection_capacity",
    "candidate_structure_capacity",
    "renderer_owned_total",
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args), cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip())
    return proc.stdout.strip()


def require_clean_lane_n() -> str:
    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N003 diagnostics requires {EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N003 diagnostics requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N003 diagnostics requires a full Git SHA")
    return commit


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


def finite_nonnegative(value: object, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise contract.ContractError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise contract.ContractError(f"{label} must be finite and non-negative")
    return result


def nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise contract.ContractError(f"{label} must be a non-negative integer")
    return value


def validate_artifact(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    path = root / "n003-diagnostics.json"
    if not path.is_file():
        raise contract.ContractError("N003 diagnostics artifact is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or payload.get("protocol_version") != PROTOCOL_VERSION:
        raise contract.ContractError("N003 diagnostics protocol mismatch")
    if payload.get("formal_decision_axis") is not False:
        raise contract.ContractError("N003 diagnostics must remain non-formal")
    if payload.get("source_warmup_frames") != config["timing"]["source_warmup_frames"]:
        raise contract.ContractError("N003 diagnostics warm-up count changed")
    scope = payload.get("host_memory_scope")
    if scope != (
        "renderer-owned-vector-and-BVH-capacity-only; "
        "allocator-bookkeeping-and-opaque-driver-host-memory-excluded"
    ):
        raise contract.ContractError("N003 diagnostics host-memory scope changed")

    device = payload.get("device")
    if not isinstance(device, dict) or device.get("name") != config["target_gpu"]:
        raise contract.ContractError("N003 diagnostics target GPU mismatch")
    for key in ("driver_name", "driver_info"):
        if not isinstance(device.get(key), str) or not device[key]:
            raise contract.ContractError(f"N003 diagnostics device.{key} missing")
    nonnegative_int(device.get("api_version"), "device.api_version")
    if finite_nonnegative(device.get("timestamp_period_ns"), "device.timestamp_period_ns") <= 0.0:
        raise contract.ContractError("N003 diagnostics timestamp period must be positive")

    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, dict) or list(scenarios) != contract.EXPECTED_SCENARIOS:
        raise contract.ContractError("N003 diagnostics scenario order changed")
    for scenario in contract.EXPECTED_SCENARIOS:
        entry = scenarios[scenario]
        if not isinstance(entry, dict) or set(entry) != {"A", "B"}:
            raise contract.ContractError(f"N003 diagnostics role set changed in {scenario}")
        for role in ("A", "B"):
            sample = entry[role]
            if not isinstance(sample, dict):
                raise contract.ContractError(f"N003 diagnostics sample missing: {scenario}/{role}")
            cpu = sample.get("cpu_wall_diagnostic_us")
            host = sample.get("host_memory_bytes")
            if not isinstance(cpu, dict) or set(cpu) != set(CPU_FIELDS):
                raise contract.ContractError(f"N003 diagnostics CPU fields changed: {scenario}/{role}")
            if not isinstance(host, dict) or set(host) != set(HOST_FIELDS):
                raise contract.ContractError(f"N003 diagnostics host fields changed: {scenario}/{role}")
            for field in CPU_FIELDS:
                finite_nonnegative(cpu[field], f"{scenario}/{role}/{field}")
            for field in HOST_FIELDS:
                nonnegative_int(host[field], f"{scenario}/{role}/{field}")
            expected_total = sum(
                host[field]
                for field in HOST_FIELDS
                if field != "renderer_owned_total"
            )
            if host["renderer_owned_total"] != expected_total:
                raise contract.ContractError(
                    f"N003 diagnostics host total mismatch: {scenario}/{role}"
                )
    return payload


def run_target(root: Path, config: dict[str, Any], binary: Path) -> int:
    commit = require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 diagnostics binary: {binary}")
    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N003 diagnostics scene missing: {scene}")
    scene_sha = common.sha256_file(scene)
    if scene_sha != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 diagnostics scene digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    command = [
        str(binary),
        "--artifact-dir", str(root),
        "--scene", str(scene),
        "--source-warmup-frames", str(config["timing"]["source_warmup_frames"]),
    ]
    if common.is_nixos():
        if not VULKAN_WRAPPER.is_file():
            raise contract.ContractError(f"missing Vulkan wrapper: {VULKAN_WRAPPER}")
        command = ["bash", str(VULKAN_WRAPPER), *command]

    proc = subprocess.run(
        command, cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    (root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError("N003 diagnostics target failed; retain artifact")

    payload = validate_artifact(root, config)
    provenance = {
        "schema_version": 1,
        "protocol_version": PROTOCOL_VERSION,
        "git": {
            "branch": EXPECTED_BRANCH,
            "commit": commit,
            "dirty": False,
        },
        "scene_sha256": scene_sha,
        "target_gpu": config["target_gpu"],
        "device": payload["device"],
        "formal_decision_axis": False,
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "host_memory_scope": payload["host_memory_scope"],
    }
    (root / "n003-diagnostics-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"N003 diagnostics artifacts: {root}")
    print("N003 CPU wall / host-memory diagnostics: PASS (non-formal)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N003 non-formal CPU wall and host-memory diagnostics"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 diagnostics GPU-independent contract validation: PASS")
        return 0
    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / "build/phos-n003-diagnostics").resolve()
    )
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 diagnostics contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
