#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import n003_preflight_v5_contract as contract
import run_n003_preflight_v4 as v4runner

ROOT = v4runner.ROOT
EXPECTED_BRANCH = v4runner.EXPECTED_BRANCH
DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-v5-config.json"
)
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-n-end-to-end-renderer/003-n003-preflight-calibration-v5"
)


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


def completed_campaigns(current_root: Path) -> list[Path]:
    if not CAMPAIGN_ROOT.exists():
        return []
    result: list[Path] = []
    for path in CAMPAIGN_ROOT.glob("*/n003-preflight-v5-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "pass":
            result.append(path)
    return sorted(result)


def _candidate_power_nodes() -> list[Path]:
    explicit = os.environ.get("PHOS_AMDGPU_DPM_NODE")
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise contract.ContractError(
                f"PHOS_AMDGPU_DPM_NODE does not name a readable file: {path}"
            )
        return [path.resolve()]

    found: dict[str, Path] = {}
    for node in Path("/sys/class/drm").glob(
        "card*/device/power_dpm_force_performance_level"
    ):
        vendor = node.parent / "vendor"
        try:
            if vendor.read_text(encoding="utf-8").strip().lower() != "0x1002":
                continue
        except OSError:
            continue
        resolved = node.resolve()
        found[str(resolved)] = resolved
    return sorted(found.values(), key=str)


def discover_power_node() -> Path:
    nodes = _candidate_power_nodes()
    if len(nodes) != 1:
        joined = ", ".join(str(path) for path in nodes) or "none"
        raise contract.ContractError(
            "N003 preflight v5 needs exactly one AMDGPU DPM node; "
            f"found {len(nodes)} ({joined}). Set PHOS_AMDGPU_DPM_NODE explicitly if needed."
        )
    return nodes[0]


def _read_optional(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def performance_snapshot(node: Path, config: dict[str, object]) -> dict[str, object]:
    level = _read_optional(node)
    if level is None:
        raise contract.ContractError(f"could not read AMDGPU performance level: {node}")
    parent = node.parent
    names = config["timing_calibration"]["gpu_performance_state"]["record_clock_state_nodes"]
    clocks = {name: _read_optional(parent / str(name)) for name in names}
    return {
        "node": str(node),
        "level": level,
        "clock_state": clocks,
    }


def require_profile_peak(
    node: Path,
    config: dict[str, object],
    label: str,
) -> dict[str, object]:
    snapshot = performance_snapshot(node, config)
    required = str(
        config["timing_calibration"]["gpu_performance_state"]["required_level"]
    )
    if snapshot["level"] != required:
        raise contract.ContractError(
            f"N003 preflight v5 requires AMDGPU {required!r} at {label}; "
            f"read {snapshot['level']!r} from {node}"
        )
    return snapshot


def run_target(root: Path, config: dict[str, object], binary: Path) -> int:
    commit = v4runner.require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 preflight binary: {binary}")

    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in existing)
        raise contract.ContractError(
            "N003 preflight v5 completed PASS rerun budget is zero; existing PASS: "
            + joined
        )

    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N003 preflight v5 scene missing: {scene}")
    actual_scene_sha = v4runner.sha256_file(scene)
    if actual_scene_sha != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 preflight v5 scene digest mismatch")

    node = discover_power_node()
    campaign_start_profile = require_profile_peak(node, config, "campaign start")

    root.mkdir(parents=True, exist_ok=True)
    (root / "n003-preflight-v5-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        proc = subprocess.run(
            [vulkaninfo, "--summary"], cwd=ROOT, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        (root / "vulkaninfo-summary.txt").write_text(proc.stdout, encoding="utf-8")

    progress: dict[str, object] = {
        "schema_version": 5,
        "protocol_version": contract.PROTOCOL_VERSION,
        "state": "running",
        "git_commit": commit,
        "completed_pair_blocks": [],
        "gpu_performance_level": campaign_start_profile["level"],
        "gpu_performance_node": campaign_start_profile["node"],
    }

    def save_progress() -> None:
        (root / "n003-preflight-v5-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    save_progress()
    normalized = contract.normalized_v4_config(config)
    blocks: list[dict[str, object]] = []
    try:
        orders = list(config["timing_calibration"]["start_orders"])
        settle = float(config["timing_calibration"]["settle_seconds_between_pairs"])
        for block, order in enumerate(orders):
            progress["current_pair_block"] = block
            save_progress()
            if settle > 0.0:
                time.sleep(settle)
            profile_before = require_profile_peak(node, config, f"block {block} before")
            result = v4runner.run_block(
                block, order, root, normalized, binary, scene
            )
            profile_after = require_profile_peak(node, config, f"block {block} after")
            result["gpu_performance_before"] = profile_before
            result["gpu_performance_after"] = profile_after
            blocks.append(result)
            progress["completed_pair_blocks"].append(block)
            save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    if not v4runner.same_device(blocks):
        raise contract.ContractError("N003 preflight v5 device provenance changed across blocks")

    campaign_end_profile = require_profile_peak(node, config, "campaign end")
    timing = contract.summarize(blocks, config)
    raw = {
        "schema_version": 5,
        "protocol_version": contract.PROTOCOL_VERSION,
        "measurement_probe_protocol": contract.PROBE_PROTOCOL_VERSION,
        "git_commit": commit,
        "scene_sha256": actual_scene_sha,
        "gpu_performance_state": {
            "campaign_start": campaign_start_profile,
            "campaign_end": campaign_end_profile,
        },
        "blocks": blocks,
    }
    (root / "n003-preflight-v5-raw.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    suitable = bool(timing["timing_suitable_for_n003_formal_claims"])
    summary = {
        "schema_version": 5,
        "protocol_version": contract.PROTOCOL_VERSION,
        "measurement_probe_protocol": contract.PROBE_PROTOCOL_VERSION,
        "phase": "n003-preflight-calibration",
        "status": "pass" if suitable else "timing-unsuitable",
        "git_commit": commit,
        "target_gpu": config["target_gpu"],
        "gpu_performance_state": {
            "node": str(node),
            "required_level": "profile_peak",
            "campaign_start_level": campaign_start_profile["level"],
            "campaign_end_level": campaign_end_profile["level"],
        },
        "all_samples_retained": True,
        "sample_exclusion": "none",
        "completed_campaign_rerun_budget": 0,
        "quality_gate": config["quality_interpretation"],
        "timing": timing,
        "n003_proper_allowed": suitable,
    }
    (root / "n003-preflight-v5-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    progress["state"] = "complete"
    progress.pop("current_pair_block", None)
    save_progress()

    worst_stage = timing["worst_stage_diagnostic"]
    print(f"N003 preflight v5 artifacts: {root}")
    print(f"AMDGPU performance level: {campaign_start_profile['level']}")
    print(f"worst paired-control noise: {timing['worst_noise_fraction'] * 100.0:.3f}%")
    print(f"worst p95 pair effect: {timing['worst_p95_pair_effect_fraction'] * 100.0:.3f}%")
    print(f"derived N003 material-change threshold: {timing['derived_material_change_threshold_fraction'] * 100.0:.1f}%")
    print(
        "worst stage diagnostic: "
        f"{worst_stage['scenario']} / {worst_stage['stage']} / "
        f"p95={worst_stage['p95_pair_effect_fraction'] * 100.0:.3f}%"
    )
    print(f"N003 preflight v5 status: {summary['status']}")
    return 0 if suitable else 3


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N003 preflight v5 clock-pinned timing calibration"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "profile-check", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 preflight v5 GPU-independent contract validation: PASS")
        return 0
    if args.phase == "profile-check":
        node = discover_power_node()
        snapshot = performance_snapshot(node, config)
        print(f"AMDGPU DPM node: {node}")
        print(f"AMDGPU performance level: {snapshot['level']}")
        required = config["timing_calibration"]["gpu_performance_state"]["required_level"]
        return 0 if snapshot["level"] == required else 3

    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / str(config["timing_calibration"]["probe_binary"])).resolve()
    )
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 preflight v5 contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
