from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import n001_contract as base

SCHEMA_VERSION = 1
EXPECTED_SCENARIOS = [
    ("static", "static"),
    ("camera-motion", "camera-motion"),
    ("light-motion", "light-motion"),
    ("moving-rigid", "moving-rigid"),
    ("stable-topology-deforming", "deforming-control"),
]
REQUIRED_COMPLETION_SCENARIOS = {
    "static",
    "camera-motion",
    "light-motion",
    "moving-rigid",
    "stable-topology-deforming",
    "topology-changing-high-churn",
}
REQUIRED_STAGES = {
    "renderer_prerequisite_attributable_to_gi",
    "frame_init_visibility",
    "producer",
    "ray_prepare",
    "geometry_prepare_upload",
    "acceleration_structure_maintenance",
    "traversal",
    "gather",
    "radiance_storage",
    "merge_resolve",
    "synchronization",
}
REQUIRED_MEMORY = {
    "persistent",
    "transient",
    "scratch",
    "old_new_overlap",
    "true_lifetime_peak",
    "radiance_storage_persistent",
    "producer_stream_capacity",
    "image_transient",
}
REQUIRED_METRICS = {
    "mean_abs_luminance_error",
    "mean_relative_luminance_error",
    "rgb_rms_error",
    "p95_abs_luminance_error",
    "p99_abs_luminance_error",
    "max_abs_luminance_error",
    "p95_relative_luminance_error",
    "p99_relative_luminance_error",
    "affected_pixel_fraction",
}

