from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import n003_comparison_contract as base

ContractError = base.ContractError
EXPECTED_SCENARIOS = base.EXPECTED_SCENARIOS


def validate_config(config: dict[str, Any]) -> None:
    base.validate_config(config)
    quality = config.get("quality")
    if not isinstance(quality, dict):
        raise ContractError("N003 quality config must be an object")
    if quality.get("evidence_binary") != "build/phos-n003-quality":
        raise ContractError("N003 quality evidence binary changed")
    if quality.get("protocol_version") != "current-vs-vanilla-quality-v1":
        raise ContractError("N003 quality protocol changed")
    if quality.get("material_error_relative_change_fraction") != 0.10:
        raise ContractError("N003 quality error material threshold changed")
    if quality.get("error_material_rule") != "lower-value-at-most-90-percent-of-other-value":
        raise ContractError("N003 quality error direction rule changed")
    if quality.get("material_affected_fraction_absolute_change") != 0.005:
        raise ContractError("N003 quality affected-fraction threshold changed")
    if quality.get("affected_material_rule") != "absolute-difference-at-least-0.005-lower-is-better":
        raise ContractError("N003 quality affected direction rule changed")
    if quality.get("material_change_requires_primary_metric_count") != 2:
        raise ContractError("N003 quality concordance count changed")
    if quality.get("scenario_direction_rule") != "at-least-two-primary-metrics-material-in-same-direction":
        raise ContractError("N003 quality scenario direction rule changed")
    if quality.get("legacy_affected_pixel_fraction") != "diagnostic-only":
        raise ContractError("N003 legacy affected fraction role changed")
    if quality.get("black_reference_frames") != "valid":
        raise ContractError("N003 black-reference interpretation changed")

    reference = quality.get("reference")
    if not isinstance(reference, dict):
        raise ContractError("N003 quality reference contract missing")
    expected_reference = {
        "transport": "diffuse-path-traced",
        "min_spp": 512,
        "max_spp": 8192,
        "max_diffuse_bounces": 8,
        "replicate_p99_abs_luminance_max": 0.001,
        "replicate_p99_relative_luminance_max": 0.01,
    }
    if reference != expected_reference:
        raise ContractError("N003 quality reference contract changed")

    correctness = config.get("correctness")
    if not isinstance(correctness, dict) or correctness.get("quality_requires_identical_scene_state") is not True:
        raise ContractError("N003 quality identical-scene-state gate changed")
    artifact = config.get("artifact_contract")
    if not isinstance(artifact, dict):
        raise ContractError("N003 quality artifact contract missing")
    required = artifact.get("quality_required")
    if set(required if isinstance(required, list) else []) != {
        "n003-quality-evidence.json",
        "n003-quality-summary.json",
    }:
        raise ContractError("N003 quality artifact set changed")


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config
