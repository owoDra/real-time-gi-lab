from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "n005-p0-p1-signal-probes-v1"
EXPECTED_BRANCH = "research-n005-adaptive-tracing"
EXPECTED_BASE = "c8af6b14bec9621cabdc8525b7e166a12a5fd272"
EXPECTED_N004_CONFIG = (
    "research/lanes/lane-n-end-to-end-renderer/experiments/"
    "004-n004-weakness-atlas-v2-config.json"
)
SIGNALS = [
    "newly-visible",
    "ownership-changed",
    "temporal-depth-change",
    "visibility-discontinuity",
    "depth-discontinuity",
]
SELECTION_FRACTIONS = [0.01, 0.05, 0.10, 0.20]
DECISION_REGIMES = [
    "camera-abrupt-reveal",
    "camera-gradual-motion",
    "stable-topology-deforming",
    "topology-changing-high-churn",
]
CONTROL_REGIMES = [
    "static",
    "changing-illumination-step",
    "world-dense",
]


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


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_config(payload)
    return payload


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N005 P0/P1 schema version changed")
    if config.get("experiment") != "N005-p0-p1-signal-probes":
        raise ContractError("N005 P0/P1 experiment identity changed")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N005 P0/P1 protocol version changed")
    if config.get("issue") != 40 or config.get("branch") != EXPECTED_BRANCH:
        raise ContractError("N005 issue/branch identity changed")

    base = _mapping(config.get("base"), "base")
    if base.get("branch") != "research-lane-n-end-to-end-renderer":
        raise ContractError("N005 base branch changed")
    if base.get("commit") != EXPECTED_BASE:
        raise ContractError("N005 base commit changed")

    predecessor = _mapping(config.get("predecessor"), "predecessor")
    if predecessor.get("config") != EXPECTED_N004_CONFIG:
        raise ContractError("N005 must reuse the accepted N004 v2 config")
    if predecessor.get("protocol_version") != "n004-weakness-atlas-v2":
        raise ContractError("N005 N004 predecessor protocol changed")
    if predecessor.get("evidence_protocol_version") != "n004-atlas-evidence-v3":
        raise ContractError("N005 N004 evidence protocol changed")
    if predecessor.get("renderer_role") != "current-lane-e-final-hwrt":
        raise ContractError("N005 must observe the frozen current renderer")

    safety = _mapping(config.get("host_safety"), "host_safety")
    if safety.get("gpu_profile_changes") != "forbidden":
        raise ContractError("N005 may not change the GPU profile")
    if safety.get("host_gpu_policy") != "leave-unchanged":
        raise ContractError("N005 host GPU policy changed")

    scope = _mapping(config.get("phase_scope"), "phase_scope")
    if scope.get("p0") != "reuse-and-accounting":
        raise ContractError("N005 P0 scope changed")
    if scope.get("p1") != "observation-only-signal-localization":
        raise ContractError("N005 P1 scope changed")
    if scope.get("extra_rays") != 0:
        raise ContractError("P0/P1 must trace zero extra rays")
    if scope.get("formal_target_measurement") is not False:
        raise ContractError("P1 is not formal target evidence")
    if scope.get("adaptive_tracing_implementation") is not False:
        raise ContractError("P0/P1 must not implement adaptive tracing")

    accounting = _mapping(
        config.get("p0_extra_ray_accounting"), "p0_extra_ray_accounting"
    )
    if accounting.get("base_traced_ray_source") != "n004-frame.stats.work_items":
        raise ContractError("base ray accounting source changed")
    if accounting.get("future_insertion_boundary") != (
        "after-frozen-base-producer-before-ray-prepare"
    ):
        raise ContractError("future extra-ray insertion boundary changed")
    if accounting.get("base_work_mutation") != "forbidden":
        raise ContractError("future extra rays may not mutate base work")
    if accounting.get("extra_work_storage") != "separate-append-range":
        raise ContractError("future extra-work isolation changed")
    if accounting.get("equal_budget_gate") != (
        "actual-extra-rays-traced-equal-per-frame-and-case"
    ):
        raise ContractError("equal-budget comparison gate changed")
    if _sequence(
        accounting.get("per_extra_ray_attribution"),
        "p0_extra_ray_accounting.per_extra_ray_attribution",
    ) != [
        "probe_x", "probe_y", "probe_z", "cascade", "source_tile_id", "signal_id"
    ]:
        raise ContractError("future per-ray attribution schema changed")
    if _sequence(
        accounting.get("required_future_frame_fields"),
        "p0_extra_ray_accounting.required_future_frame_fields",
    ) != [
        "base_traced_rays",
        "extra_rays_requested",
        "extra_rays_traced",
        "extra_work_items",
        "eligible_probe_count",
        "extra_probe_count",
        "extra_probe_fraction",
    ]:
        raise ContractError("future frame accounting schema changed")

    p1 = _mapping(config.get("p1"), "p1")
    if p1.get("signal_source") != "exact-gpu-visibility-depth-and-owner-readback":
        raise ContractError("P1 signal source changed")
    if _sequence(p1.get("signals"), "p1.signals") != SIGNALS:
        raise ContractError("P1 signal set/order changed")
    if p1.get("signal_combination") != "forbidden":
        raise ContractError("P1 must evaluate signals independently")
    if _sequence(p1.get("selection_fractions"), "p1.selection_fractions") != SELECTION_FRACTIONS:
        raise ContractError("P1 selection fractions changed")
    if _sequence(p1.get("error_axes"), "p1.error_axes") != [
        "absolute-luminance-error",
        "relative-luminance-error",
        "n004-scale-aware-affected-pixel",
    ]:
        raise ContractError("P1 error axes changed")
    if p1.get("timing_interpretation") != (
        "descriptive-only-observation-readback-can-perturb-inter-frame-host-sequencing"
    ):
        raise ContractError("P1 timing interpretation changed")
    if _sequence(p1.get("decision_regimes"), "p1.decision_regimes") != DECISION_REGIMES:
        raise ContractError("P1 decision regime matrix changed")
    if _sequence(p1.get("control_regimes"), "p1.control_regimes") != CONTROL_REGIMES:
        raise ContractError("P1 control regime matrix changed")

    if config.get("sample_exclusion") != "forbidden":
        raise ContractError("P1 sample exclusion is forbidden")
    if config.get("post_hoc_signal_threshold_change") != "forbidden":
        raise ContractError("P1 post-hoc signal threshold changes are forbidden")
    if config.get("aggregate_score") != "forbidden":
        raise ContractError("P1 aggregate scoring is forbidden")
    if "p2" in config or "candidate_rule" in config or "ray_budget" in config:
        raise ContractError("P0/P1 contract may not freeze P2 decisions")


