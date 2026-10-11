#!/usr/bin/env python3
"""N006 P1m1c hit-vs-zero-energy audit. Does not invent new quality labels.

Reuses original, unchanged frozen M1a control and three calibration keys.
Includes strict new GPU-hit readback checks and exact unchanged PFM SHA.
"""
import sys
from run_p1m1a_canonical_probe_pilot import main


if __name__ == "__main__":
    try:
        raise SystemExit(main(
            protocol_version="n006-p1m1c-ray-fate-static-c3-v1",
            output_tag="p1m1c-ray-fate-static-c3",
            summary_file_name="n006-p1m1c-ray-fate-summary.json",
            require_ray_fate=True,
        ))
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        print(f"P1m1c failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
