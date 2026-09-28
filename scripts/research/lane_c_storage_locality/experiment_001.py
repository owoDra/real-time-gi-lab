#!/usr/bin/env python3
"""C001a: representation-only structural/correctness bring-up.

This intentionally records no wall-clock/GPU timing. It exists to reject broken
or structurally implausible storage candidates before the Vulkan comparison.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path

Probe = tuple[int, int, int, int]  # cascade, x, y, z
Brick = tuple[int, int, int, int]


def next_pow2(v: int) -> int:
    return 1 << max(0, (v - 1).bit_length())


def split_probe(p: Probe, edge: int) -> tuple[Brick, int]:
    c, x, y, z = p
    b = (c, x // edge, y // edge, z // edge)
    local = x % edge + edge * ((y % edge) + edge * (z % edge))
    return b, local


def payload(p: Probe) -> int:
    c, x, y, z = p
    v = ((c + 1) * 0x9E3779B1) ^ (x * 0x85EBCA77) ^ (y * 0xC2B2AE3D) ^ (z * 0x27D4EB2F)
    return (v & 0xFFFFFFFF) or 1


def generate(cascades: int, dims: tuple[int, int, int], edge: int, occupancy: int) -> list[Probe]:
    dx, dy, dz = dims
    # Multiplication by 37 permutes 0..63 for edge=4, avoiding a spatially
    # clustered occupancy pattern without changing query ordering afterward.
    locals_ = [((i * 37) % (edge ** 3)) for i in range(occupancy)]
    out: list[Probe] = []
    for c in range(cascades):
        for bz in range(dz):
            for by in range(dy):
                for bx in range(dx):
                    for local in locals_:
                        lx = local % edge
                        ly = (local // edge) % edge
                        lz = local // (edge * edge)
                        out.append((c, bx * edge + lx, by * edge + ly, bz * edge + lz))
    return out


class ProbeHashModel:
    def __init__(self, probes: int):
        self.capacity = next_pow2(max(2, probes * 2))
        self.data: dict[Probe, int] = {}

    def upsert(self, p: Probe, value: int) -> None:
        self.data[p] = value

    def lookup(self, p: Probe) -> int | None:
        return self.data.get(p)

    def invalidate(self, p: Probe) -> None:
        self.data.pop(p, None)

    @property
    def persistent_bytes(self) -> int:
        return self.capacity * 16  # packed key/value slot model


class HashedBrickPoolModel:
    def __init__(self, bricks: int, edge: int):
        self.edge = edge
        self.dir_capacity = next_pow2(max(2, bricks * 2))
        self.data: dict[Brick, list[int]] = {}

    def upsert(self, p: Probe, value: int) -> None:
        b, local = split_probe(p, self.edge)
        self.data.setdefault(b, [0] * (self.edge ** 3))[local] = value

    def lookup(self, p: Probe) -> int | None:
        b, local = split_probe(p, self.edge)
        brick = self.data.get(b)
        return None if brick is None or brick[local] == 0 else brick[local]

    def invalidate(self, p: Probe) -> None:
        b, local = split_probe(p, self.edge)
        brick = self.data.get(b)
        if brick is None:
            return
        brick[local] = 0
        if not any(brick):
            del self.data[b]

    @property
    def persistent_bytes(self) -> int:
        physical = len(self.data) * ((self.edge ** 3) * 4 + 8 + 4)
        return self.dir_capacity * 16 + physical


class VirtualClipmapModel:
    def __init__(self, cascades: int, edge: int, extent: tuple[int, int, int]):
        self.cascades = cascades
        self.edge = edge
        self.extent = extent
        self.data: dict[Brick, list[int]] = {}

    def _inside(self, b: Brick) -> bool:
        c, x, y, z = b
        ex, ey, ez = self.extent
        return 0 <= c < self.cascades and 0 <= x < ex and 0 <= y < ey and 0 <= z < ez

    def upsert(self, p: Probe, value: int) -> None:
        b, local = split_probe(p, self.edge)
        if not self._inside(b):
            raise ValueError(f"probe outside clipmap: {p}")
        self.data.setdefault(b, [0] * (self.edge ** 3))[local] = value

    def lookup(self, p: Probe) -> int | None:
        b, local = split_probe(p, self.edge)
        brick = self.data.get(b)
        return None if brick is None or brick[local] == 0 else brick[local]

    def invalidate(self, p: Probe) -> None:
        b, local = split_probe(p, self.edge)
        brick = self.data.get(b)
        if brick is None:
            return
        brick[local] = 0
        if not any(brick):
            del self.data[b]

    @property
    def persistent_bytes(self) -> int:
        ex, ey, ez = self.extent
        page_table = self.cascades * ex * ey * ez * 4
        physical = len(self.data) * ((self.edge ** 3) * 4 + 8 + 4)
        return page_table + physical


@dataclass
class Row:
    scenario: str
    representation: str
    occupancy_per_brick: int
    active_probes: int
    active_bricks: int
    persistent_bytes: int
    scratch_bytes: int
    lookup_address_steps: int
    update_address_steps: int
    initial_allocations: int
    motion_evictions_per_frame: int
    motion_invalidations_per_frame: int
    producer_address_terms: int
    correctness: bool


def verify(storage, probes: list[Probe]) -> bool:
    for p in probes:
        storage.upsert(p, payload(p))
    if any(storage.lookup(p) != payload(p) for p in probes):
        return False
    changed = probes[::17]
    for p in changed:
        storage.upsert(p, payload(p) ^ 0xA5A5A5A5)
    if any(storage.lookup(p) != (payload(p) ^ 0xA5A5A5A5) for p in changed):
        return False
    removed = probes[::257]
    for p in removed:
        storage.invalidate(p)
    if any(storage.lookup(p) is not None for p in removed):
        return False
    for p in removed:
        storage.upsert(p, payload(p))
    return all(storage.lookup(p) == payload(p) for p in removed)


def parse3(text: str) -> tuple[int, int, int]:
    values = tuple(int(v) for v in text.split(","))
    if len(values) != 3 or min(values) <= 0:
        raise argparse.ArgumentTypeError("expected x,y,z positive integers")
    return values  # type: ignore[return-value]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cascades", type=int, default=3)
    ap.add_argument("--brick-edge", type=int, default=4)
    ap.add_argument("--brick-dims", type=parse3, default=(12, 12, 4))
    ap.add_argument("--clipmap-dims", type=parse3, default=(24, 24, 8))
    ap.add_argument("--occupancies", default="4,16,48")
    args = ap.parse_args()
    occupancies = [int(v) for v in args.occupancies.split(",")]
    cells = args.brick_edge ** 3
    if any(o <= 0 or o > cells for o in occupancies):
        ap.error(f"occupancy must be in [1,{cells}]")
    if any(args.clipmap_dims[i] < args.brick_dims[i] for i in range(3)):
        ap.error("clipmap must contain active brick window")

    active_bricks = args.cascades * math.prod(args.brick_dims)
    _, dy, dz = args.brick_dims
    leaving_bricks = args.cascades * dy * dz
    rows: list[Row] = []

    for occ in occupancies:
        probes = generate(args.cascades, args.brick_dims, args.brick_edge, occ)
        scenario = "sparse" if occ <= 4 else "medium" if occ <= 16 else "dense"
        variants = [
            ("probe-hash", ProbeHashModel(len(probes)), 1, 1, 1, len(probes), leaving_bricks * occ),
            ("hashed-brick-pool", HashedBrickPoolModel(active_bricks, args.brick_edge), 2, 2, 2, active_bricks, leaving_bricks),
            ("virtual-clipmap", VirtualClipmapModel(args.cascades, args.brick_edge, args.clipmap_dims), 1, 1, 4, active_bricks, leaving_bricks),
        ]
        for name, storage, lookup_steps, update_steps, producer_terms, allocations, evictions in variants:
            ok = verify(storage, probes)
            rows.append(Row(
                scenario, name, occ, len(probes), active_bricks,
                storage.persistent_bytes, 0, lookup_steps, update_steps,
                allocations, evictions, evictions, producer_terms, ok,
            ))

    if not all(r.correctness for r in rows):
        raise SystemExit("correctness gate failed")

    artifact = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    out = Path(artifact) if artifact else Path("out/research/lane-c-storage-locality/001-storage-baselines/manual")
    out.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]))
    with (out / "storage_baselines.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(r) for r in rows)
    summary = {
        "schema_version": 1,
        "experiment": "001-storage-baselines",
        "evidence_scope": "synthetic structural/correctness bring-up; not GPU timing evidence",
        "ordering": "unmodified representation-only axis",
        "config": vars(args),
        "rows": [asdict(r) for r in rows],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print("C001a structural/correctness bring-up; no GPU timing claim")
    for r in rows:
        print(f"{r.scenario},{r.representation},bytes={r.persistent_bytes},evict={r.motion_evictions_per_frame},correct={str(r.correctness).lower()}")
    print(f"artifact_dir={out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
