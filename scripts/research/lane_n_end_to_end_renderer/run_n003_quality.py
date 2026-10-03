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

import n001_contract as image_contract
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
    / "out/research/lane-n-end-to-end-renderer/003-n003-quality-reference"
)
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
LUMA = (0.2126, 0.7152, 0.0722)


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
            f"N003 quality requires {EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N003 quality requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N003 quality requires a full Git SHA")
    return commit


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def metrics(
    output: image_contract.PFMImage,
    reference: image_contract.PFMImage,
    config: dict[str, Any],
) -> dict[str, float | int]:
    if output.width != reference.width or output.height != reference.height:
        raise contract.ContractError("N003 quality image dimensions differ")
    fraction = float(config["quality"]["scale_aware_fraction"])
    floor = float(config["quality"]["scale_aware_floor"])
    pixel_count = output.width * output.height
    rgb_sq = 0.0
    abs_luma: list[float] = []
    affected = 0
    for pixel in range(pixel_count):
        base = pixel * 3
        out_rgb = output.pixels[base : base + 3]
        ref_rgb = reference.pixels[base : base + 3]
        out_y = sum(out_rgb[index] * LUMA[index] for index in range(3))
        ref_y = sum(ref_rgb[index] * LUMA[index] for index in range(3))
        error = abs(out_y - ref_y)
        abs_luma.append(error)
        if error >= fraction * max(abs(ref_y), floor):
            affected += 1
        for index in range(3):
            delta = out_rgb[index] - ref_rgb[index]
            rgb_sq += delta * delta
    return {
        "pixel_count": pixel_count,
        "rgb_rms_error": math.sqrt(rgb_sq / (pixel_count * 3)),
        "p99_abs_luminance_error": _percentile(abs_luma, 0.99),
        "scale_aware_affected_pixel_fraction": affected / pixel_count,
    }


def error_direction(current: float, vanilla: float, fraction: float) -> str | None:
    if current <= vanilla * (1.0 - fraction) and current < vanilla:
        return "current-better"
    if vanilla <= current * (1.0 - fraction) and vanilla < current:
        return "vanilla-better"
    return None


def affected_direction(current: float, vanilla: float, minimum_difference: float) -> str | None:
    if abs(current - vanilla) < minimum_difference:
        return None
    return "current-better" if current < vanilla else "vanilla-better"


