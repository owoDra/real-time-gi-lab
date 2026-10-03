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
    / "out/research/lane-n-end-to-end-renderer/003-n003-current-vs-vanilla"
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
            f"N003 comparison requires {EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N003 comparison requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N003 comparison requires a full Git SHA")
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
    for path in CAMPAIGN_ROOT.glob("*/n003-comparison-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "complete":
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
        "--source-warmup-frames", str(config["timing"]["source_warmup_frames"]),
        "--start-order", order,
    ]
    if common.is_nixos():
        if not VULKAN_WRAPPER.is_file():
            raise contract.ContractError(f"missing Vulkan wrapper: {VULKAN_WRAPPER}")
        command = ["bash", str(VULKAN_WRAPPER), *command]

    before = common.host_snapshot()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = common.host_snapshot()
    (micro_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (micro_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N003 comparison block {outer_block} micro {micro_index} failed; "
            "retain every completed pair and do not exclude samples"
        )

    pair_path = micro_root / "n003-comparison-pair.json"
    if not pair_path.is_file():
        raise contract.ContractError(
            f"N003 comparison block {outer_block} micro {micro_index} missing pair artifact"
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
    devices: list[dict[str, object]] = []
    for block in blocks:
        for micro in block["micro_pairs"]:
            devices.append(micro["pair"]["device"])
    if not devices:
        return False
    keys = ("name", "driver_name", "driver_info", "api_version", "timestamp_period_ns")
    first = devices[0]
    return all(all(device.get(key) == first.get(key) for key in keys) for device in devices)


def run_target(root: Path, config: dict[str, object], binary: Path) -> int:
    commit = require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 comparison binary: {binary}")
    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in existing)
        raise contract.ContractError(
            "N003 comparison completed campaign rerun budget is zero; existing campaign: "
            + joined
        )

    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N003 comparison scene missing: {scene}")
    actual_scene_sha = common.sha256_file(scene)
    if actual_scene_sha != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 comparison scene digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    (root / "n003-comparison-config.json").write_text(
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
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "state": "running",
        "git_commit": commit,
        "completed_outer_blocks": [],
        "completed_micro_pairs": [],
        "gpu_profile_changes": "forbidden",
    }

    def save_progress() -> None:
        (root / "n003-comparison-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    save_progress()
    blocks: list[dict[str, object]] = []
    try:
        outer_orders = list(config["timing"]["outer_start_orders"])
        micro_count = int(config["timing"]["micro_pairs_per_block"])
        settle = float(config["timing"]["settle_seconds_between_outer_blocks"])
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
        raise contract.ContractError("N003 comparison device provenance changed across pairs")

    comparison = contract.summarize(blocks, config)
    for scenario, result in comparison["per_scenario"].items():
        for role in ("A", "B"):
            for field, memory in result["memory"][role].items():
                if not memory["invariant"]:
                    raise contract.ContractError(
                        f"N003 comparison memory changed across campaign: {scenario}/{role}/{field}"
                    )

    raw = {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "git_commit": commit,
        "scene_sha256": actual_scene_sha,
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "blocks": blocks,
    }
    (root / "n003-comparison-raw.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "phase": "n003-current-vs-vanilla",
        "status": "complete",
        "git_commit": commit,
        "target_gpu": config["target_gpu"],
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "all_micro_pairs_retained": True,
        "sample_exclusion": "none",
        "completed_campaign_rerun_budget": 0,
        "comparison": comparison,
        "moving_rigid_timing": "measurement-limited-descriptive-only",
        "aggregate_winner": None,
        "quality_reference_phase_required": True,
    }
    (root / "n003-comparison-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    progress["state"] = "complete"
    progress.pop("current_outer_block", None)
    progress.pop("current_micro_pair", None)
    save_progress()

    print(f"N003 comparison artifacts: {root}")
    for scenario in contract.EXPECTED_SCENARIOS:
        result = comparison["per_scenario"][scenario]
        gi = result["axes"]["complete_gi_gpu"]
        renderer = result["axes"]["complete_renderer_gpu"]
        print(
            f"{scenario}: GI B/A={gi['median_ratio_vanilla_over_current']:.4f} "
            f"renderer B/A={renderer['median_ratio_vanilla_over_current']:.4f} "
            f"status={result['timing_status']}"
        )
    print("N003 comparison timing/memory campaign: COMPLETE")
    print("N003 quality/reference evidence is still required before final N003 decision")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N003 current-vs-vanilla replicated comparison"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 comparison GPU-independent contract validation: PASS")
        return 0
    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / str(config["timing"]["probe_binary"])).resolve()
    )
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 comparison contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
