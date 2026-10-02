from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PFM_MAGIC = b"PF"
LUMA = (0.2126, 0.7152, 0.0722)


class ContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class PFMImage:
    width: int
    height: int
    pixels: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ContractError("PFM dimensions must be positive")
        if len(self.pixels) != self.width * self.height * 3:
            raise ContractError("PFM pixel count does not match dimensions")
        if not all(math.isfinite(value) for value in self.pixels):
            raise ContractError("PFM contains non-finite radiance")


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return value


def _require_sequence(value: Any, label: str, length: int | None = None) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{label} must be an array")
    if length is not None and len(value) != length:
        raise ContractError(f"{label} must contain {length} values")
    return value


def _require_number(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ContractError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ContractError(f"{label} must be finite")
    return number


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported N001 config schema_version")
    if config.get("experiment") != "N001":
        raise ContractError("config experiment must be N001")

    source = _require_mapping(config.get("source_of_truth"), "source_of_truth")
    commit = source.get("research_commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ContractError("source_of_truth.research_commit must be a full Git SHA")

    render = _require_mapping(config.get("render_contract"), "render_contract")
    width = render.get("width")
    height = render.get("height")
    if not isinstance(width, int) or width <= 0 or not isinstance(height, int) or height <= 0:
        raise ContractError("render_contract width/height must be positive integers")
    if render.get("hdr_format") != "PFM-RGB-f32":
        raise ContractError("N001 currently freezes PFM-RGB-f32 as the raw HDR exchange format")
    if render.get("color_space") != "linear-rec709":
        raise ContractError("N001 metrics require linear-rec709 radiance")
    if render.get("origin") != "top-left":
        raise ContractError("N001 in-memory/image alignment origin must be top-left")
    if render.get("valid_pixel_mask") != "all-finite-pixels":
        raise ContractError("N001 currently requires all finite pixels to participate in metrics")
    if render.get("tone_mapping_for_metrics") is not False:
        raise ContractError("N001 metrics must use untone-mapped HDR values")
    exposure = _require_number(render.get("metric_exposure"), "render_contract.metric_exposure")
    if exposure != 1.0:
        raise ContractError("N001 radiometric metrics must run before exposure/tone mapping")

    scene = _require_mapping(config.get("scene"), "scene")
    if not isinstance(scene.get("path"), str) or not scene["path"]:
        raise ContractError("scene.path is required")
    scene_sha = scene.get("sha256")
    if not isinstance(scene_sha, str) or len(scene_sha) != 64:
        raise ContractError("scene.sha256 must be a SHA-256 hex digest")

    playback = _require_mapping(config.get("playback"), "playback")
    subset_seed = playback.get("geometry_subset_seed")
    if not isinstance(subset_seed, int) or isinstance(subset_seed, bool) or subset_seed < 0:
        raise ContractError("playback.geometry_subset_seed must be a non-negative integer")
    frames = _require_sequence(playback.get("frames"), "playback.frames")
    if len(frames) < 4:
        raise ContractError("N001 playback must exercise at least static, camera, light, and geometry states")
    indices: list[int] = []
    kinds: set[str] = set()
    for position, raw_frame in enumerate(frames):
        frame = _require_mapping(raw_frame, f"playback.frames[{position}]")
        index = frame.get("frame")
        if not isinstance(index, int) or index < 0:
            raise ContractError("playback frame indices must be non-negative integers")
        indices.append(index)
        kind = frame.get("kind")
        if kind not in {"static", "camera-motion", "light-motion", "geometry-motion"}:
            raise ContractError(f"unsupported playback kind: {kind!r}")
        kinds.add(kind)
        camera = _require_mapping(frame.get("camera"), f"frame {index}.camera")
        base = _require_sequence(camera.get("base_direction"), f"frame {index}.camera.base_direction", 3)
        for component in base:
            _require_number(component, f"frame {index}.camera.base_direction")
        _require_number(camera.get("orbit_radians"), f"frame {index}.camera.orbit_radians")
        distance = _require_number(camera.get("distance_diagonal"), f"frame {index}.camera.distance_diagonal")
        if distance <= 0.0:
            raise ContractError(f"frame {index}.camera.distance_diagonal must be positive")
        _require_number(camera.get("vfov_degrees"), f"frame {index}.camera.vfov_degrees")
        light = _require_mapping(frame.get("light"), f"frame {index}.light")
        for key in ("offset_diagonal", "radiance"):
            vec = _require_sequence(light.get(key), f"frame {index}.light.{key}", 3)
            for component in vec:
                _require_number(component, f"frame {index}.light.{key}")
        geometry = _require_mapping(frame.get("geometry"), f"frame {index}.geometry")
        _require_number(geometry.get("rigid_phase"), f"frame {index}.geometry.rigid_phase")
        _require_number(geometry.get("deform_phase"), f"frame {index}.geometry.deform_phase")
        epoch = geometry.get("topology_epoch")
        if not isinstance(epoch, int) or epoch < 0:
            raise ContractError(f"frame {index}.geometry.topology_epoch must be a non-negative integer")
    if indices != list(range(len(indices))):
        raise ContractError("playback frame indices must be contiguous and start at zero")
    required_kinds = {"static", "camera-motion", "light-motion", "geometry-motion"}
    if not required_kinds.issubset(kinds):
        raise ContractError("N001 playback is missing a required state kind")

    reference = _require_mapping(config.get("reference_contract"), "reference_contract")
    if reference.get("transport") != "diffuse-path-traced":
        raise ContractError("N001 reference transport must be diffuse-path-traced")
    if reference.get("glossy_specular") is not False:
        raise ContractError("N001 reference bring-up does not include glossy/specular transport")
    min_spp = reference.get("min_spp")
    max_spp = reference.get("max_spp")
    if not isinstance(min_spp, int) or min_spp <= 0 or not isinstance(max_spp, int) or max_spp < min_spp:
        raise ContractError("reference_contract min_spp/max_spp are invalid")
    if max_spp % min_spp != 0:
        raise ContractError("reference_contract.max_spp must be a multiple of min_spp")
    max_bounces = reference.get("max_diffuse_bounces")
    if not isinstance(max_bounces, int) or max_bounces < 1:
        raise ContractError("reference_contract.max_diffuse_bounces must be >= 1")
    abs_limit = _require_number(reference.get("replicate_p99_abs_luminance_max"), "reference_contract.replicate_p99_abs_luminance_max")
    rel_limit = _require_number(reference.get("replicate_p99_relative_luminance_max"), "reference_contract.replicate_p99_relative_luminance_max")
    if abs_limit <= 0.0 or rel_limit <= 0.0:
        raise ContractError("reference convergence thresholds must be positive")

    metrics = _require_mapping(config.get("image_metrics"), "image_metrics")
    relative_floor = _require_number(metrics.get("relative_luminance_floor"), "image_metrics.relative_luminance_floor")
    if relative_floor <= 0.0:
        raise ContractError("relative luminance floor must be positive")
    affected_abs = _require_number(metrics.get("affected_abs_luminance"), "image_metrics.affected_abs_luminance")
    affected_rel = _require_number(metrics.get("affected_relative_luminance"), "image_metrics.affected_relative_luminance")
    if affected_abs < 0.0 or affected_rel < 0.0:
        raise ContractError("affected-pixel thresholds must be non-negative")
    required_metrics = set(_require_sequence(metrics.get("required"), "image_metrics.required"))
    expected_metrics = {
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
    if required_metrics != expected_metrics:
        raise ContractError("image_metrics.required does not match the frozen N001 metric set")

    timing = _require_mapping(config.get("timing_boundary"), "timing_boundary")
    stages = _require_sequence(timing.get("required_gi_stages"), "timing_boundary.required_gi_stages")
    required_stages = {
        "renderer_prerequisite_attributable_to_gi",
        "producer",
        "geometry_prepare_upload",
        "acceleration_structure_maintenance",
        "traversal",
        "gather",
        "radiance_storage",
        "merge_resolve",
        "synchronization",
    }
    if set(stages) != required_stages:
        raise ContractError("timing_boundary.required_gi_stages does not match the frozen N001 boundary")
    if timing.get("primary_axis") != "gpu_timestamp":
        raise ContractError("N001 timing primary axis must remain GPU timestamp")
    if timing.get("cpu_wall_role") != "diagnostic-health-provenance":
        raise ContractError("N001 CPU wall role must remain diagnostic/health/provenance")
    if set(_require_sequence(timing.get("required_totals"), "timing_boundary.required_totals")) != {
        "complete_gi_gpu", "complete_renderer_gpu"
    }:
        raise ContractError("timing_boundary.required_totals does not match the frozen N001 totals")
    if timing.get("formal_performance_threshold") is not None:
        raise ContractError("N001 must not freeze a performance winner threshold before Lane-N calibration")

    memory = _require_mapping(config.get("memory_boundary"), "memory_boundary")
    categories = set(_require_sequence(memory.get("required_categories"), "memory_boundary.required_categories"))
    required_categories = {
        "geometry_as_persistent",
        "radiance_storage_persistent",
        "producer_stream_persistent",
        "transient",
        "scratch",
        "old_new_overlap",
        "true_lifetime_peak",
        "host_mirrors",
    }
    if categories != required_categories:
        raise ContractError("memory_boundary.required_categories does not match the frozen N001 boundary")


def build_playback_manifest(config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    states = []
    for frame in config["playback"]["frames"]:
        state = {
            "frame": frame["frame"],
            "kind": frame["kind"],
            "camera": frame["camera"],
            "light": frame["light"],
            "geometry": frame["geometry"],
        }
        states.append({**state, "state_sha256": sha256_bytes(canonical_json_bytes(state))})
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "scene_sha256": config["scene"]["sha256"],
        "render_contract_sha256": sha256_bytes(canonical_json_bytes(config["render_contract"])),
        "frames": states,
    }
    manifest["playback_sha256"] = sha256_bytes(canonical_json_bytes(manifest))
    return manifest


def write_pfm(path: Path, image: PFMImage) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = PFM_MAGIC + b"\n" + f"{image.width} {image.height}\n-1.0\n".encode("ascii")
    row_stride = image.width * 3
    payload = bytearray()
    # PFM stores the first serialized row at the bottom. Our contract exposes top-left origin.
    for y in range(image.height - 1, -1, -1):
        row = image.pixels[y * row_stride : (y + 1) * row_stride]
        payload.extend(struct.pack(f"<{len(row)}f", *row))
    path.write_bytes(header + payload)


def read_pfm(path: Path) -> PFMImage:
    with path.open("rb") as handle:
        magic = handle.readline().strip()
        if magic != PFM_MAGIC:
            raise ContractError(f"{path}: expected RGB PFM magic PF")
        dimensions = handle.readline().decode("ascii").strip().split()
        if len(dimensions) != 2:
            raise ContractError(f"{path}: invalid PFM dimensions")
        width, height = (int(value) for value in dimensions)
        scale = float(handle.readline().decode("ascii").strip())
        if scale == 0.0:
            raise ContractError(f"{path}: PFM scale must not be zero")
        endian = "<" if scale < 0.0 else ">"
        payload = handle.read()
    count = width * height * 3
    expected = count * 4
    if len(payload) != expected:
        raise ContractError(f"{path}: expected {expected} payload bytes, got {len(payload)}")
    raw = struct.unpack(f"{endian}{count}f", payload)
    row_stride = width * 3
    pixels: list[float] = []
    for y in range(height - 1, -1, -1):
        pixels.extend(raw[y * row_stride : (y + 1) * row_stride])
    return PFMImage(width, height, tuple(pixels))


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    position = fraction * (len(sorted_values) - 1)
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return sorted_values[lo]
    weight = position - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def compare_hdr(output: PFMImage, reference: PFMImage, config: dict[str, Any]) -> dict[str, float | int]:
    if output.width != reference.width or output.height != reference.height:
        raise ContractError("output/reference dimensions do not match")
    metrics = config["image_metrics"]
    rel_floor = float(metrics["relative_luminance_floor"])
    affected_abs = float(metrics["affected_abs_luminance"])
    affected_rel = float(metrics["affected_relative_luminance"])

    abs_luma: list[float] = []
    rel_luma: list[float] = []
    rgb_sq_sum = 0.0
    affected = 0
    pixel_count = output.width * output.height
    for pixel in range(pixel_count):
        base = pixel * 3
        out_rgb = output.pixels[base : base + 3]
        ref_rgb = reference.pixels[base : base + 3]
        out_y = sum(out_rgb[i] * LUMA[i] for i in range(3))
        ref_y = sum(ref_rgb[i] * LUMA[i] for i in range(3))
        absolute = abs(out_y - ref_y)
        relative = absolute / max(abs(ref_y), rel_floor)
        abs_luma.append(absolute)
        rel_luma.append(relative)
        if absolute >= affected_abs and relative >= affected_rel:
            affected += 1
        for i in range(3):
            delta = out_rgb[i] - ref_rgb[i]
            rgb_sq_sum += delta * delta
    abs_luma.sort()
    rel_luma.sort()
    return {
        "pixel_count": pixel_count,
        "mean_abs_luminance_error": sum(abs_luma) / pixel_count,
        "mean_relative_luminance_error": sum(rel_luma) / pixel_count,
        "rgb_rms_error": math.sqrt(rgb_sq_sum / (pixel_count * 3)),
        "p95_abs_luminance_error": _percentile(abs_luma, 0.95),
        "p99_abs_luminance_error": _percentile(abs_luma, 0.99),
        "max_abs_luminance_error": abs_luma[-1],
        "p95_relative_luminance_error": _percentile(rel_luma, 0.95),
        "p99_relative_luminance_error": _percentile(rel_luma, 0.99),
        "affected_pixel_fraction": affected / pixel_count,
    }


def _artifact_relative_path(root: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ContractError(f"{label} must be a non-empty relative path")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ContractError(f"{label} must stay inside the artifact root")
    path = root / relative
    if not path.is_file():
        raise ContractError(f"{label} does not exist: {relative}")
    return path


def validate_target_artifact(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    manifest_path = root / "n001-provenance.json"
    if not manifest_path.is_file():
        raise ContractError("target artifact is missing n001-provenance.json")
    provenance = json.loads(manifest_path.read_text(encoding="utf-8"))
    if provenance.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("target provenance schema_version mismatch")
    git = _require_mapping(provenance.get("git"), "provenance.git")
    if git.get("branch") != "research-lane-n-end-to-end-renderer":
        raise ContractError("target provenance branch mismatch")
    commit = git.get("commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ContractError("target provenance git.commit must be a full Git SHA")
    if git.get("dirty") is not False:
        raise ContractError("target evidence requires a clean checkout")
    device = _require_mapping(provenance.get("device"), "provenance.device")
    for key in ("name", "driver_name", "driver_info"):
        if not isinstance(device.get(key), str) or not device[key]:
            raise ContractError(f"target provenance device.{key} must be a non-empty string")
    api_version = device.get("api_version")
    if not isinstance(api_version, (int, str)) or isinstance(api_version, bool) or not str(api_version):
        raise ContractError("target provenance device.api_version is invalid")
    if _require_number(device.get("timestamp_period_ns"), "device.timestamp_period_ns") <= 0.0:
        raise ContractError("device.timestamp_period_ns must be positive")

    expected_playback = build_playback_manifest(config)
    if provenance.get("playback_sha256") != expected_playback["playback_sha256"]:
        raise ContractError("target playback digest does not match frozen config")
    if provenance.get("scene_sha256") != config["scene"]["sha256"]:
        raise ContractError("target scene digest does not match frozen config")

    frames = _require_sequence(provenance.get("frames"), "provenance.frames")
    if len(frames) != len(expected_playback["frames"]):
        raise ContractError("target frame count does not match frozen playback")

    frame_metrics: list[dict[str, Any]] = []
    required_stages = set(config["timing_boundary"]["required_gi_stages"])
    required_memory = set(config["memory_boundary"]["required_categories"])
    for expected, raw in zip(expected_playback["frames"], frames, strict=True):
        frame = _require_mapping(raw, f"provenance frame {expected['frame']}")
        if frame.get("frame") != expected["frame"]:
            raise ContractError("target frame order/index mismatch")
        if frame.get("scene_state_sha256") != expected["state_sha256"]:
            raise ContractError(f"frame {expected['frame']} state digest mismatch")
        reference_status = _require_mapping(frame.get("reference"), "frame.reference")
        spp = reference_status.get("spp")
        if not isinstance(spp, int) or spp < config["reference_contract"]["min_spp"] or spp > config["reference_contract"]["max_spp"]:
            raise ContractError(f"frame {expected['frame']} reference spp is outside the frozen range")
        if reference_status.get("converged") is not True:
            raise ContractError(f"frame {expected['frame']} reference convergence gate failed")
        if _require_number(reference_status.get("replicate_p99_abs_luminance"), "reference replicate abs") > float(config["reference_contract"]["replicate_p99_abs_luminance_max"]):
            raise ContractError(f"frame {expected['frame']} reference absolute convergence threshold failed")
        if _require_number(reference_status.get("replicate_p99_relative_luminance"), "reference replicate relative") > float(config["reference_contract"]["replicate_p99_relative_luminance_max"]):
            raise ContractError(f"frame {expected['frame']} reference relative convergence threshold failed")

        correctness = _require_mapping(frame.get("correctness"), "frame.correctness")
        for key in (
            "traversal_runtime_errors",
            "oob_errors",
            "storage_failures",
            "lifetime_errors",
        ):
            if correctness.get(key) != 0:
                raise ContractError(f"frame {expected['frame']} correctness gate failed: {key}")
        if correctness.get("alignment_valid") is not True:
            raise ContractError(f"frame {expected['frame']} alignment_valid is false")

        timings = _require_mapping(frame.get("timing_us"), "frame.timing_us")
        gi = _require_number(timings.get("complete_gi_gpu"), "complete_gi_gpu")
        renderer = _require_number(timings.get("complete_renderer_gpu"), "complete_renderer_gpu")
        if gi < 0.0 or renderer < gi:
            raise ContractError("complete renderer GPU time must contain complete GI GPU time")
        stages = _require_mapping(timings.get("stages"), "frame.timing_us.stages")
        if set(stages) != required_stages:
            raise ContractError("frame timing stage set does not match frozen boundary")
        for name, value in stages.items():
            if _require_number(value, f"timing stage {name}") < 0.0:
                raise ContractError("timing stage values must be non-negative")

        memory = _require_mapping(frame.get("memory_bytes"), "frame.memory_bytes")
        if set(memory) != required_memory:
            raise ContractError("frame memory categories do not match frozen boundary")
        normalized_memory: dict[str, int] = {}
        for name, value in memory.items():
            if not isinstance(value, int) or isinstance(value, bool):
                raise ContractError(f"memory category {name} must be an integer byte count")
            if value < 0:
                raise ContractError("memory values must be non-negative")
            normalized_memory[name] = value
        true_peak = normalized_memory["true_lifetime_peak"]
        if true_peak < max(value for name, value in normalized_memory.items() if name != "host_mirrors"):
            raise ContractError("true_lifetime_peak is smaller than a device allocation category")

        output_path = _artifact_relative_path(root, frame.get("output_hdr"), "frame.output_hdr")
        reference_path = _artifact_relative_path(root, frame.get("reference_hdr"), "frame.reference_hdr")
        output = read_pfm(output_path)
        reference = read_pfm(reference_path)
        expected_width = config["render_contract"]["width"]
        expected_height = config["render_contract"]["height"]
        if (output.width, output.height) != (expected_width, expected_height):
            raise ContractError("output dimensions do not match frozen render contract")
        if (reference.width, reference.height) != (expected_width, expected_height):
            raise ContractError("reference dimensions do not match frozen render contract")
        metrics = compare_hdr(output, reference, config)
        frame_metrics.append({"frame": expected["frame"], **metrics})

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "playback_sha256": expected_playback["playback_sha256"],
        "frame_metrics": frame_metrics,
    }


def make_contract_smoke(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    width = config["render_contract"]["width"]
    height = config["render_contract"]["height"]
    pixels: list[float] = []
    for y in range(height):
        fy = 0.0 if height == 1 else y / (height - 1)
        for x in range(width):
            fx = 0.0 if width == 1 else x / (width - 1)
            pixels.extend((fx * 2.0, fy * 2.0, 0.25 + fx * fy))
    image = PFMImage(width, height, tuple(pixels))
    output_path = root / "contract-smoke-output.pfm"
    reference_path = root / "contract-smoke-reference.pfm"
    write_pfm(output_path, image)
    write_pfm(reference_path, image)
    roundtrip = read_pfm(output_path)
    metrics = compare_hdr(roundtrip, read_pfm(reference_path), config)
    if metrics["max_abs_luminance_error"] != 0.0 or metrics["rgb_rms_error"] != 0.0:
        raise ContractError("PFM/metric contract smoke did not reproduce identical radiance")
    playback = build_playback_manifest(config)
    (root / "n001-playback-manifest.json").write_bytes(canonical_json_bytes(playback))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass",
        "config_sha256": sha256_bytes(canonical_json_bytes(config)),
        "playback_sha256": playback["playback_sha256"],
        "pfm_sha256": sha256_file(output_path),
        "metrics": metrics,
    }
