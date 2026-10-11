#!/usr/bin/env python3
"""C0 source-arithmetic numerical risk: float32 divide vs reciprocal multiply.

CPU IEEE-754 float32 storage roundoff model; NOT compiled GPU SPIR-V and NOT
a benchmark of ray-AABB execution or physical GPU instruction costs.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import random
import struct

ROOT = Path(__file__).resolve().parents[3]
SEED = 6006
SAMPLES = 200000

def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]

def audit(seed: int = SEED, samples: int = SAMPLES) -> dict:
    rng = random.Random(seed)
    differences = 0
    first: dict | None = None
    for index in range(samples):
        origin = f32(rng.uniform(-3.0, 3.0))
        minimum = f32(origin + f32(rng.uniform(0.0001, 100.0)))
        direction = f32(rng.uniform(0.0005, 10.0))
        numerator = f32(minimum - origin)
        direct = f32(numerator / direction)
        reciprocal = f32(numerator * f32(1.0 / direction))
        if not (math.isfinite(direct) and math.isfinite(reciprocal) and
                direct > 1.0e-4 and reciprocal > 1.0e-4):
            continue
        if direct != reciprocal:
            differences += 1
            if first is None:
                # Construct ray endpoint exactly on the smaller f32 enter
                # value. Valid y/z slabs are parallel and contain ray origin,
                # so only the x slab decides. This is an existence proof,
                # NOT a frequency estimate for real Sponza work.
                tmax = min(direct, reciprocal)
                maximum = f32(minimum + f32(direction * 4.0))
                exit_direct = f32(f32(maximum - origin) / direction)
                exit_reciprocal = f32(f32(maximum - origin) *
                                      f32(1.0 / direction))
                if min(exit_direct, exit_reciprocal) <= tmax:
                    raise ValueError("constructed AABB exit invalid")
                first = {
                    "sample_index": index,
                    "origin_x": origin, "bounds_min_x": minimum,
                    "bounds_max_x": maximum, "ray_direction_x": direction,
                    "tmax": tmax, "enter_direct_division": direct,
                    "enter_reciprocal_multiply": reciprocal,
                    "direct_accepts": direct <= tmax,
                    "reciprocal_accepts": reciprocal <= tmax,
                    "x_exit_division": exit_direct,
                    "x_exit_reciprocal": exit_reciprocal,
                }
    if first is None or first["direct_accepts"] == first["reciprocal_accepts"]:
        raise ValueError("no valid slab-decision counterexample found")
    return {
        "experiment": "n006-p1l-c0-f32-division-risk-v1",
        "not_gpu_timing_or_gpu_parity": True,
        "seed": seed, "samples": samples, "different_float32_enters": differences,
        "different_enter_fraction": differences / samples,
        "first_constructed_decision_flip": first,
        "interpretation": "Denominator reciprocal replacement is not bit-exact "
                          "in this CPU float32 rounding model. It is NOT "
                          "evidence of the compiler's or GPU's actual lowering.",
    }

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--samples", type=int, default=SAMPLES)
    p.add_argument("--seed", type=int, default=SEED)
    p.add_argument("--out", type=Path,
                   default=ROOT / "out/research/n006-interval-aware-allocation/"
                                  "p1l-c0-floating-divide-risk.json")
    args = p.parse_args()
    if args.samples <= 0 or args.samples > 2000000:
        raise ValueError("samples must be within 1..2000000")
    result = audit(args.seed, args.samples)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
