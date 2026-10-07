from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import n005_p2_contract as p2_contract

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "n005-p3-formal-comparison-v1"
EXPECTED_BRANCH = "research-n005-adaptive-tracing"
EXPECTED_P2_PROTOCOL = "n005-p2-equal-budget-candidates-v1"
EXPECTED_P2_COMMIT = "c9c2d80e898fe3b01e3c40e8ee449865ae65e581"
EXPECTED_N004_PROTOCOL = "n004-weakness-atlas-v2"
EXPECTED_REPETITIONS = 5
EXPECTED_MODES = ["current", "uniform-extra-rays", "adaptive-extra-rays"]
EXPECTED_ROTATION = [
    ["current", "uniform-extra-rays", "adaptive-extra-rays"],
    ["uniform-extra-rays", "adaptive-extra-rays", "current"],
    ["adaptive-extra-rays", "current", "uniform-extra-rays"],
]
EXPECTED_SCHEDULES = p2_contract.EXPECTED_SCHEDULES


class ContractError(RuntimeError):
    pass


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_config(payload)
    return payload


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N005 P3 schema version changed")
    if config.get("experiment") != "N005-p3-formal-comparison":
        raise ContractError("N005 P3 experiment identity changed")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N005 P3 protocol version changed")
    if config.get("issue") != 40 or config.get("branch") != EXPECTED_BRANCH:
        raise ContractError("N005 P3 issue/branch identity changed")

    predecessor = config.get("predecessor")
    if not isinstance(predecessor, dict):
        raise ContractError("N005 P3 predecessor missing")
    if predecessor.get("p2_protocol_version") != EXPECTED_P2_PROTOCOL:
        raise ContractError("N005 P3 P2 protocol changed")
    if predecessor.get("optimized_p2_evidence_commit") != EXPECTED_P2_COMMIT:
        raise ContractError("N005 P3 optimized P2 evidence commit changed")
    if predecessor.get("n004_protocol_version") != EXPECTED_N004_PROTOCOL:
        raise ContractError("N005 P3 N004 protocol changed")

    phase = config.get("phase_scope")
    if not isinstance(phase, dict) or phase.get("phase") != "P3":
        raise ContractError("N005 P3 phase changed")
    if phase.get("formal_target_measurement") is not True:
        raise ContractError("N005 P3 must remain formal")

    candidate = config.get("candidate")
    if not isinstance(candidate, dict):
        raise ContractError("N005 P3 candidate missing")
    expected_candidate = {
        "signal": p2_contract.EXPECTED_SIGNAL,
        "normalized_depth_threshold": p2_contract.EXPECTED_THRESHOLD,
        "state_gate": "camera-or-dynamic-state-change-only",
        "owner_budget_per_active_frame": p2_contract.EXPECTED_OWNER_BUDGET,
        "cascades_per_owner": p2_contract.EXPECTED_CASCADES,
        "extra_rays_per_probe": p2_contract.EXPECTED_EXTRA_RAYS_PER_PROBE,
        "requested_extra_rays_per_active_frame": p2_contract.EXPECTED_EXTRA_RAYS,
        "adaptive_selection": "deterministically-even-across-threshold-eligible-owner-order",
        "uniform_selection": "deterministically-even-across-all-visible-owner-order",
        "eligibility_shortfall": "invalid-candidate-frame",
        "extra_direction_rule": "same-deterministic-probe-key-hash-directions-for-uniform-and-adaptive",
    }
    if candidate != expected_candidate:
        raise ContractError("N005 P3 candidate drifted from frozen P2")

    if config.get("state_change_schedule") != EXPECTED_SCHEDULES:
        raise ContractError("N005 P3 state schedules changed")
    if config.get("required_modes") != EXPECTED_MODES:
        raise ContractError("N005 P3 modes changed")

    regimes = config.get("formal_regimes")
    if not isinstance(regimes, dict):
        raise ContractError("N005 P3 formal regimes missing")
    if regimes.get("decision") != [
        "camera-abrupt-reveal",
        "camera-gradual-motion",
        "stable-topology-deforming",
        "topology-changing-high-churn",
    ]:
        raise ContractError("N005 P3 decision regimes changed")
    if regimes.get("controls") != [
        "static", "changing-illumination-step", "world-dense"
    ]:
        raise ContractError("N005 P3 controls changed")
    if regimes.get("moving_rigid") != "excluded-formal-timing":
        raise ContractError("N005 P3 moving-rigid scope changed")

    reference = config.get("reference")
    if not isinstance(reference, dict):
        raise ContractError("N005 P3 reference policy missing")
    if reference.get("policy") != (
        "one-canonical-reference-set-per-case-shared-across-all-modes-and-repetitions"
    ):
        raise ContractError("N005 P3 reference policy changed")
    if reference.get("seed_mode") != "current":
        raise ContractError("N005 P3 reference seed mode changed")
    if reference.get("seed_is_formal_repetition") is not False:
        raise ContractError("N005 P3 reference seed cannot be a formal repetition")
    if reference.get("n004_reference_contract_unchanged") is not True:
        raise ContractError("N005 P3 N004 reference contract changed")

    repetition = config.get("repetition")
    if not isinstance(repetition, dict):
        raise ContractError("N005 P3 repetition contract missing")
    if repetition.get("count") != EXPECTED_REPETITIONS:
        raise ContractError("N005 P3 repetition count changed")
    if repetition.get("fresh_process_per_mode_repetition") is not True:
        raise ContractError("N005 P3 fresh-process requirement changed")
    if repetition.get("mode_order_rotation") != EXPECTED_ROTATION:
        raise ContractError("N005 P3 mode rotation changed")
    if repetition.get("summary_statistic") != "median":
        raise ContractError("N005 P3 summary statistic changed")
    if repetition.get("retain_all_raw_samples") is not True:
        raise ContractError("N005 P3 raw-sample retention disabled")

    timing = config.get("timing")
    if not isinstance(timing, dict):
        raise ContractError("N005 P3 timing contract missing")
    if timing.get("primary") != "gpu-timestamp":
        raise ContractError("N005 P3 timing primary changed")
    if timing.get("cpu_wall") != "diagnostic-only":
        raise ContractError("N005 P3 CPU-wall policy changed")
    if timing.get("non_positive_incremental_gpu_cost") != "measurement-limited":
        raise ContractError("N005 P3 non-positive timing policy changed")

    equal = config.get("equal_budget_gate")
    if not isinstance(equal, dict):
        raise ContractError("N005 P3 equal-budget gate missing")
    if equal.get("basis") != "actual-extra-rays-traced":
        raise ContractError("N005 P3 equal-budget basis changed")
    if equal.get("scope") != "per-frame-case-repetition":
        raise ContractError("N005 P3 equal-budget scope changed")
    if equal.get("uniform_adaptive_must_match") is not True:
        raise ContractError("N005 P3 equal-budget equality disabled")
    if equal.get("active_actual_extra_rays") != p2_contract.EXPECTED_EXTRA_RAYS:
        raise ContractError("N005 P3 active extra-ray count changed")
    if equal.get("base_work_prefix_immutable") is not True:
        raise ContractError("N005 P3 base prefix mutation allowed")
    if equal.get("extra_work_boundary") != (
        "after-frozen-base-producer-before-ray-prepare"
    ):
        raise ContractError("N005 P3 extra-work boundary changed")

    discipline = config.get("decision_discipline")
    if not isinstance(discipline, dict):
        raise ContractError("N005 P3 decision discipline missing")
    if discipline.get("primary_quality_metric") != "rgb-rms-error":
        raise ContractError("N005 P3 primary quality metric changed")
    for key in (
        "aggregate_score",
        "sample_exclusion",
        "post_hoc_threshold_or_budget_change",
        "gpu_profile_changes",
        "github_actions",
    ):
        if discipline.get(key) != "forbidden":
            raise ContractError(f"N005 P3 {key} must remain forbidden")
    if discipline.get("final_decision_values") != ["adopt", "reject", "refine"]:
        raise ContractError("N005 P3 decision values changed")


def validate_n004_predecessor(n004: dict[str, Any]) -> None:
    try:
        p2_contract.validate_n004_predecessor(n004)
    except p2_contract.ContractError as error:
        raise ContractError(str(error)) from error