ContractError = base.ContractError
PFMImage = base.PFMImage
read_pfm = base.read_pfm
compare_hdr = base.compare_hdr
sha256_bytes = base.sha256_bytes
canonical_json_bytes = base.canonical_json_bytes
sha256_file = base.sha256_file


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _sequence(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be an array")
    return value


def _number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ContractError(f"{label} must be finite")
    return number


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported N002 config schema_version")
    if config.get("experiment") != "N002" or config.get("phase") != "core-baseline":
        raise ContractError("N002 core config identity mismatch")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    for key in ("research_commit", "n001_completion_commit"):
        value = source.get(key)
        if not isinstance(value, str) or len(value) != 40:
            raise ContractError(f"source_of_truth.{key} must be a full Git SHA")
    if source.get("issue") != 27 or source.get("parent_issue") != 26:
        raise ContractError("N002 issue identity mismatch")

    scene = _mapping(config.get("scene"), "scene")
    if not isinstance(scene.get("path"), str) or not scene["path"]:
        raise ContractError("scene.path is required")
    if not isinstance(scene.get("sha256"), str) or len(scene["sha256"]) != 64:
        raise ContractError("scene.sha256 must be SHA-256")

    render = _mapping(config.get("render_contract"), "render_contract")
    if render.get("width") != 320 or render.get("height") != 180:
        raise ContractError("N002 core resolution must remain 320x180")
    expected_render = {
        "hdr_format": "PFM-RGB-f32",
        "color_space": "linear-rec709",
        "origin": "top-left",
        "valid_pixel_mask": "all-finite-pixels",
        "tone_mapping_for_metrics": False,
        "material_model": "constant-white-lambertian",
    }
    for key, expected in expected_render.items():
        if render.get(key) != expected:
            raise ContractError(f"render_contract.{key} mismatch")
    if _number(render.get("metric_exposure"), "metric_exposure") != 1.0:
        raise ContractError("N002 metrics must be pre-exposure")

    reference = _mapping(config.get("reference_contract"), "reference_contract")
    if reference.get("transport") != "diffuse-path-traced" or reference.get("glossy_specular") is not False:
        raise ContractError("N002 core reference transport mismatch")
    if reference.get("min_spp") != 512 or reference.get("max_spp") != 8192:
        raise ContractError("N002 core reference SPP range mismatch")
    if reference.get("sample_growth") != "powers-of-two" or reference.get("max_diffuse_bounces") != 8:
        raise ContractError("N002 core reference sampling mismatch")
    if reference.get("seed_a") != 305419896 or reference.get("seed_b") != 2596069104:
        raise ContractError("N002 reference seeds mismatch")
    if _number(reference.get("replicate_p99_abs_luminance_max"), "reference abs") != 0.001:
        raise ContractError("N002 reference absolute convergence mismatch")
    if _number(reference.get("replicate_p99_relative_luminance_max"), "reference rel") != 0.01:
        raise ContractError("N002 reference relative convergence mismatch")

    playback = _mapping(config.get("playback"), "playback")
    if playback.get("geometry_subset_seed") != 20261002:
        raise ContractError("N002 geometry subset seed mismatch")
    frames = _sequence(playback.get("frames"), "playback.frames")
    if len(frames) != len(EXPECTED_SCENARIOS):
        raise ContractError("N002 core playback must contain exactly five frames")
    for index, ((kind, runtime_scenario), raw) in enumerate(zip(EXPECTED_SCENARIOS, frames, strict=True)):
        frame = _mapping(raw, f"playback.frames[{index}]")
        if frame.get("frame") != index:
            raise ContractError("N002 frame indices must be contiguous")
        if frame.get("kind") != kind or frame.get("runtime_scenario") != runtime_scenario:
            raise ContractError(f"N002 frame {index} scenario identity mismatch")
        for section in ("camera", "light", "geometry"):
            if not isinstance(frame.get(section), dict):
                raise ContractError(f"N002 frame {index} missing {section}")

    completion = _mapping(config.get("completion"), "completion")
    required = set(_sequence(completion.get("required_scenarios"), "completion.required_scenarios"))
    implemented = set(_sequence(completion.get("implemented_in_this_phase"), "completion.implemented_in_this_phase"))
    pending = set(_sequence(completion.get("pending_after_this_phase"), "completion.pending_after_this_phase"))
    if required != REQUIRED_COMPLETION_SCENARIOS:
        raise ContractError("N002 completion scenario set mismatch")
    if implemented != REQUIRED_COMPLETION_SCENARIOS - {"topology-changing-high-churn"}:
        raise ContractError("N002 core implemented scenario set mismatch")
    if pending != {"topology-changing-high-churn"}:
        raise ContractError("N002 core must leave topology-changing-high-churn pending")
    if completion.get("n002_complete_when_pending_empty") is not True:
        raise ContractError("N002 completion rule missing")

    metrics = _mapping(config.get("image_metrics"), "image_metrics")
    if set(_sequence(metrics.get("required"), "image_metrics.required")) != REQUIRED_METRICS:
        raise ContractError("N002 image metric set mismatch")
    if _number(metrics.get("relative_luminance_floor"), "relative floor") <= 0.0:
        raise ContractError("N002 relative luminance floor must be positive")

    timing = _mapping(config.get("timing_boundary"), "timing_boundary")
    if timing.get("primary_axis") != "gpu_timestamp" or timing.get("cpu_wall_role") != "diagnostic-health-provenance":
        raise ContractError("N002 timing axis role mismatch")
    if timing.get("interpretation") != "descriptive-only-until-lane-n-complete-frame-calibration":
        raise ContractError("N002 core timing must remain descriptive-only")
    if timing.get("formal_performance_threshold") is not None:
        raise ContractError("N002 core must not freeze a performance threshold")
    if set(_sequence(timing.get("required_gi_stages"), "timing stages")) != REQUIRED_STAGES:
        raise ContractError("N002 timing stage set mismatch")
    if set(_sequence(timing.get("required_totals"), "timing totals")) != {"complete_gi_gpu", "complete_renderer_gpu"}:
        raise ContractError("N002 timing total set mismatch")
    if _number(timing.get("stage_sum_tolerance_us"), "stage tolerance") != 2.0:
        raise ContractError("N002 stage accounting tolerance mismatch")

    memory = _mapping(config.get("memory_boundary"), "memory_boundary")
    if set(_sequence(memory.get("required_categories"), "memory categories")) != REQUIRED_MEMORY:
        raise ContractError("N002 memory category set mismatch")

    correctness = _mapping(config.get("correctness"), "correctness")
    if set(_sequence(correctness.get("required_zero"), "correctness.required_zero")) != {
        "traversal_runtime_errors", "oob_errors", "storage_failures", "lifetime_errors"
    }:
        raise ContractError("N002 correctness gate set mismatch")
    if correctness.get("alignment_valid") is not True or correctness.get("sample_exclusion_allowed") is not False:
        raise ContractError("N002 correctness/exclusion contract mismatch")


def build_playback_manifest(config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    states: list[dict[str, Any]] = []
    for frame in config["playback"]["frames"]:
        state = {
            "frame": frame["frame"],
            "kind": frame["kind"],
            "runtime_scenario": frame["runtime_scenario"],
            "camera": frame["camera"],
            "light": frame["light"],
            "geometry": frame["geometry"],
        }
        states.append({**state, "state_sha256": sha256_bytes(canonical_json_bytes(state))})
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "scene_sha256": config["scene"]["sha256"],
        "render_contract_sha256": sha256_bytes(canonical_json_bytes(config["render_contract"])),
        "frames": states,
    }
    manifest["playback_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    return manifest


def image_signal_stats(image: PFMImage, relative_floor: float) -> dict[str, float | int]:
    luminance: list[float] = []
    for pixel in range(image.width * image.height):
        base_index = pixel * 3
        value = (
            image.pixels[base_index] * 0.2126
            + image.pixels[base_index + 1] * 0.7152
            + image.pixels[base_index + 2] * 0.0722
        )
        luminance.append(value)
    count = len(luminance)
    return {
        "pixel_count": count,
        "mean_luminance": sum(luminance) / count,
        "max_luminance": max(luminance),
        "positive_pixel_fraction": sum(value > 0.0 for value in luminance) / count,
        "above_relative_floor_fraction": sum(value >= relative_floor for value in luminance) / count,
    }


def _artifact_file(root: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ContractError(f"{label} must be a non-empty relative path")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ContractError(f"{label} escapes artifact root")
    path = root / relative
    if not path.is_file():
        raise ContractError(f"{label} does not exist: {relative}")
    return path


def validate_target_artifact(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    provenance_path = root / "n002-provenance.json"
    if not provenance_path.is_file():
        raise ContractError("target artifact is missing n002-provenance.json")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    if provenance.get("schema_version") != SCHEMA_VERSION or provenance.get("phase") != "core-baseline":
        raise ContractError("N002 provenance identity mismatch")

    git = _mapping(provenance.get("git"), "provenance.git")
    if git.get("branch") != "research-lane-n-end-to-end-renderer" or git.get("dirty") is not False:
        raise ContractError("N002 target evidence requires a clean Lane-N checkout")
    commit = git.get("commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ContractError("N002 provenance requires a full Git commit")

    device = _mapping(provenance.get("device"), "provenance.device")
    for key in ("name", "driver_name", "driver_info"):
        if not isinstance(device.get(key), str) or not device[key]:
            raise ContractError(f"N002 device.{key} missing")
    if _number(device.get("timestamp_period_ns"), "timestamp_period_ns") <= 0.0:
        raise ContractError("N002 timestamp period must be positive")

    expected = build_playback_manifest(config)
    if provenance.get("scene_sha256") != config["scene"]["sha256"]:
        raise ContractError("N002 scene digest mismatch")
    if provenance.get("playback_sha256") != expected["playback_sha256"]:
        raise ContractError("N002 playback digest mismatch")

    frames = _sequence(provenance.get("frames"), "provenance.frames")
    if len(frames) != len(expected["frames"]):
        raise ContractError("N002 core frame count mismatch")

    frame_metrics: list[dict[str, Any]] = []
    frame_signal: list[dict[str, Any]] = []
    renderer_has_signal = False
    reference_has_signal = False
    relative_floor = float(config["image_metrics"]["relative_luminance_floor"])
    tolerance = float(config["timing_boundary"]["stage_sum_tolerance_us"])

    for expected_frame, raw in zip(expected["frames"], frames, strict=True):
        frame = _mapping(raw, f"frame {expected_frame['frame']}")
        index = expected_frame["frame"]
        if frame.get("frame") != index or frame.get("scene_state_sha256") != expected_frame["state_sha256"]:
            raise ContractError(f"N002 frame {index} state identity mismatch")

        reference = _mapping(frame.get("reference"), "frame.reference")
        spp = reference.get("spp")
        if not isinstance(spp, int) or not (512 <= spp <= 8192):
            raise ContractError(f"N002 frame {index} reference SPP invalid")
        if reference.get("converged") is not True:
            raise ContractError(f"N002 frame {index} reference did not converge")
        if _number(reference.get("replicate_p99_abs_luminance"), "reference abs") > 0.001:
            raise ContractError(f"N002 frame {index} reference absolute convergence failed")
        if _number(reference.get("replicate_p99_relative_luminance"), "reference rel") > 0.01:
            raise ContractError(f"N002 frame {index} reference relative convergence failed")

        correctness = _mapping(frame.get("correctness"), "frame.correctness")
        for key in ("traversal_runtime_errors", "oob_errors", "storage_failures", "lifetime_errors"):
            if correctness.get(key) != 0:
                raise ContractError(f"N002 frame {index} correctness failed: {key}")
        if correctness.get("alignment_valid") is not True:
            raise ContractError(f"N002 frame {index} alignment invalid")

        timing = _mapping(frame.get("timing_us"), "frame.timing_us")
        gi = _number(timing.get("complete_gi_gpu"), "complete_gi_gpu")
        renderer = _number(timing.get("complete_renderer_gpu"), "complete_renderer_gpu")
        if gi < 0.0 or renderer < gi:
            raise ContractError(f"N002 frame {index} timing containment failed")
        stages = _mapping(timing.get("stages"), "timing.stages")
        if set(stages) != REQUIRED_STAGES:
            raise ContractError(f"N002 frame {index} timing stage set mismatch")
        normalized_stages = {name: _number(value, name) for name, value in stages.items()}
        if any(value < 0.0 for value in normalized_stages.values()):
            raise ContractError(f"N002 frame {index} timing stage negative")
        if abs(sum(normalized_stages.values()) - gi) > tolerance:
            raise ContractError(f"N002 frame {index} complete-GI accounting mismatch")

        memory = _mapping(frame.get("memory_bytes"), "frame.memory_bytes")
        if set(memory) != REQUIRED_MEMORY:
            raise ContractError(f"N002 frame {index} memory category mismatch")
        normalized_memory: dict[str, int] = {}
        for name, value in memory.items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ContractError(f"N002 frame {index} memory {name} invalid")
            normalized_memory[name] = value
        if normalized_memory["true_lifetime_peak"] < max(
            value for name, value in normalized_memory.items() if name != "true_lifetime_peak"
        ):
            raise ContractError(f"N002 frame {index} lifetime peak is too small")

        output = read_pfm(_artifact_file(root, frame.get("output_hdr"), "output HDR"))
        ref_image = read_pfm(_artifact_file(root, frame.get("reference_hdr"), "reference HDR"))
        if (output.width, output.height) != (320, 180) or (ref_image.width, ref_image.height) != (320, 180):
            raise ContractError(f"N002 frame {index} image dimensions mismatch")
        metrics = compare_hdr(output, ref_image, config)
        frame_metrics.append({"frame": index, "scenario": EXPECTED_SCENARIOS[index][0], **metrics})
        output_signal = image_signal_stats(output, relative_floor)
        ref_signal = image_signal_stats(ref_image, relative_floor)
        renderer_has_signal = renderer_has_signal or output_signal["max_luminance"] > 0.0
        reference_has_signal = reference_has_signal or ref_signal["max_luminance"] > 0.0
        frame_signal.append({
            "frame": index,
            "scenario": EXPECTED_SCENARIOS[index][0],
            "output": output_signal,
            "reference": ref_signal,
        })

    if not renderer_has_signal or not reference_has_signal:
        raise ContractError("N002 core campaign lacks positive renderer/reference HDR signal")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "phase": "core-baseline",
        "n002_complete": False,
        "pending_scenarios": ["topology-changing-high-churn"],
        "timing_interpretation": "descriptive-only",
        "playback_sha256": expected["playback_sha256"],
        "renderer_campaign_has_positive_signal": renderer_has_signal,
        "reference_campaign_has_positive_signal": reference_has_signal,
        "frame_signal": frame_signal,
        "frame_metrics": frame_metrics,
    }
