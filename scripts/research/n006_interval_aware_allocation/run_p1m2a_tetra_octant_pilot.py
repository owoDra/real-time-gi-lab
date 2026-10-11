#!/usr/bin/env python3
"""P1m2a fixed tetra-octant-jitter distribution, calibration-only and unsigned.

Isolated alternative to M1a's immutable P1a uniform-sphere directions.
Preserves frozen 3 static/C3 keys, exact +4 rays, canonical and CPU hit checks.
"""
import sys
from run_p1m1a_canonical_probe_pilot import main


if __name__ == "__main__":
    try:
        raise SystemExit(main(
            protocol_version="n006-p1m2a-tetra-octant-jitter-static-c3-v1",
            output_tag="p1m2a-tetra-octant-static-c3",
            summary_file_name="n006-p1m2a-tetra-octant-summary.json",
            require_ray_fate=True,
            direction_mode="p1m2a-tetra",
            frozen_null=False,
        ))
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        print(f"P1m2a failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
