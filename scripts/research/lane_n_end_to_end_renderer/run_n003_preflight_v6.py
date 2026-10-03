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

import n003_preflight_v6_contract as contract
import run_n003_preflight_v4 as v4runner

ROOT = v4runner.ROOT
EXPECTED_BRANCH = v4runner.EXPECTED_BRANCH
DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-v6-config.json"
)
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-n-end-to-end-renderer/003-n003-preflight-calibration-v6"
)
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip())
    return proc.stdout.strip()


def require_clean_lane_n() -> str:
    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N003 preflight v6 requires {EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N003 preflight v6 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N003 preflight v6 requires a full Git SHA")
    return commit


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
    for path in CAMPAIGN_ROOT.glob("*/n003-preflight-v6-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "pass":
            result.append(path)
    return sorted(result)


def run_micro_pair(
    outer_block: int,
    micro_index: int,
    order: str,
    root: Path,
    config: dict[str, object],
    binary: Path,
    scene: Path,
) -> dict[str, object]:
    micro_root = (
        root / "blocks" / f"block-{outer_block:02d}" / f"micro-{micro_index:02d}"
    )
    micro_root.mkdir(parents=True, exist_ok=False)
    command = [
        str(binary),
        "--artifact-dir", str(micro_root),
        "--scene", str(scene),
        "--source-warmup-frames", str(config["timing_calibration"]["source_warmup_frames"]),
        "--start-order", order,
    ]
    if v4runner.is_nixos():
        if not VULKAN_WRAPPER.is_file():
            raise contract.ContractError(f"missing Vulkan wrapper: {VULKAN_WRAPPER}")
        command = ["bash", str(VULKAN_WRAPPER), *command]

    before = v4runner.host_snapshot()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = v4runner.host_snapshot()
    (micro_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (micro_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N003 preflight v6 block {outer_block} micro {micro_index} failed; "
            "retain every completed micro-pair and do not exclude samples"
        )

    pair_path = micro_root / "n003-timing-pair.json"
    if not pair_path.is_file():
        raise contract.ContractError(
            f"N003 preflight v6 block {outer_block} micro {micro_index} missing pair artifact"
        )
    pair = json.loads(pair_path.read_text(encoding="utf-8"))
    contract.validate_pair(pair, config, order)
    return {
        "micro": micro_index,
        "order": order,
        "before": before,
        "after": after,
        "pair": pair,
    }


def same_device(blocks: list[dict[str, object]]) -> bool:
    keys = ("name", "driver_name", "driver_info", "api_version", "timestamp_period_ns")
    devices: list[dict[str, object]] = []
    for block in blocks:
        for micro in block["micro_pairs"]:
            devices.append(micro["pair"]["device"])
    if not devices:
        return False
    first = devices[0]
    return all(all(device.get(key) == first.get(key) for key in keys) for device in devices)


def run_target(root: Path, config: dict[str, object], binary: Path) -> int:
    commit = require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 preflight binary: {binary}")
    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in existing)
        raise contract.ContractError(
            "N003 preflight v6 completed PASS rerun budget is zero; existing PASS: "
            + joined
        )

    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N003 preflight v6 scene missing: {scene}")
    actual_scene_sha = v4runner.sha256_file(scene)
    if actual_scene_sha != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 preflight v6 scene digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    (root / "n003-preflight-v6-config.json").write_text(
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
        "schema_version": 6,
        "protocol_version": contract.PROTOCOL_VERSION,
        "state": "running",
        "git_commit": commit,
        "completed_outer_blocks": [],
        "completed_micro_pairs": [],
        "gpu_profile_changes": "forbidden",
    }

    def save_progress() -> None:
        (root / "n003-preflight-v6-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    save_progress()
    blocks: list[dict[str, object]] = []
    try:
        outer_orders = list(config["timing_calibration"]["outer_start_orders"])
        micro_count = int(config["timing_calibration"]["micro_pairs_per_block"])
        settle = float(
            config["timing_calibration"]["settle_seconds_between_outer_blocks"]
        )
        for block_index, outer_order in enumerate(outer_orders):
            if settle > 0.0:
                time.sleep(settle)
            progress["current_outer_block"] = block_index
            save_progress()
            micros: list[dict[str, object]] = []
            orders = contract.micro_orders(outer_order, micro_count)
            for micro_index, order in enumerate(orders):
                progress["current_micro_pair"] = micro_index
                save_progress()
                result = run_micro_pair(
                    block_index, micro_index, order, root, config, binary, scene
                )
                micros.append(result)
                progress["completed_micro_pairs"].append(
                    {"block": block_index, "micro": micro_index}
                )
                save_progress()
            blocks.append(
                {
                    "block": block_index,
                    "outer_start_order": outer_order,
                    "micro_pairs": micros,
                }
            )
            progress["completed_outer_blocks"].append(block_index)
            progress.pop("current_micro_pair", None)
            save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    if not same_device(blocks):
        raise contract.ContractError("N003 preflight v6 device provenance changed across micro-pairs")

    timing = contract.summarize(blocks, config)
    raw = {
        "schema_version": 6,
        "protocol_version": contract.PROTOCOL_VERSION,
        "measurement_probe_protocol": contract.PROBE_PROTOCOL_VERSION,
        "git_commit": commit,
        "scene_sha256": actual_scene_sha,
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "blocks": blocks,
    }
    (root / "n003-preflight-v6-raw.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    suitable = bool(timing["timing_suitable_for_n003_formal_claims"])
    summary = {
        "schema_version": 6,
        "protocol_version": contract.PROTOCOL_VERSION,
        "measurement_probe_protocol": contract.PROBE_PROTOCOL_VERSION,
        "phase": "n003-preflight-calibration",
        "status": "pass" if suitable else "timing-unsuitable",
        "git_commit": commit,
        "target_gpu": config["target_gpu"],
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "all_micro_pairs_retained": True,
        "sample_exclusion": "none",
        "completed_campaign_rerun_budget": 0,
        "quality_gate": config["quality_interpretation"],
        "timing": timing,
        "n003_proper_allowed": suitable,
    }
    (root / "n003-preflight-v6-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    progress["state"] = "complete"
    progress.pop("current_outer_block", None)
    progress.pop("current_micro_pair", None)
    save_progress()

    worst_stage = timing["worst_stage_diagnostic"]
    print(f"N003 preflight v6 artifacts: {root}")
    print(f"worst replicated-control noise: {timing['worst_noise_fraction'] * 100.0:.3f}%")
    print(f"worst p95 block effect: {timing['worst_p95_block_effect_fraction'] * 100.0:.3f}%")
    print(
        "derived N003 material-change threshold: "
        f"{timing['derived_material_change_threshold_fraction'] * 100.0:.1f}%"
    )
    print(
        "worst stage diagnostic: "
        f"{worst_stage['scenario']} / {worst_stage['stage']} / "
        f"p95-block={worst_stage['p95_block_effect_fraction'] * 100.0:.3f}%"
    )
    print(f"N003 preflight v6 status: {summary['status']}")
    return 0 if suitable else 3


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N003 preflight v6 replicated-median timing calibration"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 preflight v6 GPU-independent contract validation: PASS")
        return 0
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
        print(f"N003 preflight v6 contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
