#!/usr/bin/env python3
"""M1 step 3: tables from scripts/m1_dynamic.sh (dynamic Sponza, light switch, cold start).

Usage: python scripts/m1_dynamic_summary.py out/m1/dyn1 [--json FILE]
The cold-start table needs out/m1/dyn1/cold-<n>/reference.json (compare_ref, run after the GPU jobs).
"""
import json
import os
import sys

d = sys.argv[1]
out_json = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None


def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


res = {"kind": "exploratory (探索値)", "source": d, "dynamic": [], "switch": [], "cold": []}
names = sorted(f[:-13] for f in os.listdir(os.path.join(d, "dyn-nosky")) if f.endswith(".summary.json"))
print("| config | GI ms static cam (mean) | moving cam | vox | field | flicker static cam sun/sky | moving sun/sky | toon fine static/moving | ramp change static/moving (control) |")
print("|---|---|---|---|---|---|---|---|---|")
for n in names:
    a = load(os.path.join(d, "dyn-nosky", n + ".summary.json"))
    b = load(os.path.join(d, "dyn-sky", n + ".summary.json"))
    st, mv = a["static"], a["moving"]
    row = {
        "config": n,
        "giStaticMean": st["timing"]["giTotal"]["mean"], "giStaticMedian": st["timing"]["giTotal"]["median"],
        "giMovingMean": mv["timing"]["giTotal"]["mean"], "voxMean": st["timing"]["vox"]["mean"],
        "fieldMean": st["timing"]["giSum"]["mean"],
        "flickerStaticSun": st["flicker"]["photoFinePct"], "flickerStaticSky": b["static"]["flicker"]["photoFinePct"] if b else None,
        "flickerMovingSun": mv["flicker"]["photoFinePct"], "flickerMovingSky": b["moving"]["flicker"]["photoFinePct"] if b else None,
        "toonFineStatic": st["flicker"]["toonFinePct"], "toonFineMoving": mv["flicker"]["toonFinePct"],
        "rampChangeStatic": st["flicker"]["toonRampChangePct"], "rampChangeMoving": mv["flicker"]["toonRampChangePct"],
        "rampControlMoving": mv["flicker"]["controlRampChangePct"],
    }
    res["dynamic"].append(row)
    print(f"| {n} | {row['giStaticMean']:.2f} | {row['giMovingMean']:.2f} | {row['voxMean']:.3f} | {row['fieldMean']:.2f} | "
          f"{row['flickerStaticSun']} / {row['flickerStaticSky']} | {row['flickerMovingSun']} / {row['flickerMovingSky']} | "
          f"{row['toonFineStatic']} / {row['toonFineMoving']} | {row['rampChangeStatic']} / {row['rampChangeMoving']} ({row['rampControlMoving']}) |")

print("\n| config | frames to 50% | frames to 90% | curve (frames 1..10 after the switch) |")
print("|---|---|---|---|")
for f in sorted(os.listdir(os.path.join(d, "switch"))):
    if not f.endswith(".response.json"):
        continue
    r = load(os.path.join(d, "switch", f))
    res["switch"].append({"config": r["config"], "frames50": r["frames50"], "frames90": r["frames90"], "curve": r["curve"]})
    print(f"| {r['config']} | {r['frames50']} | {r['frames90']} | {', '.join(str(round(c, 3)) for c in r['curve'][:10])} |")

cold = {}
for e in sorted(os.listdir(d)):
    if not e.startswith("cold-") or not os.path.isdir(os.path.join(d, e)):
        continue
    n = int(e[5:])
    ref = load(os.path.join(d, e, "reference.json"))
    if not ref:
        continue
    for k, v in ref["results"].items():
        cold.setdefault(k.replace(".static.irr.f32", ""), {})[n] = v
if cold:
    ns = sorted({n for v in cold.values() for n in v})
    print("\n| config (cold start) | " + " | ".join(f"{n} fr" for n in ns) + " |")
    print("|---|" + "---|" * len(ns))
    for c, v in sorted(cold.items()):
        res["cold"].append({"config": c, "byFrames": {str(n): v[n] for n in ns if n in v}})
        print(f"| {c} | " + " | ".join(f"{v[n]['meanAbsRel']:.3f} ({v[n]['bias'] * 100:+.0f}%)" if n in v else "" for n in ns) + " |")
if out_json:
    with open(out_json, "w") as f:
        json.dump(res, f, indent=1)
