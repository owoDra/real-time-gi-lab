#!/usr/bin/env python3
"""N009 WP-PT: run n009_probe_model on an attested GPU capture and score the
preregistered counterfactual ladder R0-R6 against the locked T_B2 indirect
reference (luma; scoring mask = matched primary visibility, as N008 Phase C).

Gates: V1 R0 == GPU indirect (max abs <= 1e-6, 0 positivity disagreements);
V2 re-quantised value == captured contribution (exact or +-1) for >= 99.9 %;
V3 CPU re-trace == GPU secondary hit for >= 99 %; V4 (eligible indirect only)
|relative bias of sum| of R6 <= 3 %."""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "n008_hdr_oracle"))
import n008lib as L  # noqa: E402
import phase_b_ladder as B  # noqa: E402

LUMA = np.array((0.2126, 0.7152, 0.0722))
MODEL = L.ROOT / "build/n009/src/research/n009_scene_contract/n009_probe_model"
STAGES = ("R0", "R1", "R2", "R3", "R4", "R5", "R6")
NAMES = ("gpu_integer_replay", "dequantized", "secondary_shadow", "full_probe_coverage", "unbounded_range",
         "dense_directions", "pixel_cosine_one_bounce")


def load_stages(path: Path):
    raw = path.read_bytes()
    assert raw[:8] == b"N009PM1\0"
    w, h, n = struct.unpack_from("<3I", raw, 8)
    return np.frombuffer(raw, "<f8", offset=20).reshape(n, h, w)


def mask(capture: Path, ref_work: Path, w: int, h: int):
    oh = np.frombuffer((ref_work / "o.hits").read_bytes(), dtype=np.dtype([("t", "<f8"), ("tri", "<u4"), ("front", "<u4")]),
                       offset=16)
    gh = C_hits(capture / "gpu" / "hits.bin", w * h)
    geom = (capture / "geometry-state.bin").read_bytes()
    n = struct.unpack_from("<2I", geom)[1]
    meta = np.frombuffer(geom, dtype=np.dtype([("v", "<f4", (9,)), ("m", "<u4", (4,))]), offset=8)["m"]
    o_hit, g_hit = oh["t"] >= 0, gh["flag"] == 1
    o_prim = np.where(o_hit, meta[np.minimum(oh["tri"], n - 1), 0], 0xFFFFFFFF)
    back_single = o_hit & (meta[np.minimum(oh["tri"], n - 1), 3] == 0) & (oh["front"] == 0)
    return (((o_hit & g_hit & (o_prim == gh["prim"])) | (~o_hit & ~g_hit)) & ~back_single).reshape(h, w)


def C_hits(path: Path, n: int):
    rec = np.frombuffer(path.read_bytes(), dtype=np.dtype([("n", "<f4", (3,)), ("t", "<f4"), ("prim", "<u4"),
                                                           ("mat", "<u4"), ("inst", "<u4"), ("flag", "<u4")]))
    assert rec.size == n
    return rec


def metrics(s, r, m):
    s, r = s[m], r[m]
    out = {"sum": float(s.sum()), "positive": int((s > 0).sum()),
           "energy_on_reference_zero": float(s[r <= 0].sum()), "positive_on_reference_zero": int(((s > 0) & (r <= 0)).sum())}
    if r.sum() > 0:
        out.update({"relative_bias_of_sum": float((s.sum() - r.sum()) / r.sum()),
                    "rmse": float(np.sqrt(np.mean((s - r) ** 2))),
                    "zero_on_reference_positive": int(((s <= 0) & (r > 0)).sum())})
    return out


