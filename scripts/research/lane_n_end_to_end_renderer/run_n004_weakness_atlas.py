#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import n001_contract as image_contract
import n004_contract as contract
import n004_scene_factory as scene_factory
import run_n003_preflight_v4 as common

ROOT = common.ROOT
EXPECTED_BRANCH = common.EXPECTED_BRANCH
DEFAULT_CONFIG = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/004-n004-weakness-atlas-config.json"
CAMPAIGN_ROOT = ROOT / "out/research/lane-n-end-to-end-renderer/004-n004-weakness-atlas"
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
LUMA = (0.2126, 0.7152, 0.0722)


def git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip())
    return proc.stdout.strip()


def require_clean_lane_n() -> str:
    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise contract.ContractError(f"N004 requires {EXPECTED_BRANCH}, got {branch!r}")
    if git("status", "--porcelain"):
        raise contract.ContractError("N004 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N004 requires a full Git SHA")
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
    completed: list[Path] = []
    for path in CAMPAIGN_ROOT.glob("*/n004-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") == "complete":
            completed.append(path)
    return sorted(completed)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def safe_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise contract.ContractError("N004 evidence path escaped case root")
    result = root / path
    if not result.is_file():
        raise contract.ContractError(f"N004 evidence file missing: {result}")
    return result


def luminance(rgb: list[float] | tuple[float, ...]) -> float:
    return sum(rgb[index] * LUMA[index] for index in range(3))


def metrics(output: image_contract.PFMImage, reference: image_contract.PFMImage, config: dict[str, Any]) -> dict[str, float | int]:
    if (output.width, output.height) != (reference.width, reference.height):
        raise contract.ContractError("N004 image dimensions differ")
    floor = float(config["quality_metrics"]["scale_aware_floor"])
    fraction = float(config["quality_metrics"]["scale_aware_fraction"])
    pixels = output.width * output.height
    rgb_sq = 0.0
    abs_luma: list[float] = []
    rel_luma: list[float] = []
    signed_luma: list[float] = []
    affected = 0
    for pixel in range(pixels):
        base = pixel * 3
        out_rgb = output.pixels[base:base + 3]
        ref_rgb = reference.pixels[base:base + 3]
        out_y, ref_y = luminance(out_rgb), luminance(ref_rgb)
        signed = out_y - ref_y
        delta = abs(signed)
        abs_luma.append(delta)
        signed_luma.append(signed)
        rel_luma.append(delta / max(abs(ref_y), floor))
        if delta >= fraction * max(abs(ref_y), floor):
            affected += 1
        for channel in range(3):
            d = out_rgb[channel] - ref_rgb[channel]
            rgb_sq += d * d
    return {
        "pixel_count": pixels,
        "rgb_rms_error": math.sqrt(rgb_sq / (pixels * 3)),
        "mean_abs_luminance_error": statistics.fmean(abs_luma),
        "signed_mean_luminance_error": statistics.fmean(signed_luma),
        "p99_abs_luminance_error": percentile(abs_luma, 0.99),
        "max_abs_luminance_error": max(abs_luma, default=0.0),
        "p99_relative_luminance_error": percentile(rel_luma, 0.99),
        "scale_aware_affected_pixel_fraction": affected / pixels,
    }


def temporal_rgb_rms(a: image_contract.PFMImage, b: image_contract.PFMImage) -> float:
    if (a.width, a.height) != (b.width, b.height):
        raise contract.ContractError("N004 temporal image dimensions differ")
    total = 0.0
    for x, y in zip(a.pixels, b.pixels, strict=True):
        d = x - y
        total += d * d
    return math.sqrt(total / max(len(a.pixels), 1))


def generic_classification(m: dict[str, Any], config: dict[str, Any]) -> str:
    q = config["quality_metrics"]
    n = q["generic_not_observed"]
    if (m["rgb_rms_error"] < n["rgb_rms_max_exclusive"] and
        m["p99_relative_luminance_error"] < n["p99_relative_luminance_max_exclusive"] and
        m["scale_aware_affected_pixel_fraction"] < n["scale_aware_affected_fraction_max_exclusive"]):
        return "not-observed-under-tested-regime"
    blocker = q["generic_material_blocker"]
    triggers = sum((
        m["rgb_rms_error"] >= blocker["rgb_rms_min"],
        m["p99_relative_luminance_error"] >= blocker["p99_relative_luminance_min"],
        m["scale_aware_affected_pixel_fraction"] >= blocker["scale_aware_affected_fraction_min"],
    ))
    return "material-blocker" if triggers >= blocker["minimum_trigger_count"] else "present-but-bounded"


