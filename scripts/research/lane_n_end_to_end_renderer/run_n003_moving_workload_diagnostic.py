#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import n003_moving_workload_contract as contract
import run_n003_preflight_v4 as v4runner

ROOT = v4runner.ROOT
EXPECTED_BRANCH = v4runner.EXPECTED_BRANCH
DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-moving-workload-diagnostic-config.json"
)
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-n-end-to-end-renderer/003-n003-moving-workload-diagnostic"
)


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


def run_block(
    block: int,
    order: str,
    root: Path,
    config: dict[str, object],
    binary: Path,
    scene: Path,
) -> dict[str, object]:
    block_root = root / "blocks" / f"block-{block:02d}"
    block_root.mkdir(parents=True, exist_ok=False)
    command = [
        str(binary),
        "--artifact-dir", str(block_root),
        "--scene", str(scene),
        "--source-warmup-frames", str(config["diagnostic"]["source_warmup_frames"]),
        "--start-order", order,
    ]
    if v4runner.is_nixos():
        if not v4runner.VULKAN_WRAPPER.is_file():
            raise contract.ContractError(f"missing Vulkan wrapper: {v4runner.VULKAN_WRAPPER}")
        command = ["bash", str(v4runner.VULKAN_WRAPPER), *command]

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
    (block_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (block_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N003 moving workload diagnostic block {block} failed; artifact retained"
        )

    pair_path = block_root / "n003-moving-workload-pair.json"
    if not pair_path.is_file():
        raise contract.ContractError(
            f"N003 moving workload diagnostic block {block} missing pair artifact"
        )
    pair = json.loads(pair_path.read_text(encoding="utf-8"))
    contract.validate_pair(pair, config, order)
    return {
        "block": block,
        "start_order": order,
        "before": before,
        "after": after,
        "pair": pair,
    }


def run_target(root: Path, config: dict[str, object], binary: Path) -> int:
    commit = v4runner.require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 moving diagnostic binary: {binary}")

    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N003 moving diagnostic scene missing: {scene}")
    actual_scene_sha = v4runner.sha256_file(scene)
    if actual_scene_sha != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 moving diagnostic scene digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    (root / "n003-moving-workload-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    progress: dict[str, object] = {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "state": "running",
        "git_commit": commit,
        "gpu_profile_changes": "forbidden",
        "completed_blocks": [],
    }

    def save_progress() -> None:
        (root / "n003-moving-workload-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    save_progress()
    blocks: list[dict[str, object]] = []
    try:
        for block, order in enumerate(config["diagnostic"]["start_orders"]):
            progress["current_block"] = block
            save_progress()
            result = run_block(block, order, root, config, binary, scene)
            blocks.append(result)
            progress["completed_blocks"].append(block)
            save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    summary_core = contract.summarize(blocks, config)
    raw = {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "git_commit": commit,
        "scene_sha256": actual_scene_sha,
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "blocks": blocks,
    }
    (root / "n003-moving-workload-raw.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    invariant = bool(summary_core["workload_invariant"])
    summary = {
        "schema_version": 1,
        "protocol_version": contract.PROTOCOL_VERSION,
        "phase": "n003-moving-workload-diagnostic",
        "status": "workload-invariant" if invariant else "workload-nondeterministic",
        "git_commit": commit,
        "target_gpu": config["target_gpu"],
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "all_samples_retained": True,
        "sample_exclusion": "none",
        **summary_core,
    }
    (root / "n003-moving-workload-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    progress["state"] = "complete"
    progress.pop("current_block", None)
    save_progress()

    print(f"N003 moving workload diagnostic artifacts: {root}")
    print(f"workload invariant: {invariant}")
    print(summary_core["interpretation"])
    return 0 if invariant else 3


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N003 moving-rigid workload invariance diagnostic"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 moving workload diagnostic contract: PASS")
        return 0

    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / str(config["diagnostic"]["probe_binary"])).resolve()
    )
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 moving workload diagnostic contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