def safe_file(root: Path, raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise contract.ContractError(f"{label} must be a non-empty relative path")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise contract.ContractError(f"{label} escapes the artifact root")
    path = root / relative
    if not path.is_file():
        raise contract.ContractError(f"missing {label}: {relative}")
    return path


def analyze(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    evidence_path = root / "n003-quality-evidence.json"
    if not evidence_path.is_file():
        raise contract.ContractError("N003 quality evidence JSON is missing")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("schema_version") != 1 or evidence.get("protocol_version") != config["quality"]["protocol_version"]:
        raise contract.ContractError("N003 quality evidence protocol mismatch")
    if evidence.get("source_warmup_frames") != 32:
        raise contract.ContractError("N003 quality warm-up count changed")
    device = evidence.get("device")
    if not isinstance(device, dict) or device.get("name") != config["target_gpu"]:
        raise contract.ContractError("N003 quality target GPU mismatch")

    frames = evidence.get("frames")
    if not isinstance(frames, list) or len(frames) != len(contract.EXPECTED_SCENARIOS):
        raise contract.ContractError("N003 quality frame count mismatch")

    reference_cfg = config["quality"]["reference"]
    error_fraction = float(config["quality"]["material_error_relative_change_fraction"])
    affected_minimum = float(config["quality"]["material_affected_fraction_absolute_change"])
    required_count = int(config["quality"]["material_change_requires_primary_metric_count"])
    results: list[dict[str, Any]] = []

    for index, (scenario, frame) in enumerate(zip(contract.EXPECTED_SCENARIOS, frames, strict=True)):
        if not isinstance(frame, dict) or frame.get("frame") != index or frame.get("scenario") != scenario:
            raise contract.ContractError("N003 quality frame identity/order mismatch")
        if frame.get("scene_state_identical") is not True:
            raise contract.ContractError(f"N003 quality scene state differs in {scenario}")
        if frame.get("current_internal_correctness") is not True or frame.get("vanilla_internal_correctness") is not True:
            raise contract.ContractError(f"N003 quality internal correctness failed in {scenario}")
        reference_status = frame.get("reference")
        if not isinstance(reference_status, dict) or reference_status.get("converged") is not True:
            raise contract.ContractError(f"N003 quality reference did not converge in {scenario}")
        spp = reference_status.get("spp")
        if not isinstance(spp, int) or spp < reference_cfg["min_spp"] or spp > reference_cfg["max_spp"]:
            raise contract.ContractError(f"N003 quality reference SPP out of range in {scenario}")
        if float(reference_status.get("replicate_p99_abs_luminance", math.inf)) > float(reference_cfg["replicate_p99_abs_luminance_max"]):
            raise contract.ContractError(f"N003 quality reference abs convergence failed in {scenario}")
        if float(reference_status.get("replicate_p99_relative_luminance", math.inf)) > float(reference_cfg["replicate_p99_relative_luminance_max"]):
            raise contract.ContractError(f"N003 quality reference relative convergence failed in {scenario}")

        current = image_contract.read_pfm(safe_file(root, frame.get("current_hdr"), "current_hdr"))
        vanilla = image_contract.read_pfm(safe_file(root, frame.get("vanilla_hdr"), "vanilla_hdr"))
        reference = image_contract.read_pfm(safe_file(root, frame.get("reference_hdr"), "reference_hdr"))
        if (current.width, current.height) != (320, 180) or (vanilla.width, vanilla.height) != (320, 180):
            raise contract.ContractError("N003 quality renderer resolution changed")

        current_metrics = metrics(current, reference, config)
        vanilla_metrics = metrics(vanilla, reference, config)
        directions = {
            "rgb_rms_error": error_direction(
                float(current_metrics["rgb_rms_error"]),
                float(vanilla_metrics["rgb_rms_error"]),
                error_fraction,
            ),
            "p99_abs_luminance_error": error_direction(
                float(current_metrics["p99_abs_luminance_error"]),
                float(vanilla_metrics["p99_abs_luminance_error"]),
                error_fraction,
            ),
            "scale_aware_affected_pixel_fraction": affected_direction(
                float(current_metrics["scale_aware_affected_pixel_fraction"]),
                float(vanilla_metrics["scale_aware_affected_pixel_fraction"]),
                affected_minimum,
            ),
        }
        current_count = sum(value == "current-better" for value in directions.values())
        vanilla_count = sum(value == "vanilla-better" for value in directions.values())
        material_direction = None
        if current_count >= required_count:
            material_direction = "current-better"
        elif vanilla_count >= required_count:
            material_direction = "vanilla-better"
        results.append(
            {
                "scenario": scenario,
                "reference_spp": spp,
                "current": current_metrics,
                "vanilla": vanilla_metrics,
                "primary_metric_directions": directions,
                "material_quality_change": material_direction is not None,
                "material_quality_direction": material_direction,
            }
        )

    return {
        "status": "complete",
        "protocol_version": config["quality"]["protocol_version"],
        "per_scenario": results,
        "aggregate_winner": None,
    }


def completed_campaigns(current_root: Path) -> list[Path]:
    if not CAMPAIGN_ROOT.exists():
        return []
    result: list[Path] = []
    for path in CAMPAIGN_ROOT.glob("*/n003-quality-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "complete":
            result.append(path)
    return sorted(result)


def run_target(root: Path, config: dict[str, Any], binary: Path) -> int:
    commit = require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N003 quality binary: {binary}")
    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in existing)
        raise contract.ContractError(
            "N003 quality completed rerun budget is zero; existing campaign: " + joined
        )
    scene = (ROOT / str(config["baseline"]["scene"])).resolve()
    if common.sha256_file(scene) != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N003 quality scene digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    command = [
        str(binary),
        "--artifact-dir", str(root),
        "--scene", str(scene),
        "--source-warmup-frames", "32",
    ]
    if common.is_nixos():
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
        raise contract.ContractError("N003 quality target failed; retain artifact")

    summary = analyze(root, config)
    summary.update(
        {
            "schema_version": 1,
            "git_commit": commit,
            "target_gpu": config["target_gpu"],
            "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
            "sample_exclusion": "none",
        }
    )
    (root / "n003-quality-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"N003 quality artifacts: {root}")
    for item in summary["per_scenario"]:
        print(
            f"{item['scenario']}: material_quality_direction="
            f"{item['material_quality_direction']}"
        )
    print("N003 quality/reference evidence: COMPLETE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane N N003 quality/reference evidence")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N003 quality contract validation: PASS")
        return 0
    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / str(config["quality"]["evidence_binary"])).resolve()
    )
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N003 quality contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