def validate_n004_predecessor(n004: dict[str, Any]) -> None:
    """Check only the N004 facts N005 consumes after n004_contract validates it."""
    if n004.get("protocol_version") != "n004-weakness-atlas-v2":
        raise ContractError("accepted N004 v2 protocol is required")
    baseline = _mapping(n004.get("baseline"), "n004.baseline")
    if baseline.get("role") != "current-lane-e-final-hwrt":
        raise ContractError("N004 renderer role changed")
    if baseline.get("resolution") != [320, 180]:
        raise ContractError("N004 resolution changed")
    if baseline.get("cascades") != 4 or baseline.get("rays_per_probe") != 8:
        raise ContractError("N004 sampling contract changed")
    if baseline.get("source_warmup_frames") != 32:
        raise ContractError("N004 warm-up contract changed")

    families = _mapping(n004.get("families"), "n004.families")
    camera = _mapping(families.get("camera-disocclusion"), "n004.camera")
    if [item.get("name") for item in _sequence(camera.get("cases"), "n004.camera.cases")] != [
        "abrupt-reveal", "gradual-motion"
    ]:
        raise ContractError("N004 camera cases changed")
    dynamic = _mapping(families.get("dynamic-geometry"), "n004.dynamic")
    if [item.get("name") for item in _sequence(dynamic.get("scenarios"), "n004.dynamic.scenarios")] != [
        "moving-rigid",
        "stable-topology-deforming",
        "topology-changing-high-churn",
    ]:
        raise ContractError("N004 dynamic cases changed")
    world = _mapping(families.get("world-shape"), "n004.world")
    if "world-dense" not in _sequence(world.get("scenes"), "n004.world.scenes"):
        raise ContractError("N004 world-dense control disappeared")
