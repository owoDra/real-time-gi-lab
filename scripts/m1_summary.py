#!/usr/bin/env python3
"""M1: one table per sweep directory (scripts/m1_sweep.sh): cost, error against Mitsuba, flicker and leakage per config.

Usage: python scripts/m1_summary.py box/out/m1/sweep1 [--json docs/reference/measurements/<phase>/sweep.json]
Times are GPU timestamp medians of one run (exploratory values). 'field' is the GI without the voxel rebuild
(build + trace + merge + gather); the rebuild is the same for every config.
"""
import json
import os
import sys

d = sys.argv[1]
out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


ref = {s: (load(os.path.join(d, s, "reference.json")) or {}).get("results", {}) for s in ("nosky", "sky")}
names = sorted({f[: -len(".summary.json")] for f in os.listdir(os.path.join(d, "nosky")) if f.endswith(".summary.json")})
rows = []
for n in names:
    a = load(os.path.join(d, "nosky", n + ".summary.json"))
    b = load(os.path.join(d, "sky", n + ".summary.json"))
    l1 = load(os.path.join(d, "leak-0.02", n + ".summary.json"))
    l2 = load(os.path.join(d, "leak-0.1", n + ".summary.json"))
    st = a["static"]["timing"]
    rn = ref["nosky"].get(n + ".static.irr.f32", {})
    rs = ref["sky"].get(n + ".static.irr.f32", {})
    mem = a["allocatedBytes"]
    row = {
        "config": n,
        "probes": a["static"]["counts"][0] if a.get("ddgiDims") else sum(a["static"]["counts"]),
        "fieldMs": round(st["giSum"]["median"], 2),
        "voxMs": round(st["vox"]["median"], 2),
        "totalMs": round(st["giTotal"]["median"], 2),
        "movingTotalMs": round(a["moving"]["timing"]["giTotal"]["median"], 2) if a.get("moving") else None,
        "fieldMiB": round(mem / 2**20, 1),
        "biasSun": rn.get("bias"), "absRelSun": rn.get("meanAbsRel"),
        "biasSky": rs.get("bias"), "absRelSky": rs.get("meanAbsRel"),
        "flickerStaticSun": a["static"]["flicker"]["giFinePct"],
        "flickerMovingSun": a["moving"]["flicker"]["giFinePct"] if a.get("moving") else None,
        "flickerMovingSunCoarse": a["moving"]["flicker"]["giCoarsePct"] if a.get("moving") else None,
        "flickerMovingSky": b["moving"]["flicker"]["giFinePct"] if b and b.get("moving") else None,
        "leak002": round(l1["leak"]["meanFractionOfSun"] * 100, 2) if l1 else None,
        "leak01": round(l2["leak"]["meanFractionOfSun"] * 100, 2) if l2 else None,
        "leak002p99": round(l1["leak"]["p99Irradiance"], 3) if l1 else None,
    }
    rows.append(row)

rows.sort(key=lambda r: (not r["config"].startswith("ddgi"), r["fieldMs"]))
cols = ["config", "probes", "fieldMs", "totalMs", "fieldMiB", "biasSun", "absRelSun", "biasSky", "absRelSky",
        "flickerStaticSun", "flickerMovingSun", "flickerMovingSky", "leak002", "leak01"]
print("| " + " | ".join(cols) + " |")
print("|" + "---|" * len(cols))
for r in rows:
    print("| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |")
if out_json:
    with open(out_json, "w") as f:
        json.dump({"kind": "exploratory (探索値)", "source": d, "rows": rows}, f, indent=1)
