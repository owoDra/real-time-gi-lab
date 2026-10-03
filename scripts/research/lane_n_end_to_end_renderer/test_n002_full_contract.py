#!/usr/bin/env python3
from __future__ import annotations

import copy
from pathlib import Path

import n002_full_contract as contract

ROOT = Path(__file__).resolve().parents[3]
CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/002-n002-full-config.json"
)


def require_contract_error(config: dict, label: str) -> None:
    try:
        contract.validate_config(config)
    except contract.ContractError:
        return
    raise AssertionError(f"{label}: expected ContractError")


def main() -> int:
    config = contract.load_config(CONFIG)
    manifest = contract.build_playback_manifest(config)

    assert len(manifest["frames"]) == 6
    topology = manifest["frames"][5]
    assert topology["kind"] == "topology-changing-high-churn"
    assert topology["runtime_scenario"] == "lane-e-object-local-hwrt-rebuild"
    assert topology["geometry"]["high_churn_fraction"] == 0.5
    assert topology["geometry"]["object_local_rebuild"] is True
    assert topology["geometry"]["stable_renderer_slot_count"] is True

    bad_churn = copy.deepcopy(config)
    bad_churn["playback"]["frames"][5]["geometry"]["high_churn_fraction"] = 0.25
    require_contract_error(bad_churn, "high-churn drift")

    bad_backend = copy.deepcopy(config)
    bad_backend["playback"]["frames"][5]["runtime_scenario"] = "global-rebuild"
    require_contract_error(bad_backend, "topology backend drift")

    bad_pending = copy.deepcopy(config)
    bad_pending["completion"]["pending_after_this_phase"] = [
        "topology-changing-high-churn"
    ]
    require_contract_error(bad_pending, "completion drift")

    bad_threshold = copy.deepcopy(config)
    bad_threshold["timing_boundary"]["formal_performance_threshold"] = 0.05
    require_contract_error(bad_threshold, "post-hoc performance threshold")

    print("N002 full GPU-independent contract tests: PASS")
    print(f"playback_sha256={manifest['playback_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
