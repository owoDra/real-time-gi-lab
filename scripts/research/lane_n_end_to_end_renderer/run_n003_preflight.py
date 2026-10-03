#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import n001_contract as image_contract
import n003_preflight_contract as contract

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-n-end-to-end-renderer"
DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/003-n003-preflight-calibration-config.json"
)
DEFAULT_CORE_BINARY = ROOT / "build/phos-n002"
DEFAULT_TOPOLOGY_BINARY = ROOT / "build/phos-n002-topology"
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-n-end-to-end-renderer/003-n003-preflight-calibration"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise contract.ContractError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value).resolve()
    return (CAMPAIGN_ROOT / "manual").resolve()


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def require_clean_lane_n() -> str:
    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N003 preflight requires {EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N003 preflight requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N003 preflight requires a full Git commit SHA")
    return commit


def same_device(devices: list[dict[str, object]]) -> bool:
    if not devices:
        return False
    keys = (
        "name",
        "driver_name",
        "driver_info",
        "api_version",
        "timestamp_period_ns",
    )
    first = devices[0]
    return all(
        all(device.get(key) == first.get(key) for key in keys)
        for device in devices
    )


def completed_campaigns(current_root: Path) -> list[Path]:
    completed: list[Path] = []
    if not CAMPAIGN_ROOT.exists():
        return completed
    for summary in CAMPAIGN_ROOT.glob("*/n003-preflight-summary.json"):
        if summary.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "pass" and payload.get("protocol_version") == "paired-control-v2":
            completed.append(summary)
    return sorted(completed)


def run_member(
    block: int,
    role: str,
    pair_root: Path,
    config: dict[str, object],
    core_binary: Path,
    topology_binary: Path,
    expected_commit: str,
) -> dict[str, object]:
    member_root = pair_root / role
    member_root.mkdir(parents=True, exist_ok=False)

    runner = ROOT / str(config["baseline"]["runner"])
    baseline_config = ROOT / str(config["baseline"]["config"])
    command = [
        sys.executable,
        str(runner),
        "--phase",
        "target",
        "--artifact-dir",
        str(member_root),
        "--config",
        str(baseline_config),
        "--core-binary",
        str(core_binary),
        "--topology-binary",
        str(topology_binary),
    ]

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
    (member_root / "preflight-stdout.log").write_text(proc.stdout, encoding="utf-8")
    (member_root / "preflight-stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} failed; retain artifact"
        )

    provenance_path = member_root / "n002-provenance.json"
    summary_path = member_root / "n002-validation-summary.json"
    if not provenance_path.is_file() or not summary_path.is_file():
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} is missing N002 artifacts"
        )
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    validation = json.loads(summary_path.read_text(encoding="utf-8"))
    if validation.get("status") != "pass" or validation.get("n002_complete") is not True:
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} failed N002 completion gate"
        )
    git_info = provenance.get("git")
    if not isinstance(git_info, dict) or git_info.get("commit") != expected_commit:
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} Git provenance changed"
        )
    if git_info.get("dirty") is not False:
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} used a dirty worktree"
        )

    raw_frames = provenance.get("frames")
    raw_metrics = validation.get("frame_metrics")
    if not isinstance(raw_frames, list) or not isinstance(raw_metrics, list):
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} frame payload malformed"
        )
    if len(raw_frames) != len(contract.EXPECTED_SCENARIOS) or len(raw_metrics) != len(contract.EXPECTED_SCENARIOS):
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} frame count mismatch"
        )

    timing: dict[str, object] = {}
    quality: dict[str, object] = {}
    for index, scenario in enumerate(contract.EXPECTED_SCENARIOS):
        frame = raw_frames[index]
        metric = raw_metrics[index]
        if frame.get("scenario") != scenario or metric.get("scenario") != scenario:
            raise contract.ContractError(
                f"N003 preflight block {block} role {role} scenario mismatch at {index}"
            )
        timing_payload = frame.get("timing_us")
        if not isinstance(timing_payload, dict):
            raise contract.ContractError(
                f"N003 preflight block {block} role {role} timing payload malformed"
            )
        timing[scenario] = {
            axis: timing_payload.get(axis) for axis in contract.TIMING_TOTALS
        }

        output_path = member_root / str(frame.get("output_hdr"))
        reference_path = member_root / str(frame.get("reference_hdr"))
        output = image_contract.read_pfm(output_path)
        reference = image_contract.read_pfm(reference_path)
        scale_aware = contract.scale_aware_affected_pixel_fraction(
            output, reference, config
        )
        quality[scenario] = {
            "rgb_rms_error": metric.get("rgb_rms_error"),
            "p99_abs_luminance_error": metric.get("p99_abs_luminance_error"),
            "scale_aware_affected_pixel_fraction": scale_aware,
            "legacy_affected_pixel_fraction": metric.get("affected_pixel_fraction"),
        }

    device = provenance.get("device")
    if not isinstance(device, dict) or device.get("name") != config["target_gpu"]:
        raise contract.ContractError(
            f"N003 preflight block {block} role {role} ran on the wrong GPU"
        )

    return {
        "role": role,
        "git_commit": expected_commit,
        "device": device,
        "before": before,
        "after": after,
        "timing": timing,
        "quality": quality,
        "n002_playback_sha256": provenance.get("playback_sha256"),
        "n002_scene_sha256": provenance.get("scene_sha256"),
    }