def analyse(capture: Path, ref_work: Path, classification: str, out: Path, stages_used: int, dense: int, cos_spp: int):
    subprocess.run([str(MODEL), "--state", str(capture), "--capture", str(capture), "--out", str(out),
                    "--dense", str(dense), "--cos-spp", str(cos_spp)], check=True, capture_output=True, text=True)
    info = json.loads(Path(str(out) + ".json").read_text())
    st = load_stages(Path(str(out) + ".stages.f64"))
    _, h, w = st.shape
    gpu = L.read_pfm(capture / "gpu" / "indirect.pfm")[..., 0]
    runs = [L.read_sidecar(Path(str(B.level_prefix(ref_work, i, B.LEVELS[-1])) + ".f64")) for i in range(4)]
    ref = (sum(r["mean"] for r in runs) / 4)[..., L.COMPONENTS.index("indirect"), :] @ LUMA
    m = mask(capture, ref_work, w, h)
    d0 = np.abs(st[0] - gpu)
    q = info["quantization_check"]
    gates = {"V1": bool(d0.max() <= 1e-6 and ((st[0] > 0) != (gpu > 0)).sum() == 0),
             "V1_max_abs": float(d0.max()),
             "V2": (q["exact"] + q["off_by_one"]) >= 0.999 * info["work_items"],
             "V3": info["cpu_retrace_matches_gpu_hit"] >= 0.99 * info["work_items"]}
    eligible = classification == "STATISTICALLY_ELIGIBLE"
    rows = []
    for k in range(stages_used):
        row = {"stage": STAGES[k], "name": NAMES[k], **metrics(st[k], ref, m)}
        if k:
            prev = rows[-1]
            for key in ("relative_bias_of_sum", "sum", "energy_on_reference_zero", "zero_on_reference_positive"):
                if key in row and key in prev:
                    row["delta_" + key] = row[key] - prev[key]
        rows.append(row)
    if eligible and stages_used == 7:
        gates["V4_R6_relative_bias"] = rows[6]["relative_bias_of_sum"]
        gates["V4"] = abs(rows[6]["relative_bias_of_sum"]) <= 0.03
    gates_pass = gates["V1"] and gates["V2"] and gates["V3"] and gates.get("V4", True)
    transitions = [r for r in rows[1:] if "delta_relative_bias_of_sum" in r]
    dominant = max(transitions, key=lambda r: abs(r["delta_relative_bias_of_sum"]))["stage"] if transitions else None
    if not eligible:  # leak cells: dominant = largest absolute energy change on reference-zero pixels
        tr = [r for r in rows[1:] if "delta_energy_on_reference_zero" in r]
        dominant = max(tr, key=lambda r: abs(r["delta_energy_on_reference_zero"]))["stage"] if tr else None
    return {"capture": capture.name, "reference": str(ref_work.relative_to(L.ROOT)), "reference_classification": classification,
            "scoring_mask_pixels": int(m.sum()), "model": info, "gates": gates,
            "attribution": "COMPLETE" if gates_pass else "INCOMPLETE", "dominant_transition": dominant, "stages": rows}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job", action="append", required=True,
                    help="capture_dir:reference_work_dir:classification[:stages]  (stages default 7)")
    ap.add_argument("--work", type=Path, default=L.ROOT / "out/research/n009-scene-contract/probe-model")
    ap.add_argument("--dense", type=int, default=256)
    ap.add_argument("--cos-spp", type=int, default=1024)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    results = []
    for job in a.job:
        parts = job.split(":")
        cap, ref, cls = Path(parts[0]), Path(parts[1]), parts[2]
        n = int(parts[3]) if len(parts) > 3 else 7
        r = analyse(cap.resolve(), ref.resolve(), cls, a.work / cap.name, n, a.dense, a.cos_spp)
        results.append(r)
        print(cap.name, r["attribution"], r["dominant_transition"],
              [round(s.get("relative_bias_of_sum", float("nan")), 4) for s in r["stages"]], flush=True)
    a.output.write_text(json.dumps({"schema": "n009-probe-attribution/1", "dense_directions": a.dense,
                                    "cos_spp": a.cos_spp, "results": results}, indent=1, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
