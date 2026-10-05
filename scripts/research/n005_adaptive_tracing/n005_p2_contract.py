from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import n005_contract as p1_contract

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "n005-p2-equal-budget-candidates-v1"
EXPECTED_BRANCH = "research-n005-adaptive-tracing"
EXPECTED_SIGNAL = "depth-discontinuity"
EXPECTED_THRESHOLD = 0.01
EXPECTED_OWNER_BUDGET = 576
EXPECTED_CASCADES = 4
EXPECTED_EXTRA_RAYS_PER_PROBE = 4
EXPECTED_EXTRA_RAYS = 9216
EXPECTED_P1_PROTOCOL = "n005-p0-p1-signal-probes-v1"
EXPECTED_P1_COMMIT = "f110ee3044b00f4dba5c7ae5787aa3df094bd0e1"
EXPECTED_N004_PROTOCOL = "n004-weakness-atlas-v2"

EXPECTED_SCHEDULES = {
    "camera-abrupt-reveal": [576, 0, 0, 0, 0, 0, 0, 0],
    "camera-gradual-motion": [576] * 8,
    "stable-topology-deforming": [576, 0, 0, 0],
    "topology-changing-high-churn": [576, 0, 0, 0],
    "static": [0],
    "changing-illumination-step": [0] * 8,
    "world-dense": [0],
}


class ContractError(RuntimeError):
    pass


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_config(payload)
    return payload


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N005 P2 schema version changed")
    if config.get("experiment") != "N005-p2-equal-budget-candidates":
        raise ContractError("N005 P2 experiment identity changed")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N005 P2 protocol version changed")
    if config.get("issue") != 40 or config.get("branch") != EXPECTED_BRANCH:
        raise ContractError("N005 P2 issue/branch identity changed")

    predecessor = config.get("predecessor")
    if not isinstance(predecessor, dict):
        raise ContractError("N005 P2 predecessor missing")
    if predecessor.get("p1_protocol_version") != EXPECTED_P1_PROTOCOL:
        raise ContractError("N005 P2 P1 predecessor protocol changed")
    if predecessor.get("p1_commit") != EXPECTED_P1_COMMIT:
        raise ContractError("N005 P2 P1 predecessor commit changed")
    if predecessor.get("n004_protocol_version") != EXPECTED_N004_PROTOCOL:
        raise ContractError("N005 P2 N004 predecessor protocol changed")

    phase = config.get("phase_scope")
    if not isinstance(phase, dict):
        raise ContractError("N005 P2 phase scope missing")
    if phase.get("phase") != "P2":
        raise ContractError("N005 P2 phase changed")
    if phase.get("formal_target_measurement") is not False:
        raise ContractError("P2 must remain non-formal")

    candidate = config.get("candidate")
    if not isinstance(candidate, dict):
        raise ContractError("N005 P2 candidate missing")
    if candidate.get("signal") != EXPECTED_SIGNAL:
        raise ContractError("N005 P2 signal changed")
    if candidate.get("normalized_depth_threshold") != EXPECTED_THRESHOLD:
        raise ContractError("N005 P2 depth threshold changed")
    if candidate.get("state_gate") != "camera-or-dynamic-state-change-only":
        raise ContractError("N005 P2 state gate changed")
    if candidate.get("owner_budget_per_active_frame") != EXPECTED_OWNER_BUDGET:
        raise ContractError("N005 P2 owner budget changed")
    if candidate.get("cascades_per_owner") != EXPECTED_CASCADES:
        raise ContractError("N005 P2 cascade count changed")
    if candidate.get("extra_rays_per_probe") != EXPECTED_EXTRA_RAYS_PER_PROBE:
        raise ContractError("N005 P2 extra-ray multiplicity changed")
    if candidate.get("requested_extra_rays_per_active_frame") != EXPECTED_EXTRA_RAYS:
        raise ContractError("N005 P2 requested extra-ray count changed")
    if candidate.get("eligibility_shortfall") != "invalid-candidate-frame":
        raise ContractError("N005 P2 eligibility shortfall policy changed")

    schedules = config.get("state_change_schedule")
    if schedules != EXPECTED_SCHEDULES:
        raise ContractError("N005 P2 state-change schedules changed")

    if config.get("required_modes") != [
        "current", "uniform-extra-rays", "adaptive-extra-rays"
    ]:
        raise ContractError("N005 P2 baseline set changed")

    equal = config.get("equal_budget_gate")
    if not isinstance(equal, dict):
        raise ContractError("N005 P2 equal-budget gate missing")
    if equal.get("basis") != "actual-extra-rays-traced":
        raise ContractError("N005 P2 equal-budget basis changed")
    if equal.get("scope") != "per-frame-and-case":
        raise ContractError("N005 P2 equal-budget scope changed")
    if equal.get("uniform_adaptive_must_match") is not True:
        raise ContractError("N005 P2 equal-budget equality disabled")
    if equal.get("base_work_prefix_immutable") is not True:
        raise ContractError("N005 P2 base work mutation allowed")
    if equal.get("extra_work_boundary") != (
        "after-frozen-base-producer-before-ray-prepare"
    ):
        raise ContractError("N005 P2 insertion boundary changed")

    discipline = config.get("decision_discipline")
    if not isinstance(discipline, dict):
        raise ContractError("N005 P2 discipline missing")
    for key in (
        "aggregate_score",
        "sample_exclusion",
        "post_hoc_threshold_change",
        "gpu_profile_changes",
        "github_actions",
    ):
        if discipline.get(key) != "forbidden":
            raise ContractError(f"N005 P2 {key} must remain forbidden")
    if discipline.get("p3_requires_new_frozen_formal_contract") is not True:
        raise ContractError("N005 P3 freeze requirement changed")


def validate_n004_predecessor(n004: dict[str, Any]) -> None:
    """Reuse the P1-frozen N004 facts consumed by N005."""
    try:
        p1_contract.validate_n004_predecessor(n004)
    except p1_contract.ContractError as error:
        raise ContractError(str(error)) from error