def run_pair(
    block: int,
    root: Path,
    config: dict[str, object],
    core_binary: Path,
    topology_binary: Path,
    expected_commit: str,
) -> dict[str, object]:
    pair_root = root / "pairs" / f"pair-{block:02d}"
    pair_root.mkdir(parents=True, exist_ok=False)
    pair_before = host_snapshot()
    a = run_member(
        block, "A", pair_root, config, core_binary, topology_binary, expected_commit
    )
    b = run_member(
        block, "B", pair_root, config, core_binary, topology_binary, expected_commit
    )
    pair_after = host_snapshot()
    return {
        "block": block,
        "comparison": "current-vs-current-control",
        "pair_before": pair_before,
        "A": a,
        "B": b,
        "pair_after": pair_after,
    }


def run_target(
    root: Path,
    config: dict[str, object],
    core_binary: Path,
    topology_binary: Path,
) -> int:
    commit = require_clean_lane_n()
    if not core_binary.is_file() or not topology_binary.is_file():
        raise contract.ContractError(
            "N003 preflight requires built phos-n002 and phos-n002-topology binaries"
        )

    completed = completed_campaigns(root)
    if completed:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in completed)
        raise contract.ContractError(
            "N003 paired-control preflight completed-campaign rerun budget is zero; existing PASS: "
            + joined
        )

    root.mkdir(parents=True, exist_ok=True)
    (root / "n003-preflight-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    progress: dict[str, object] = {
        "schema_version": 2,
        "protocol_version": config["protocol_version"],
        "state": "running",
        "git_commit": commit,
        "completed_pair_blocks": [],
    }

    def save_progress() -> None:
        (root / "n003-preflight-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    save_progress()
    blocks: list[dict[str, object]] = []
    try:
        block_count = int(config["timing_calibration"]["fresh_process_pair_blocks"])
        settle = float(config["timing_calibration"]["settle_seconds_between_pairs"])
        for block in range(block_count):
            progress["current_pair_block"] = block
            save_progress()
            if settle > 0.0:
                time.sleep(settle)
            result = run_pair(
                block,
                root,
                config,
                core_binary,
                topology_binary,
                commit,
            )
            blocks.append(result)
            progress["completed_pair_blocks"].append(block)
            save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    members = [block[role] for block in blocks for role in ("A", "B")]
    devices = [member["device"] for member in members]
    if not same_device(devices):
        raise contract.ContractError(
            "N003 preflight device/driver/API provenance changed during campaign"
        )
    playback = {member["n002_playback_sha256"] for member in members}
    scene = {member["n002_scene_sha256"] for member in members}
    if len(playback) != 1 or len(scene) != 1:
        raise contract.ContractError(
            "N003 preflight N002 playback/scene provenance changed during campaign"
        )

    timing = contract.summarize_timing(blocks, config)
    quality = contract.summarize_quality(blocks, config)
    raw = {
        "schema_version": 2,
        "protocol_version": config["protocol_version"],
        "git_commit": commit,
        "config_sha256": canonical_sha256(config),
        "blocks": blocks,
    }
    (root / "n003-preflight-raw.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    status = "pass" if timing["timing_suitable_for_n003_formal_claims"] else "timing-unsuitable"
    summary = {
        "schema_version": 2,
        "protocol_version": config["protocol_version"],
        "status": status,
        "phase": "n003-preflight-calibration",
        "git_commit": commit,
        "config_sha256": raw["config_sha256"],
        "target_gpu": config["target_gpu"],
        "sample_exclusion": "none",
        "all_samples_retained": True,
        "completed_campaign_rerun_budget": 0,
        "v1_failure_retained": config["source_of_truth"]["v1_result"],
        "timing": timing,
        "quality": quality,
        "n003_proper_allowed": status == "pass",
    }
    (root / "n003-preflight-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    progress["state"] = "complete"
    progress.pop("current_pair_block", None)
    save_progress()

    print(f"N003 paired-control preflight artifacts: {root}")
    print(
        "robust paired timing noise: "
        f"{timing['worst_noise_fraction'] * 100.0:.3f}%"
    )
    print(
        "worst p95 A/A pair effect: "
        f"{timing['worst_p95_pair_effect_fraction'] * 100.0:.3f}%"
    )
    print(
        "derived N003 material-change threshold: "
        f"{timing['derived_material_change_threshold_fraction'] * 100.0:.1f}%"
    )
    print(
        "scale-aware quality signal: "
        f"{quality['scale_aware_campaign_has_signal']}"
    )
    print(f"N003 preflight status: {status}")
    return 0 if status == "pass" else 3


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N003 paired-control preflight calibration"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--core-binary", type=Path, default=DEFAULT_CORE_BINARY)
    parser.add_argument(
        "--topology-binary", type=Path, default=DEFAULT_TOPOLOGY_BINARY
    )
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 paired-control preflight GPU-independent contract validation: PASS")
        return 0
    return run_target(
        artifact_dir(args.artifact_dir),
        config,
        args.core_binary.resolve(),
        args.topology_binary.resolve(),
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 preflight contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
