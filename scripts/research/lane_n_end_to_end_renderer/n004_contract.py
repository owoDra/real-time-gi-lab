from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "n004-weakness-atlas-v1"
EXPECTED_CLASSIFICATIONS = [
    "not-observed-under-tested-regime",
    "present-but-bounded",
    "material-blocker",
    "capability-not-implemented",
    "measurement-limited",
]
EXPECTED_LEAK_SCENES = [
    "leak-thin", "leak-medium", "leak-thick", "leak-grazing",
    "leak-one-sided", "leak-enclosed",
]
GRADUAL_FRACTIONS = [0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0]
ABRUPT_FRACTIONS = [1.0] * 8


class ContractError(RuntimeError):
    pass


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
    return float(value)


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_config(payload)
    return payload


def validate_motion_cases(value: Any, label: str, names: list[str]) -> None:
    cases = _sequence(value, label)
    if [case.get("name") for case in cases] != names:
        raise ContractError(f"{label} names/order changed")
    if cases[0].get("motion_fractions") != ABRUPT_FRACTIONS:
        raise ContractError(f"{label} abrupt/step path changed")
    if cases[1].get("motion_fractions") != GRADUAL_FRACTIONS:
        raise ContractError(f"{label} gradual path changed")


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION or config.get("experiment") != "N004-weakness-atlas":
        raise ContractError("N004 experiment identity changed")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N004 protocol_version changed")
    if config.get("parent_issue") != 26 or config.get("issue") != 39:
        raise ContractError("N004 issue identity changed")
    if config.get("target_gpu") != "AMD Radeon 8060S Graphics (RADV STRIX_HALO)":
        raise ContractError("N004 target GPU changed")
    if config.get("completed_campaign_rerun_budget") != 0:
        raise ContractError("N004 completed campaign rerun budget changed")

    baseline = _mapping(config.get("baseline"), "baseline")
    if baseline.get("role") != "current-lane-e-final-hwrt":
        raise ContractError("N004 must measure the accepted current renderer")
    if baseline.get("resolution") != [320, 180] or baseline.get("cascades") != 4 or baseline.get("rays_per_probe") != 8:
        raise ContractError("N004 renderer sampling contract changed")
    if baseline.get("source_warmup_frames") != 32:
        raise ContractError("N004 source warm-up changed")

    safety = _mapping(config.get("host_safety"), "host_safety")
    if safety.get("gpu_profile_changes") != "forbidden" or safety.get("host_gpu_policy") != "leave-unchanged":
        raise ContractError("N004 must not modify the host GPU profile")

    reference = _mapping(config.get("reference"), "reference")
    if reference.get("min_spp") != 512 or reference.get("max_spp") != 8192 or reference.get("max_diffuse_bounces") != 8:
        raise ContractError("N004 reference convergence contract changed")

    metrics = _mapping(config.get("quality_metrics"), "quality_metrics")
    if _number(metrics.get("scale_aware_fraction"), "scale_aware_fraction") != 0.05 or _number(metrics.get("scale_aware_floor"), "scale_aware_floor") != 0.0001:
        raise ContractError("N004 scale-aware contract changed")
    n = _mapping(metrics.get("generic_not_observed"), "generic_not_observed")
    if (_number(n.get("rgb_rms_max_exclusive"), "not_observed.rgb") != 0.001 or
        _number(n.get("p99_relative_luminance_max_exclusive"), "not_observed.p99rel") != 0.05 or
        _number(n.get("scale_aware_affected_fraction_max_exclusive"), "not_observed.affected") != 0.01):
        raise ContractError("N004 not-observed threshold changed")
    b = _mapping(metrics.get("generic_material_blocker"), "generic_material_blocker")
    if (b.get("minimum_trigger_count") != 2 or
        _number(b.get("rgb_rms_min"), "blocker.rgb") != 0.01 or
        _number(b.get("p99_relative_luminance_min"), "blocker.p99rel") != 0.25 or
        _number(b.get("scale_aware_affected_fraction_min"), "blocker.affected") != 0.10):
        raise ContractError("N004 blocker threshold changed")

    families = _mapping(config.get("families"), "families")
    if set(families) != {
        "thin-geometry-light-leak", "camera-disocclusion", "changing-illumination",
        "dynamic-geometry", "world-shape", "capability-boundary",
    }:
        raise ContractError("N004 family set changed")

    leak = _mapping(families["thin-geometry-light-leak"], "leak")
    if leak.get("scenes") != EXPECTED_LEAK_SCENES or leak.get("target_frames") != 1:
        raise ContractError("N004 leak matrix changed")

    camera = _mapping(families["camera-disocclusion"], "camera")
    if camera.get("scenario") != "camera-motion" or camera.get("bounded_convergence_frame_max") != 4:
        raise ContractError("N004 camera contract changed")
    validate_motion_cases(camera.get("cases"), "camera.cases", ["abrupt-reveal", "gradual-motion"])

    light = _mapping(families["changing-illumination"], "light")
    if light.get("scenario") != "light-motion" or light.get("bounded_convergence_frame_max") != 4:
        raise ContractError("N004 light contract changed")
    validate_motion_cases(light.get("cases"), "light.cases", ["step-change", "gradual-change"])

    dynamic = _mapping(families["dynamic-geometry"], "dynamic")
    if dynamic.get("target_frames") != 4:
        raise ContractError("N004 dynamic sequence length changed")
    dynamic_scenarios = _sequence(dynamic.get("scenarios"), "dynamic.scenarios")
    if [item.get("name") for item in dynamic_scenarios] != ["moving-rigid", "stable-topology-deforming", "topology-changing-high-churn"]:
        raise ContractError("N004 dynamic scenario order changed")
    if dynamic_scenarios[0].get("formal_timing") is not False:
        raise ContractError("N004 moving-rigid timing must remain measurement-limited")

    world = _mapping(families["world-shape"], "world")
    if world.get("scenes") != ["world-sparse", "world-dense", "world-large-horizontal", "world-vertical-tall"]:
        raise ContractError("N004 world-shape matrix changed")

    capability = _mapping(families["capability-boundary"], "capability")
    if capability.get("diffuse_reference_bounces") != [1, 8]:
        raise ContractError("N004 diffuse capability reference changed")
    glossy = _mapping(capability.get("glossy_specular"), "capability.glossy_specular")
    if glossy.get("expected_classification") != "capability-not-implemented":
        raise ContractError("N004 glossy capability classification changed")

    if config.get("classification_values") != EXPECTED_CLASSIFICATIONS:
        raise ContractError("N004 classification vocabulary changed")
    timing = _mapping(config.get("timing"), "timing")
    if timing.get("primary") != "gpu-timestamp" or timing.get("cpu_wall") != "diagnostic-only":
        raise ContractError("N004 timing axis changed")
    if timing.get("moving_rigid") != "measurement-limited-descriptive-only":
        raise ContractError("N004 moving-rigid timing interpretation changed")
    if config.get("sample_exclusion") != "forbidden" or config.get("aggregate_weakness_score") != "forbidden":
        raise ContractError("N004 sample/aggregation discipline changed")