def false_irradiance_metrics(output: image_contract.PFMImage, reference: image_contract.PFMImage, leak_cfg: dict[str, Any]) -> dict[str, Any]:
    dark_limit = float(leak_cfg["dark_reference_luminance_max"])
    delta_min = float(leak_cfg["false_irradiance_delta_min"])
    dark_count = false_count = 0
    deltas: list[float] = []
    xs: list[int] = []
    ys: list[int] = []
    for pixel in range(output.width * output.height):
        base = pixel * 3
        out_y = luminance(output.pixels[base:base + 3])
        ref_y = luminance(reference.pixels[base:base + 3])
        if ref_y <= dark_limit:
            dark_count += 1
            positive = max(0.0, out_y - ref_y)
            deltas.append(positive)
            if positive >= delta_min:
                false_count += 1
                xs.append(pixel % output.width)
                ys.append(pixel // output.width)
    bbox = None if not xs else {
        "min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys),
        "width": max(xs) - min(xs) + 1, "height": max(ys) - min(ys) + 1,
    }
    return {
        "dark_reference_pixels": dark_count,
        "false_irradiance_pixels": false_count,
        "false_irradiance_fraction": false_count / max(dark_count, 1),
        "false_irradiance_mean": statistics.fmean(deltas) if deltas else 0.0,
        "false_irradiance_p99": percentile(deltas, 0.99),
        "false_irradiance_max": max(deltas, default=0.0),
        "false_irradiance_bbox": bbox,
    }


def classify_leak(m: dict[str, Any], cfg: dict[str, Any]) -> str:
    n = cfg["not_observed"]
    if (m["false_irradiance_fraction"] < n["false_irradiance_fraction_max_exclusive"] and
        m["false_irradiance_p99"] < n["false_irradiance_p99_max_exclusive"]):
        return "not-observed-under-tested-regime"
    b = cfg["material_blocker"]
    if m["false_irradiance_fraction"] >= b["false_irradiance_fraction_min"] and m["false_irradiance_p99"] >= b["false_irradiance_p99_min"]:
        return "material-blocker"
    return "present-but-bounded"


def run_case(
    binary: Path, root: Path, scene: Path, scenario: str, source_warmup: int,
    target_frames: int, *, topology: bool = False, one_bounce: bool = False,
    motion_fractions: list[float] | None = None,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    command = [str(binary), "--artifact-dir", str(root), "--scene", str(scene), "--scenario", scenario,
               "--source-warmup-frames", str(source_warmup), "--target-frames", str(target_frames)]
    if motion_fractions is not None:
        command += ["--motion-fractions", ",".join(str(value) for value in motion_fractions)]
    if topology:
        command.append("--topology")
    if one_bounce:
        command.append("--one-bounce-reference")
    if common.is_nixos():
        command = ["bash", str(VULKAN_WRAPPER), *command]
    proc = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    (root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout); sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(f"N004 case failed: {root.name}; artifact retained")
    path = root / "n004-evidence.json"
    if not path.is_file():
        raise contract.ContractError(f"N004 evidence missing: {root.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != "n004-atlas-evidence-v3":
        raise contract.ContractError("N004 evidence protocol changed")
    if len(payload.get("frames", [])) != target_frames:
        raise contract.ContractError("N004 evidence frame count mismatch")
    return payload


def analyze_case(case_root: Path, evidence: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    frames: list[dict[str, Any]] = []
    images: list[image_contract.PFMImage] = []
    for frame in evidence["frames"]:
        image = image_contract.read_pfm(safe_file(case_root, frame["image"]))
        reference = image_contract.read_pfm(safe_file(case_root, frame["reference"]["path"]))
        m = metrics(image, reference, config)
        images.append(image)
        frames.append({
            "index": frame["index"],
            "motion_fraction": frame["motion_fraction"],
            "internal_correctness": bool(frame["internal_correctness"]),
            "quality": frame["quality"],
            "reference": frame["reference"],
            "metrics": m,
            "generic_classification": generic_classification(m, config),
            "timing_us": frame["timing_us"],
            "stats": frame["stats"],
            "memory_bytes": frame["memory_bytes"],
        })
    for index, frame in enumerate(frames):
        frame["temporal_rgb_rms_from_previous"] = None if index == 0 else temporal_rgb_rms(images[index], images[index - 1])
    return {
        "scenario": evidence["scenario"],
        "probe_spacing_world": evidence["probe_spacing_world"],
        "source": evidence["source"],
        "frames": frames,
    }


def correctness_failed(analyzed: dict[str, Any]) -> bool:
    if not bool(analyzed["source"]["internal_correctness"]):
        return True
    return any(not bool(frame["internal_correctness"]) for frame in analyzed["frames"])


def convergence_classification(frames: list[dict[str, Any]], max_bounded: int) -> tuple[str, int | None]:
    if frames[0]["generic_classification"] == "not-observed-under-tested-regime":
        return "not-observed-under-tested-regime", 0
    convergence = next((frame["index"] for frame in frames if frame["generic_classification"] == "not-observed-under-tested-regime"), None)
    blocker = any(frame["generic_classification"] == "material-blocker" for frame in frames)
    if blocker and (convergence is None or convergence > max_bounded):
        return "material-blocker", convergence
    return "present-but-bounded", convergence


def run_target(root: Path, config: dict[str, Any], binary: Path) -> int:
    commit = require_clean_lane_n()
    if not binary.is_file():
        raise contract.ContractError(f"missing N004 binary: {binary}")
    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(path.parent.relative_to(ROOT)) for path in existing)
        raise contract.ContractError("N004 completed campaign rerun budget is zero; existing campaign: " + joined)

    sponza = (ROOT / config["baseline"]["scene"]).resolve()
    if common.sha256_file(sponza) != config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N004 Sponza digest mismatch")
    root.mkdir(parents=True, exist_ok=True)
    generated = root / "generated-scenes"
    manifest = scene_factory.generate_all(generated)
    source_warmup = int(config["baseline"]["source_warmup_frames"])
    families: dict[str, Any] = {}

    leak_cfg = config["families"]["thin-geometry-light-leak"]
    leak_cases = []
    for scene_name in leak_cfg["scenes"]:
        meta = manifest["scenes"][scene_name]
        case_root = root / "cases" / scene_name
        evidence = run_case(binary, case_root, generated / meta["path"], "static", source_warmup, 1)
        analyzed = analyze_case(case_root, evidence, config)
        frame = evidence["frames"][0]
        image = image_contract.read_pfm(safe_file(case_root, frame["image"]))
        reference = image_contract.read_pfm(safe_file(case_root, frame["reference"]["path"]))
        leak_metrics = false_irradiance_metrics(image, reference, leak_cfg)
        analyzed["scene"] = meta
        analyzed["wall_thickness_over_probe_spacing"] = meta["wall_thickness_world"] / analyzed["probe_spacing_world"]
        analyzed["leak_metrics"] = leak_metrics
        analyzed["classification"] = classify_leak(leak_metrics, leak_cfg)
        leak_cases.append(analyzed)
    families["thin-geometry-light-leak"] = {"cases": leak_cases}

    for family_name in ("camera-disocclusion", "changing-illumination"):
        cfg = config["families"][family_name]
        temporal_cases = []
        for spec in cfg["cases"]:
            fractions = [float(value) for value in spec["motion_fractions"]]
            case_root = root / "cases" / family_name / spec["name"]
            evidence = run_case(binary, case_root, sponza, cfg["scenario"], source_warmup, len(fractions), motion_fractions=fractions)
            analyzed = analyze_case(case_root, evidence, config)
            classification, convergence = convergence_classification(analyzed["frames"], int(cfg["bounded_convergence_frame_max"]))
            analyzed["name"] = spec["name"]
            analyzed["classification"] = classification
            analyzed["convergence_frame"] = convergence
            temporal_cases.append(analyzed)
        families[family_name] = {"cases": temporal_cases}

    dynamic_cfg = config["families"]["dynamic-geometry"]
    dynamic_cases = []
    for spec in dynamic_cfg["scenarios"]:
        case_root = root / "cases" / spec["name"]
        evidence = run_case(binary, case_root, sponza, spec["scenario"], source_warmup, int(dynamic_cfg["target_frames"]), topology=bool(spec["topology"]))
        analyzed = analyze_case(case_root, evidence, config)
        analyzed["name"] = spec["name"]
        analyzed["formal_timing"] = bool(spec["formal_timing"])
        analyzed["classification"] = "measurement-limited" if spec["name"] == "moving-rigid" else analyzed["frames"][0]["generic_classification"]
        dynamic_cases.append(analyzed)
    families["dynamic-geometry"] = {"cases": dynamic_cases}

    world_cfg = config["families"]["world-shape"]
    world_cases = []
    for scene_name in world_cfg["scenes"]:
        meta = manifest["scenes"][scene_name]
        case_root = root / "cases" / scene_name
        evidence = run_case(binary, case_root, generated / meta["path"], "static", source_warmup, 1)
        analyzed = analyze_case(case_root, evidence, config)
        analyzed["scene"] = meta
        analyzed["correctness_or_capacity_failure"] = correctness_failed(analyzed)
        analyzed["classification"] = (
            "material-blocker"
            if analyzed["correctness_or_capacity_failure"] and world_cfg["correctness_or_capacity_failure_is_blocker"]
            else analyzed["frames"][0]["generic_classification"]
        )
        world_cases.append(analyzed)
    families["world-shape"] = {"cases": world_cases}

    capability_root = root / "cases" / "capability-diffuse"
    cap = run_case(binary, capability_root, sponza, "static", source_warmup, 1, one_bounce=True)
    one = image_contract.read_pfm(safe_file(capability_root, cap["reference_one_bounce"]["path"]))
    eight = image_contract.read_pfm(safe_file(capability_root, cap["frames"][0]["reference"]["path"]))
    higher = metrics(one, eight, config)
    rule = config["families"]["capability-boundary"]["higher_order_material_rule"]
    triggers = sum((
        higher["rgb_rms_error"] >= rule["rgb_rms_min"],
        higher["p99_relative_luminance_error"] >= rule["p99_relative_luminance_min"],
        higher["scale_aware_affected_pixel_fraction"] >= rule["scale_aware_affected_fraction_min"],
    ))
    families["capability-boundary"] = {
        "higher_order_diffuse": {
            "classification": "capability-not-implemented",
            "reference_delta_metrics_1bounce_vs_8bounce": higher,
            "material_gap_exposed_under_sponza": triggers >= rule["minimum_trigger_count"],
        },
        "glossy_specular": {
            "classification": "capability-not-implemented",
            "evidence": "frozen renderer is constant-white Lambertian diffuse and has no glossy/specular indirect transport path",
        },
    }

    summary = {
        "schema_version": 1,
        "protocol_version": config["protocol_version"],
        "status": "complete",
        "git_commit": commit,
        "target_gpu": config["target_gpu"],
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        "completed_campaign_rerun_budget": 0,
        "sample_exclusion": "none",
        "families": families,
        "aggregate_weakness_score": None,
    }
    (root / "n004-scenes.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "n004-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / "n004-provenance.json").write_text(json.dumps({
        "schema_version": 1,
        "protocol_version": config["protocol_version"],
        "git": {"branch": EXPECTED_BRANCH, "commit": commit, "dirty": False},
        "scene_sha256": config["baseline"]["scene_sha256"],
        "target_gpu": config["target_gpu"],
        "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"N004 weakness-atlas artifacts: {root}")
    print("N004 weakness atlas: COMPLETE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane N N004 weakness-atlas runner")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()
    config = contract.load_config(args.config.resolve())
    if args.phase == "contract":
        print("N004 weakness-atlas contract validation: PASS")
        return 0
    binary = args.binary.resolve() if args.binary else (ROOT / "build/release/phos-n004-atlas").resolve()
    return run_target(artifact_dir(args.artifact_dir), config, binary)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N004 contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
