#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import n003_preflight_v4_contract as contract

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-n-end-to-end-renderer"
DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-v4-config.json"
)
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-n-end-to-end-renderer/003-n003-preflight-calibration-v4"
)
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip())
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def host_snapshot() -> dict[str, object]:
    try:
        load = list(os.getloadavg())
    except OSError:
        load = [None, None, None]
    available = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                available = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    return {
        "loadavg_1m": load[0],
        "loadavg_5m": load[1],
        "loadavg_15m": load[2],
        "mem_available_bytes": available,
        "monotonic_ns": time.monotonic_ns(),
    }


def is_nixos() -> bool:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key == "ID":
                return value.strip().strip('"\'') == "nixos"
    except OSError:
        pass
    return False


def require_clean_lane_n() -> str:
    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N003 preflight v4 requires {EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N003 preflight v4 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N003 preflight v4 requires a full Git SHA")
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
    result = []
    for path in CAMPAIGN_ROOT.glob("*/n003-preflight-v4-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "pass":
            result.append(path)
    return sorted(result)


def same_device(blocks: list[dict[str, object]]) -> bool:
    if not blocks:
        return False
    keys = ("name", "driver_name", "driver_info", "api_version", "timestamp_period_ns")
    first = blocks[0]["pair"]["device"]
    return all(
        all(block["pair"]["device"].get(key) == first.get(key) for key in keys)
        for block in blocks
    )


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
        "--source-warmup-frames", str(config["timing_calibration"]["source_warmup_frames"]),
        "--start-order", order,
    ]
    if is_nixos():
        if not VULKAN_WRAPPER.is_file():
            raise contract.ContractError(f"missing Vulkan wrapper: {VULKAN_WRAPPER}")
        command = ["bash", str(VULKAN_WRAPPER), *command]

    before = host_snapshot()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = host_snapshot()
    (block_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (block_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N003 preflight v4 block {block} failed; retain artifact and do not exclude it"
        )
    pair_path = block_root / "n003-timing-pair.json"
    if not pair_path.is_file():
        raise contract.ContractError(f"N003 preflight v4 block {block} missing pair artifact")
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
    commit = require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 preflight v4 binary: {binary}")
    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in existing)
        raise contract.ContractError(
            "N003 preflight v4 completed PASS rerun budget is zero; existing PASS: " + joined
        )

    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N003 preflight v4 scene missing: {scene}")
    actual_scene_sha = sha256_file(scene)
    if actual_scene_sha != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 preflight v4 scene digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    (root / "n003-preflight-v4-config.json").write_text(
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
        "schema_version": 4,
        "protocol_version": contract.PROTOCOL_VERSION,
        "state": "running",
        "git_commit": commit,
        "completed_pair_blocks": [],
    }

    def save_progress() -> None:
        (root / "n003-preflight-v4-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    save_progress()
    blocks: list[dict[str, object]] = []
    try:
        orders = list(config["timing_calibration"]["start_orders"])
        settle = float(config["timing_calibration"]["settle_seconds_between_pairs"])
        for block, order in enumerate(orders):
            progress["current_pair_block"] = block
            save_progress()
            if settle > 0.0:
                time.sleep(settle)
            result = run_block(block, order, root, config, binary, scene)
            blocks.append(result)
            progress["completed_pair_blocks"].append(block)
            save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    if not same_device(blocks):
        raise contract.ContractError("N003 preflight v4 device provenance changed across blocks")

    timing = contract.summarize(blocks, config)
    raw = {
        "schema_version": 4,
        "protocol_version": contract.PROTOCOL_VERSION,
        "git_commit": commit,
        "scene_sha256": actual_scene_sha,
        "blocks": blocks,
    }
    (root / "n003-preflight-v4-raw.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    suitable = bool(timing["timing_suitable_for_n003_formal_claims"])
    summary = {
        "schema_version": 4,
        "protocol_version": contract.PROTOCOL_VERSION,
        "phase": "n003-preflight-calibration",
        "status": "pass" if suitable else "timing-unsuitable",
        "git_commit": commit,
        "target_gpu": config["target_gpu"],
        "all_samples_retained": True,
        "sample_exclusion": "none",
        "completed_campaign_rerun_budget": 0,
        "quality_gate": config["quality_interpretation"],
        "timing": timing,
        "n003_proper_allowed": suitable,
    }
    (root / "n003-preflight-v4-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    progress["state"] = "complete"
    progress.pop("current_pair_block", None)
    save_progress()

    worst_stage = timing["worst_stage_diagnostic"]
    print(f"N003 preflight v4 artifacts: {root}")
    print(f"worst paired-control noise: {timing['worst_noise_fraction'] * 100.0:.3f}%")
    print(f"worst p95 pair effect: {timing['worst_p95_pair_effect_fraction'] * 100.0:.3f}%")
    print(f"derived N003 material-change threshold: {timing['derived_material_change_threshold_fraction'] * 100.0:.1f}%")
    print(
        "worst active stage diagnostic: "
        f"{worst_stage['scenario']} / {worst_stage['stage']} / "
        f"p95={worst_stage['p95_pair_effect_fraction'] * 100.0:.3f}%"
    )
    print(f"N003 preflight v4 status: {summary['status']}")
    return 0 if suitable else 3


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane N N003 preflight v4 timing calibration")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 preflight v4 GPU-independent contract validation: PASS")
        return 0
    binary = args.binary.resolve() if args.binary else (
        ROOT / str(config["timing_calibration"]["probe_binary"])
    ).resolve()
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 preflight v4 contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
