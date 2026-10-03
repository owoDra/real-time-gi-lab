from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROTOCOL_VERSION = "moving-rigid-workload-invariance-v1"
EXPECTED_ORDERS = ["AB", "BA", "AB", "BA", "BA", "AB", "BA", "AB"]
REQUIRED_STAT_FIELDS = [
    "work_items",
    "outputs",
    "requested_work_items",
    "requested_outputs",
    "overflow",
    "visible_owners",
    "moved_primitives",
    "segment_membership_changes",
    "hierarchy_refit_segments",
    "hierarchy_rebuilt_segments",
    "topology_mutations",
    "topology_replaced_primitives",
    "backend_rebuilds",
    "storage_allocations",
    "storage_updates",
    "storage_invalidations",
    "storage_failures",
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
    config = json.loads(path.read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("N003 moving diagnostic schema changed")
    if config.get("experiment") != "N003-moving-workload-diagnostic":
        raise ContractError("N003 moving diagnostic identity changed")
    if config.get("phase") != "diagnostic":
        raise ContractError("N003 moving diagnostic phase changed")
    if config.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 moving diagnostic protocol changed")
    if config.get("target_gpu") != "AMD Radeon 8060S Graphics (RADV STRIX_HALO)":
        raise ContractError("N003 moving diagnostic target GPU changed")

    source = _mapping(config.get("source_of_truth"), "source_of_truth")
    if source.get("issue") != 31 or source.get("parent_issue") != 26:
        raise ContractError("N003 moving diagnostic issue identity changed")

    diagnostic = _mapping(config.get("diagnostic"), "diagnostic")
    if diagnostic.get("scenario") != "moving-rigid":
        raise ContractError("N003 moving diagnostic scenario changed")
    if diagnostic.get("pair_blocks") != 8:
        raise ContractError("N003 moving diagnostic requires eight pair blocks")
    if _sequence(diagnostic.get("start_orders"), "diagnostic.start_orders") != EXPECTED_ORDERS:
        raise ContractError("N003 moving diagnostic pair order changed")
    if diagnostic.get("source_warmup_frames") != 32:
        raise ContractError("N003 moving diagnostic warm-up changed")
    if diagnostic.get("gpu_profile_changes") != "forbidden":
        raise ContractError("N003 moving diagnostic must forbid GPU profile changes")
    if diagnostic.get("host_gpu_policy") != "leave-unchanged":
        raise ContractError("N003 moving diagnostic host GPU policy changed")
    if diagnostic.get("sample_exclusion") != "forbidden":
        raise ContractError("N003 moving diagnostic sample exclusion changed")
    if diagnostic.get("timing_role") != "diagnostic-only":
        raise ContractError("N003 moving diagnostic timing role changed")
    if _sequence(diagnostic.get("required_stat_fields"), "required_stat_fields") != REQUIRED_STAT_FIELDS:
        raise ContractError("N003 moving diagnostic stat fields changed")


def validate_stats(stats: Any, label: str) -> dict[str, int]:
    value = _mapping(stats, label)
    result: dict[str, int] = {}
    for field in REQUIRED_STAT_FIELDS:
        item = value.get(field)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise ContractError(f"{label}.{field} must be a non-negative integer")
        result[field] = item
    return result


def validate_pair(pair: dict[str, Any], config: dict[str, Any], expected_order: str) -> None:
    validate_config(config)
    if pair.get("schema_version") != 1 or pair.get("protocol_version") != PROTOCOL_VERSION:
        raise ContractError("N003 moving diagnostic pair identity mismatch")
    if pair.get("source_warmup_frames") != config["diagnostic"]["source_warmup_frames"]:
        raise ContractError("N003 moving diagnostic warm-up mismatch")
    if pair.get("start_order") != expected_order:
        raise ContractError("N003 moving diagnostic start order mismatch")

    device = _mapping(pair.get("device"), "pair.device")
    if device.get("name") != config["target_gpu"]:
        raise ContractError("N003 moving diagnostic ran on wrong GPU")

    for role in ("A", "B"):
        sample = _mapping(pair.get(role), f"pair.{role}")
        validate_stats(sample.get("source_stats"), f"pair.{role}.source_stats")
        validate_stats(sample.get("target_stats"), f"pair.{role}.target_stats")
        for timing in ("complete_gi_gpu_us", "complete_renderer_gpu_us"):
            value = sample.get(timing)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) <= 0.0:
                raise ContractError(f"pair.{role}.{timing} must be positive")


def summarize(blocks: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    if len(blocks) != 8:
        raise ContractError("N003 moving diagnostic expected eight blocks")

    phases: dict[str, Any] = {}
    workload_invariant = True
    for phase_key in ("source_stats", "target_stats"):
        fields: dict[str, Any] = {}
        for field in REQUIRED_STAT_FIELDS:
            values: list[int] = []
            mismatch_blocks: list[int] = []
            for index, block in enumerate(blocks):
                if block.get("block") != index:
                    raise ContractError("N003 moving diagnostic block index mismatch")
                expected_order = EXPECTED_ORDERS[index]
                if block.get("start_order") != expected_order:
                    raise ContractError("N003 moving diagnostic block order mismatch")
                pair = _mapping(block.get("pair"), "block.pair")
                validate_pair(pair, config, expected_order)
                a = int(pair["A"][phase_key][field])
                b = int(pair["B"][phase_key][field])
                values.extend((a, b))
                if a != b:
                    mismatch_blocks.append(index)
            distinct = sorted(set(values))
            invariant = len(distinct) == 1 and not mismatch_blocks
            workload_invariant = workload_invariant and invariant
            fields[field] = {
                "invariant": invariant,
                "distinct_values": distinct,
                "a_b_mismatch_blocks": mismatch_blocks,
            }
        phases[phase_key] = fields

    timing_ratios = []
    for block in blocks:
        pair = block["pair"]
        timing_ratios.append(
            {
                "block": block["block"],
                "complete_gi_B_over_A": float(pair["B"]["complete_gi_gpu_us"])
                / float(pair["A"]["complete_gi_gpu_us"]),
                "complete_renderer_B_over_A": float(pair["B"]["complete_renderer_gpu_us"])
                / float(pair["A"]["complete_renderer_gpu_us"]),
            }
        )

    return {
        "workload_invariant": workload_invariant,
        "phase_fields": phases,
        "timing_ratios_diagnostic_only": timing_ratios,
        "interpretation": (
            "integer workload counters are invariant; residual v6 timing noise is not explained by measured workload-count drift"
            if workload_invariant
            else "integer workload counters vary; investigate moving-rigid workload nondeterminism before further timing calibration"
        ),
    }
