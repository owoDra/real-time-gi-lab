from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
from typing import Iterable, Mapping, Sequence

A001_MAGIC = b"PHOSRC1\0"
A001_HEADER = struct.Struct("<8s11I4xQ")
A001_ITEM = struct.Struct("<iiiIIIIIffffffff")
A001_HEADER_BYTES = 64
A001_ITEM_BYTES = 64
A001_SCHEMA_VERSION = 1

RAY_T_MIN = 1.0e-4
HIT_ABS_TOL = 2.0e-4
HIT_REL_TOL = 2.0e-5
INVALID_ID = 0xFFFFFFFF

MUTATING_OPERATIONS = frozenset({
    "allocate", "reallocate", "geometry_upload", "build", "rebuild",
    "refit", "update", "write", "release", "ownership_change",
})


@dataclass(frozen=True)
class TopologyStep:
    index: int
    primitive_count: int
    topology_seed: int
    replacement_count: int
    locality: str


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
    allocation_class: str = "persistent"


@dataclass(frozen=True)
class Ray:
    origin: tuple[float, float, float]
    direction: tuple[float, float, float]
    t_max: float


@dataclass(frozen=True)
class Triangle:
    v0: tuple[float, float, float]
    v1: tuple[float, float, float]
    v2: tuple[float, float, float]
    primitive_id: int
    material_id: int = 0
    instance_id: int = 0
    two_sided: bool = True


@dataclass(frozen=True)
class Hit:
    hit: bool = False
    t: float = math.inf
    normal: tuple[float, float, float] = (0.0, 0.0, 0.0)
    primitive_id: int = INVALID_ID
    material_id: int = INVALID_ID
    instance_id: int = INVALID_ID


def xorshift32(value: int) -> int:
    value &= 0xFFFFFFFF
    value ^= (value << 13) & 0xFFFFFFFF
    value ^= value >> 17
    value ^= (value << 5) & 0xFFFFFFFF
    return value & 0xFFFFFFFF


def profile_seed(master_seed: int, profile_index: int) -> int:
    state = (master_seed ^ ((profile_index + 1) * 0x9E3779B9)) & 0xFFFFFFFF
    return xorshift32(state or 0xA341316C)


def topology_sequence(
    base_primitive_count: int,
    factors: Sequence[float],
    seed: int,
    replacement_fraction: float,
    locality: str,
) -> list[TopologyStep]:
    if base_primitive_count <= 0:
        raise ValueError("base_primitive_count must be positive")
    if len(factors) < 2:
        raise ValueError("at least two primitive-count factors are required")
    if not 0.0 < replacement_fraction <= 1.0:
        raise ValueError("replacement_fraction must be in (0, 1]")
    if locality not in {"global", "local"}:
        raise ValueError("locality must be global or local")

    counts = [max(1, round(base_primitive_count * factor)) for factor in factors]
    if any(a == b for a, b in zip(counts, counts[1:], strict=False)):
        raise ValueError("every J002 transition must change primitive count")

    state = seed & 0xFFFFFFFF
    previous = counts[0]
    steps: list[TopologyStep] = []
    for index, count in enumerate(counts):
        state = xorshift32(state or 0xA341316C)
        retained = min(previous, count)
        replacement = 0 if index == 0 else max(
            1, round(retained * replacement_fraction)
        )
        steps.append(
            TopologyStep(index, count, state, replacement, locality)
        )
        previous = count
    return steps


