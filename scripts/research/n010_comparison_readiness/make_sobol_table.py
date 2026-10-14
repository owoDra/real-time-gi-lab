#!/usr/bin/env python3
"""Generate fixed, nested, unrandomised directions; runtime applies digital shifts."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import qmc

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.output.exists():
        raise SystemExit("refuse to replace an existing direction table")
    points = qmc.Sobol(d=16, scramble=False, bits=32).random_base2(m=18)
    values = (points * (2**32)).astype("<u4")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(b"N010NET1" + struct.pack("<2I", 16, 262144) + values.tobytes())
    a.output.with_suffix(".json").write_text(json.dumps({
        "schema": "n010-sobol-table/1", "scipy": scipy.__version__, "numpy": np.__version__,
        "bits": 32, "dimensions": 16, "samples": 262144, "scramble_in_table": False,
        "runtime_randomization": "per-replicate/per-pixel/per-dimension digital xor shift",
        "sha256": hashlib.sha256(a.output.read_bytes()).hexdigest()
    }, indent=2) + "\n")
