from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable, Mapping, Sequence


MUTATING_OPERATIONS = frozenset({
    "allocate",
    "reallocate",
    "geometry_upload",
    "build",
    "rebuild",
    "update",
    "write",
})


@dataclass(frozen=True)
class TopologyStep:
    index: int
    primitive_count: int
    topology_seed: int
    replacement_count: int


@dataclass(frozen=True)
class MutationEvent:
    owner_id: str
    operation: str


@dataclass(frozen=True)
class AllocationLifetime:
    name: str
    owner_id: str
    bytes: int
    birth_phase: int
    death_phase: int


def xorshift32(value: int) -> int:
    value &= 0xFFFFFFFF
    value ^= (value << 13) & 0xFFFFFFFF
    value ^= value >> 17
    value ^= (value << 5) & 0xFFFFFFFF
    return value & 0xFFFFFFFF


def topology_sequence(
    base_primitive_count: int,
    factors: Sequence[float],
    seed: int,
    replacement_fraction: float,
) -> list[TopologyStep]:
    if base_primitive_count <= 0:
        raise ValueError("base_primitive_count must be positive")
    if len(factors) < 2:
        raise ValueError("at least two primitive-count factors are required")
    if not 0.0 < replacement_fraction <= 1.0:
        raise ValueError("replacement_fraction must be in (0, 1]")

    counts = [max(1, round(base_primitive_count * factor)) for factor in factors]
    if any(left == right for left, right in zip(counts, counts[1:], strict=False)):
        raise ValueError("every H002 transition must change primitive count")

    state = seed & 0xFFFFFFFF
    steps: list[TopologyStep] = []
    previous = counts[0]
    for index, count in enumerate(counts):
        state = xorshift32(state or 0xA341316C)
        retained = min(previous, count)
        replacement_count = (
            0 if index == 0 else max(1, round(retained * replacement_fraction))
        )
        steps.append(TopologyStep(index, count, state, replacement_count))
        previous = count
    return steps


def workload_digest(
    steps: Sequence[TopologyStep],
    *,
    producer_contract: str,
    hit_contract: str,
    storage_contract: str,
) -> str:
    payload = {
        "producer_contract": producer_contract,
        "hit_contract": hit_contract,
        "storage_contract": storage_contract,
        "steps": [
            {
                "index": step.index,
                "primitive_count": step.primitive_count,
                "topology_seed": step.topology_seed,
                "replacement_count": step.replacement_count,
            }
            for step in steps
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_object_local_mutations(
    events: Iterable[MutationEvent],
    *,
    changed_object_id: str,
    immutable_owner_ids: Iterable[str],
) -> None:
    immutable = frozenset(immutable_owner_ids)
    if changed_object_id in immutable:
        raise ValueError("changed object cannot also be immutable")
    for event in events:
        if event.operation in MUTATING_OPERATIONS and event.owner_id != changed_object_id:
            raise ValueError(
                f"mutation escaped object-local boundary: {event.owner_id}:{event.operation}"
            )


def validate_boundary_record(
    record: Mapping[str, object],
    required_fields: Sequence[str],
) -> None:
    missing = [field for field in required_fields if field not in record]
    if missing:
        raise ValueError(f"missing boundary fields: {', '.join(missing)}")
    for field in required_fields:
        value = record[field]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{field} must be numeric")
        if value < 0:
            raise ValueError(f"{field} must be non-negative")


def true_peak_resident_bytes(allocations: Sequence[AllocationLifetime]) -> int:
    if not allocations:
        return 0
    for allocation in allocations:
        if allocation.bytes < 0:
            raise ValueError("allocation bytes must be non-negative")
        if allocation.birth_phase >= allocation.death_phase:
            raise ValueError("allocation lifetime must have positive phase extent")

    phases = sorted({
        phase
        for allocation in allocations
        for phase in (allocation.birth_phase, allocation.death_phase)
    })
    peak = 0
    for phase in phases:
        resident = sum(
            allocation.bytes
            for allocation in allocations
            if allocation.birth_phase <= phase < allocation.death_phase
        )
        peak = max(peak, resident)
    return peak