def topology_digest(
    profile_name: str,
    steps: Sequence[TopologyStep],
) -> str:
    payload = {
        "profile": profile_name,
        "steps": [
            {
                "index": step.index,
                "primitive_count": step.primitive_count,
                "topology_seed": step.topology_seed,
                "replacement_count": step.replacement_count,
                "locality": step.locality,
            }
            for step in steps
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_transition_identity(
    records: Sequence[Mapping[str, object]],
) -> None:
    if len(records) < 2:
        raise ValueError("at least two materialized snapshots are required")
    for previous, current in zip(records, records[1:], strict=False):
        if int(previous["primitive_count"]) == int(current["primitive_count"]):
            raise ValueError(
                "measured transition did not change primitive count"
            )
        if str(previous["snapshot_digest"]) == str(current["snapshot_digest"]):
            raise ValueError(
                "measured transition did not change geometry snapshot"
            )


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
        if (
            event.operation in MUTATING_OPERATIONS
            and event.owner_id != changed_object_id
        ):
            raise ValueError(
                "mutation escaped object-local boundary: "
                f"{event.owner_id}:{event.operation}"
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
        if not math.isfinite(float(value)) or float(value) < 0.0:
            raise ValueError(f"{field} must be finite and non-negative")


def true_peak_resident_bytes(
    allocations: Sequence[AllocationLifetime],
) -> int:
    if not allocations:
        return 0
    for allocation in allocations:
        if allocation.bytes < 0:
            raise ValueError("allocation bytes must be non-negative")
        if allocation.birth_phase >= allocation.death_phase:
            raise ValueError(
                "allocation lifetime must have positive phase extent"
            )
    phases = sorted({
        phase
        for allocation in allocations
        for phase in (allocation.birth_phase, allocation.death_phase)
    })
    return max(
        sum(
            allocation.bytes
            for allocation in allocations
            if allocation.birth_phase <= phase < allocation.death_phase
        )
        for phase in phases
    )


def allocation_class_bytes(
    allocations: Sequence[AllocationLifetime],
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for allocation in allocations:
        totals[allocation.allocation_class] = (
            totals.get(allocation.allocation_class, 0) + allocation.bytes
        )
    return totals


def lane_a_workload_id(data: bytes) -> int:
    value = 1469598103934665603
    for byte in data:
        value ^= byte
        value = (value * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return value


def parse_lane_a_stream(data: bytes) -> dict[str, object]:
    if len(data) < A001_HEADER_BYTES:
        raise ValueError("Lane A stream is smaller than header")
    fields = A001_HEADER.unpack_from(data, 0)
    (
        magic,
        schema,
        header_bytes,
        item_bytes,
        frame_id,
        item_count,
        output_count,
        cascade_count,
        rays_per_probe,
        tile_width,
        tile_height,
        reserved0,
        workload_id,
    ) = fields
    if magic != A001_MAGIC or schema != A001_SCHEMA_VERSION:
        raise ValueError("Lane A stream magic/schema mismatch")
    if (
        header_bytes != A001_HEADER_BYTES
        or item_bytes != A001_ITEM_BYTES
    ):
        raise ValueError("Lane A stream layout mismatch")
    if (
        reserved0 != 0
        or min(
            cascade_count,
            rays_per_probe,
            tile_width,
            tile_height,
        ) <= 0
    ):
        raise ValueError("Lane A stream header dimensions are invalid")
    expected = header_bytes + item_count * item_bytes
    if len(data) != expected:
        raise ValueError("Lane A stream byte size mismatch")
    payload = data[header_bytes:]
    actual = lane_a_workload_id(payload)
    if actual != workload_id:
        raise ValueError("Lane A workload_id mismatch")
    return {
        "schema_version": schema,
        "frame_id": frame_id,
        "item_count": item_count,
        "output_count": output_count,
        "cascade_count": cascade_count,
        "rays_per_probe": rays_per_probe,
        "tile_width": tile_width,
        "tile_height": tile_height,
        "workload_id": workload_id,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }


def _dot(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _length(value: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(value, value))


def _normalize(
    value: tuple[float, float, float],
) -> tuple[float, float, float]:
    length = _length(value)
    if length <= 0.0:
        return (0.0, 0.0, 0.0)
    return (
        value[0] / length,
        value[1] / length,
        value[2] / length,
    )


def normalize_ray(ray: Ray) -> Ray | None:
    length = _length(ray.direction)
    if (
        not math.isfinite(length)
        or length <= 1.0e-8
        or not math.isfinite(ray.t_max)
        or ray.t_max <= RAY_T_MIN
    ):
        return None
    return Ray(
        ray.origin,
        (
            ray.direction[0] / length,
            ray.direction[1] / length,
            ray.direction[2] / length,
        ),
        ray.t_max,
    )


def intersect_triangle(
    triangle: Triangle,
    ray: Ray,
    best_t: float,
) -> Hit | None:
    e1 = _sub(triangle.v1, triangle.v0)
    e2 = _sub(triangle.v2, triangle.v0)
    p = _cross(ray.direction, e2)
    det = _dot(e1, p)
    if (
        abs(det) < 1.0e-8
        if triangle.two_sided
        else det <= 1.0e-8
    ):
        return None
    inverse = 1.0 / det
    tv = _sub(ray.origin, triangle.v0)
    u = _dot(tv, p) * inverse
    if u < 0.0 or u > 1.0:
        return None
    q = _cross(tv, e1)
    v = _dot(ray.direction, q) * inverse
    if v < 0.0 or u + v > 1.0:
        return None
    distance = _dot(e2, q) * inverse
    tolerance = max(
        HIT_ABS_TOL,
        abs(best_t) * HIT_REL_TOL,
    )
    if (
        distance < RAY_T_MIN
        or distance > ray.t_max
        or distance > best_t + tolerance
    ):
        return None
    return Hit(
        True,
        distance,
        _normalize(_cross(e1, e2)),
        triangle.primitive_id,
        triangle.material_id,
        triangle.instance_id,
    )


def prefer_hit(candidate: Hit, current: Hit) -> bool:
    if not candidate.hit:
        return False
    if not current.hit:
        return True
    tolerance = max(
        HIT_ABS_TOL,
        abs(current.t) * HIT_REL_TOL,
    )
    return (
        candidate.t < current.t - tolerance
        or (
            abs(candidate.t - current.t) <= tolerance
            and candidate.primitive_id < current.primitive_id
        )
    )


def trace_reference(
    triangles: Sequence[Triangle],
    ray: Ray,
) -> Hit:
    normalized = normalize_ray(ray)
    if normalized is None:
        return Hit()
    best = Hit()
    for triangle in triangles:
        candidate = intersect_triangle(
            triangle,
            normalized,
            best.t if best.hit else normalized.t_max,
        )
        if candidate is not None and prefer_hit(candidate, best):
            best = candidate
    return best


def equivalent_hit(expected: Hit, actual: Hit) -> bool:
    if expected.hit != actual.hit:
        return False
    if not expected.hit:
        return (
            math.isinf(actual.t)
            and actual.primitive_id == INVALID_ID
            and actual.material_id == INVALID_ID
            and actual.instance_id == INVALID_ID
        )
    tolerance = max(
        HIT_ABS_TOL,
        abs(expected.t) * HIT_REL_TOL,
    )
    expected_normal = _normalize(expected.normal)
    actual_normal = _normalize(actual.normal)
    return (
        abs(expected.t - actual.t) <= tolerance
        and expected.primitive_id == actual.primitive_id
        and expected.material_id == actual.material_id
        and expected.instance_id == actual.instance_id
        and _dot(expected_normal, actual_normal) > 0.9999
    )
