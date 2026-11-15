"""Phase 34: applies the judgement rules of docs/spec/60-confirmation.md to the outputs of scripts/p34_confirm.sh.

Usage: python scripts/p34_judge.py [--out docs/reference/measurements/finish/phase34-confirmation.json]
Reads box/out/p34/run/. Every claim gets "holds": true / false (成立 / 不成立) by the rule written before the run.
Ratio claims also get "withinMde": true when the median ratio is within the neutral control's MDE of the threshold
(the verdict still stands; the flag says the margin is inside the run-to-run spread)."""
import argparse
import glob
import json
import math
import os
import statistics as st

R = "box/out/p34/run"
Q, T, C = f"{R}/quality", f"{R}/timing", f"{R}/compare"
RC, RCOBJ = "world-48-voxel-rc2-vrel", "world-48-voxel-rc2-vrel-obj"
DL, DH = "ddgi-100-128-u8-g1-noadapt", "ddgi-100-128-u8-h0.5-g1-noadapt"
DF1, DF2 = "ddgi-150-64-u1-h0.8-g1-noadapt", "ddgi-125-64-u2-h0.5-g1-noadapt"
GL = "gl2-8-8"
N64 = "sponza-dynobj-n64-deform"
MB128_MIB = 128e6 / 2**20  # 128 MB = 128 x 10^6 bytes = 122.07 MiB


def js(p):
    with open(p) as f:
        return json.load(f)


def summ(d, c):
    return js(f"{d}/{c}.summary.json")


def gi(d, c, mode="static"):
    s = summ(d, c)
    return s[mode]["timing"]["giTotal"]["median"]


def alloc_mib(d, c):
    s = summ(d, c)
    return (s["allocatedBytes"] + s["voxAllocatedBytes"] + s["dynAllocatedBytes"]) / 2**20


def excess(d, c):
    return summ(d, c)["staticGeo"]["excess"]["k16"]["excessPerFrame"]


def flick(d, c):
    return summ(d, c)["static"]["flicker"]["giFinePct"]


def last_json(p):
    with open(p) as f:
        lines = [l for l in f.read().splitlines() if l.startswith("{")]
    return json.loads(lines[-1])


def ref(name):
    r = js(f"{C}/{name}.json")
    (v,) = r["results"].values()
    return v, r


claims, metrics = {}, {}


def claim(cid, req, text, holds, values, mde_margin=None):
    c = {"requirement": req, "claim": text, "holds": bool(holds), "values": values}
    if mde_margin is not None:
        c["withinMde"] = bool(mde_margin)
    claims[cid] = c


# ---- T1 neutral control (MDE) ----
t1 = [f"{T}/t1/{i}" for i in range(1, 9)]
t1s = [gi(d, RC) for d in t1]
t1m = [gi(d, RC, "moving") for d in t1]
pairs = [t1s[i] / t1s[i + 1] for i in range(0, 8, 2)]
MDE = max(abs(r - 1) for r in pairs)
metrics["T1_neutral"] = {"static": t1s, "moving": t1m, "pairRatios": [round(r, 4) for r in pairs], "mde": round(MDE, 4)}


def ratio_claim(nums, dens, thr):
    rs = [a / b for a, b in zip(nums, dens)]
    m = st.median(rs)
    return m, rs, m <= thr, abs(m - thr) <= MDE


# C1 R1 time and memory, base view
a1 = alloc_mib(t1[0], RC)
claim("C1", "R1", "建物が波打ち物体 64 個が動く場面（sponza-dynobj-n64-deform-bwave）で、RC の GI が 8 回とも静止・移動の中央値 4.0 ms 以下、確保 128 MB 以下（混んだ機械）",
      max(t1s + t1m) <= 4.0 and a1 <= MB128_MIB, {"staticMs": t1s, "movingMs": t1m, "allocMiB": round(a1, 1)})

# C2 R1 held-out view (T2)
t2rc = sorted(glob.glob(f"{T}/t2/*-{RC}"))
t2dl = sorted(glob.glob(f"{T}/t2/*-{DL}"))
s2 = [gi(d, RC) for d in t2rc]
m2 = [gi(d, RC, "moving") for d in t2rc]
a2 = alloc_mib(t2rc[0], RC)
claim("C2", "R1", "同じ場面を探索で使っていない視点（-cam2）で、RC の GI が 4 回とも静止・移動 4.0 ms 以下、確保 128 MB 以下（混んだ機械）",
      max(s2 + m2) <= 4.0 and a2 <= MB128_MIB, {"staticMs": s2, "movingMs": m2, "allocMiB": round(a2, 1)})
metrics["T2_ddgiLinear_cam2"] = {"staticMs": [gi(d, DL) for d in t2dl], "movingMs": [gi(d, DL, "moving") for d in t2dl], "allocMiB": round(alloc_mib(t2dl[0], DL), 1)}

# C3 static flicker 0
f3 = {"sponza": flick(f"{Q}/sponza", RC), "sponza-cam2": flick(f"{Q}/sponza-cam2", RC), "town-cam2": flick(f"{Q}/town-cam2", RC)}
claim("C3", "R4", "何も動かない場面で RC の静止時のちらつき（細帯）が 0（sponza、sponza-cam2、town-cam2）", all(v == 0 for v in f3.values()), f3)

# C4 response
resp = {c: js(f"{Q}/response/{c}.response.json") for c in (RC, DH, DF1, DF2)}
r90 = {c: resp[c]["frames90"] for c in resp}
r50 = {c: resp[c]["frames50"] for c in resp}
claim("C4", "R1", "光源の切り替え（sponza-dyn-switch200）で RC の応答が 90% まで 4 フレーム以内", r90[RC] is not None and r90[RC] <= 4, {"frames90": r90, "frames50": r50})

# C5 advantage over the fast DDGI configs
fast = [c for c in (DH, DF1, DF2) if r90[c] is not None and r90[c] <= 14]
ex5 = {v: {c: excess(f"{Q}/{v}", c) for c in (RC, DL, DH, DF1, DF2)} for v in ("dynobj", "dynobj-cam2")}
fl5 = {v: {c: flick(f"{Q}/{v}", c) for c in (RC, DL, DH, DF1, DF2)} for v in ("sponza", "sponza-cam2")}
ok5 = bool(fast) and all(ex5[v][RC] < ex5[v][c] for v in ex5 for c in fast) and all(fl5[v][RC] < fl5[v][c] for v in fl5 for c in fast)
claim("C5", "R1/R4（優位）", "応答 14 フレーム以下の DDGI 系のどの設定よりも、RC は物体が動く跳び（sponza-dynobj、-cam2）と静止時のちらつき（sponza、-cam2）が小さい",
      ok5, {"fastConfigs": fast, "excessK16": ex5, "staticFlickerPct": fl5})

# C6 building jumps reproduce phase 29
reach = {"town-dynobj-bwave": 0.19359, f"{N64}-bwave": 0.09037, f"{N64}-bcut": 0.0171}
bld = {s: {c: excess(f"{Q}/bld-{s}", c) for c in (RC, DL)} for s in ("town-dynobj-bwave", f"{N64}-bwave", f"{N64}-bcut", f"{N64}-cam2-bwave", "town-dynobj-cam2-bwave")}
claim("C6", "R1/R4", "建物が動く場面の RC の跳びが Phase 29 の到達値の 1.1 倍以内（town 0.194、波打つ Sponza 0.090、現れて消える 0.0171）",
      all(bld[s][RC] <= 1.1 * v for s, v in reach.items()), {s: {"rc": bld[s][RC], "limit": round(1.1 * v, 5)} for s, v in reach.items()})

# C7 limitation: RC jumps more than DDGI linear when the building moves
claim("C7", "R1/R4（限界）", "建物が動く 5 場面（-cam2 の 2 つを含む）のすべてで、RC の跳びは DDGI 線形より大きい（限界の確認）",
      all(bld[s][RC] > bld[s][DL] for s in bld), {s: {"rc": bld[s][RC], "ddgiLinear": bld[s][DL], "ratio": round(bld[s][RC] / bld[s][DL], 2)} for s in bld})

# C8 leak
lk = {t: {c: summ(f"{Q}/leak-{t}", c)["leak"]["meanFractionOfSun"] for c in (RC, DL)} for t in ("0.02", "0.1", "0.05")}
claim("C8", "高品質（光が壁を抜けない）", "閉じた部屋（壁 0.02、0.1、0.05 m）のリークが 3 つとも RC < DDGI 線形", all(lk[t][RC] < lk[t][DL] for t in lk), lk)
metrics["leak_gl2"] = {t: summ(f"{Q}/leak-{t}", GL)["leak"]["meanFractionOfSun"] for t in lk}

# C9 / C10 reference error (8x8 blocks, multi-bounce)
er = {}
for s in ("sponza", "sponza-cam2", "town", "town-cam2"):
    vr, rr = ref(f"ref-{s}-rc")
    vd, _ = ref(f"ref-{s}-ddgi")
    er[s] = {"rc": vr["blocks"]["b8"]["meanAbsRel"], "rcBias": vr["bias"], "ddgiLinear": vd["blocks"]["b8"]["meanAbsRel"], "ddgiBias": vd["bias"],
             "refHalvesB8": rr.get("referenceHalvesBlocks")}
claim("C9", "高品質（誤差）", "town 系（town、town-cam2）では RC の参照との誤差（8×8）が DDGI 線形以下", all(er[s]["rc"] <= er[s]["ddgiLinear"] for s in ("town", "town-cam2")),
      {s: er[s] for s in ("town", "town-cam2")})
claim("C10", "高品質（誤差、限界）", "Sponza 系（sponza、sponza-cam2）では DDGI 線形の誤差（8×8）が RC より小さい（限界の確認）",
      all(er[s]["ddgiLinear"] < er[s]["rc"] for s in ("sponza", "sponza-cam2")), {s: er[s] for s in ("sponza", "sponza-cam2")})

# C11 object pixel bias (O1)
ob = {}
for f in ("0", "100"):
    for k, nm in (("rc", "rc"), ("rcObj", "rcobj"), ("ddgiLinear", "ddgi")):
        v, _ = ref(f"obj-f{f}-{nm}")
        ob.setdefault(f"f{f}", {})[k] = {"pixelBias": v["objects"]["bias"], "b8Bias": v["objects"]["blocks"]["b8"]["bias"]}
lim = {"f0": 0.109, "f100": 0.0745}
ok11 = all(abs(ob[f]["rc"][b]) <= lim[f] for f in lim for b in ("pixelBias", "b8Bias"))
claim("C11", "R5", "動く物体の画素の偏りが、既定の RC で姿勢 0 |偏り| ≤ 10.9%、姿勢 100 ≤ 7.45%（画素と 8×8 の両方）", ok11, ob)
claims["C11"]["objOption"] = all(abs(ob[f]["rcObj"][b]) <= lim[f] for f in lim for b in ("pixelBias", "b8Bias"))

# C12 floor near objects (O2)
fr = {k: [r["ratio"] for r in ref(f"floor-{nm}")[0]["rects"]] for k, nm in (("rc", "rc"), ("rcObj", "rcobj"))}
claim("C12", "R5", "物体の近くの床 4 か所の参照に対する比が、既定の RC で 4 つとも 0.7〜1.4 倍", all(0.7 <= x <= 1.4 for x in fr["rc"]), fr)
claims["C12"]["objOption"] = all(0.7 <= x <= 1.4 for x in fr["rcObj"])

# C13 toon ramp band
tb = {}
for v in ("toon", "toon-cam2"):
    fl = summ(f"{Q}/{v}", RC)["static"]["flicker"]
    tb[v] = {"rampChangePct": fl["toonRampChangePct"], "controlPct": fl["controlRampChangePct"]}
claim("C13", "R4/R5", "トゥーンの物体のランプの帯の切り替わりが、対照の 2 倍以下（sponza-dyn、sponza-dyn-cam2）", all(x["rampChangePct"] <= 2 * x["controlPct"] for x in tb.values()), tb)


# ---- T3 width ----
def t3(c):
    out = {"s": [], "w10": [], "w100": []}
    for k in range(1, 7):
        for w in out:
            out[w].append(gi(f"{T}/t3/{c}/{k}-{w}", c))
    mem = {w: round(alloc_mib(f"{T}/t3/{c}/1-{w}", c), 1) for w in out}
    return out, mem


w_rc, wm_rc = t3(RC)
w_dl, wm_dl = t3(DL)
m14, rs14, ok14, mde14 = ratio_claim(w_rc["w100"], w_rc["w10"], 1.10)
claim("C14", "R2", "RC の広さ 100 倍の GI が 10 倍の 1.1 倍以内（同じ周の比の中央値）、確保が 10 倍の 1.1 倍以内で 128 MB 以下",
      ok14 and wm_rc["w100"] <= 1.1 * wm_rc["w10"] and wm_rc["w100"] <= MB128_MIB,
      {"ms": w_rc, "ratios": [round(r, 4) for r in rs14], "medianRatio": round(m14, 4), "allocMiB": wm_rc}, mde14)
m15, rs15, ok15, mde15 = ratio_claim(w_rc["w100"], w_rc["s"], 1.10)
claim("C15", "R2", "RC の広さ 100 倍の GI が 6 回とも 4.0 ms 以下で、Sponza（同じ物体と建物の動き）の 1.1 倍以内（混んだ機械）",
      ok15 and max(w_rc["w100"]) <= 4.0, {"ratios": [round(r, 4) for r in rs15], "medianRatio": round(m15, 4), "w100MaxMs": max(w_rc["w100"])}, mde15)
metrics["T3_ddgiLinear"] = {"ms": w_dl, "allocMiB": wm_dl, "w100OverW10": round(st.median([a / b for a, b in zip(w_dl["w100"], w_dl["w10"])]), 4),
                            "w100OverS": round(st.median([a / b for a, b in zip(w_dl["w100"], w_dl["s"])]), 4)}


# ---- T4 density ----
def t4(c):
    out = {"s": [], "d": []}
    for k in range(1, 7):
        for w in out:
            out[w].append(gi(f"{T}/t4/{c}/{k}-{w}", c))
    return out


d_rc, d_dl = t4(RC), t4(DL)
m16, rs16, ok16, mde16 = ratio_claim(d_rc["d"], d_rc["s"], 1.25)
claim("C16", "R3", "三角形 10 倍（sponza-dense10-bwave）の RC の GI が sponza-bwave の 1.25 倍以内（同じ周の比の中央値）",
      ok16, {"ms": d_rc, "ratios": [round(r, 4) for r in rs16], "medianRatio": round(m16, 4), "denseMaxMs": max(d_rc["d"])}, mde16)
metrics["T4_ddgiLinear"] = {"ms": d_dl, "medianRatio": round(st.median([a / b for a, b in zip(d_dl["d"], d_dl["s"])]), 4)}


# ---- T5 fly ----
def fly(c):
    out = []
    for d in sorted(glob.glob(f"{T}/t5/*-{c}")):
        t = summ(d, c)["moving"]["timing"]["giTotal"]
        out.append({"median": t["median"], "p99": t["p99"], "max": t["max"], "p99OverMedian": round(t["p99"] / t["median"], 3)})
    return out


f_rc, f_dl = fly(RC), fly(DL)
claim("C17", "R2", "広さ 100 倍を 0.5 m / フレームで飛ぶ道筋で、RC の移動の GI の最大が 3 回とも 4.0 ms 以下、99% 値 ÷ 中央値が 3 回とも 1.2 以下（混んだ機械）",
      all(x["max"] <= 4.0 and x["p99OverMedian"] <= 1.2 for x in f_rc), {"rc": f_rc})
metrics["T5_ddgiLinear"] = f_dl

# C18 overflow
ov = last_json(f"{C}/overflow.log")
claim("C18", "R2", "プールを 3072 ブリックに縮めた飛ぶ道筋で、8×8 ブロックの 95% 以上が十分なプール（12288）の 0.8〜1.25 倍", ov["inRangePct"] >= 95,
      {"inRangePct": ov["inRangePct"], "worstFramePct": ov["worstFramePct"], "blocks": ov["blocks"]})

# ---- T7 browser ----
nat = [f"{T}/t7/{k}-native" for k in (1, 2, 3)]
bro = [f"{T}/t7/{k}-browser" for k in (1, 2, 3)]
bs = [gi(d, RC) for d in bro]
bm = [gi(d, RC, "moving") for d in bro]
ns = [gi(d, RC) for d in nat]
nm = [gi(d, RC, "moving") for d in nat]
claim("C19a", "R6", "ブラウザ（作業機の Brave）で RC の GI が 3 回とも静止・移動 4.0 ms 以下（混んだ機械）", max(bs + bm) <= 4.0, {"browserStaticMs": bs, "browserMovingMs": bm})
br = last_json(f"{C}/browser-rc.log")
claim("C19b", "R6", "ブラウザの画像がネイティブと一致する（間接光の 8 ビットの平均の差 0.5 段以下）", br["indirect"]["meanAbsLevels"] <= 0.5, br)
rb = st.median(bs) / st.median(ns)
claim("C19c", "R6", "ブラウザとネイティブの静止の GI の差が、中立な対照の最小検出差（MDE）以内", abs(rb - 1) <= MDE,
      {"nativeStaticMs": ns, "nativeMovingMs": nm, "browserOverNativeMedian": round(rb, 4), "mde": round(MDE, 4)})

# ---- WebGL2 tier ----
g2b = [js(f"{T}/t7/{k}-gl2/{GL}.summary.json")["timing"]["giTotal"]["median"] for k in (1, 2, 3)]
claim("C20a", "望ましい（WebGL2）", "ブラウザの WebGL2 で sponza の GI が 3 回とも 4.0 ms 以下（混んだ機械）", max(g2b) <= 4.0, {"browserMs": g2b})
g2c = last_json(f"{C}/browser-gl2.log")
claim("C20b", "望ましい（WebGL2）", "ブラウザの WebGL2 の画像がネイティブの WGSL 版と一致する（間接光の 8 ビットの平均の差 0.5 段以下）", g2c["indirect"]["meanAbsLevels"] <= 0.5, g2c)
t6g = [gi(d, GL) for d in sorted(glob.glob(f"{T}/t6/*-{GL}"))]
t6r = [gi(d, RC) for d in sorted(glob.glob(f"{T}/t6/*-{RC}"))]
claim("C20c", "望ましい（WebGL2）", "ネイティブの WGSL 版で建物が波打ち物体 64 個の場面の GI が 3 回とも 4.0 ms 以下（混んだ機械）", max(t6g) <= 4.0,
      {"gl2Ms": t6g, "rcMs": t6r, "gl2AllocMiB": round(alloc_mib(sorted(glob.glob(f"{T}/t6/*-{GL}"))[0], GL), 1)})
claim("C20d", "望ましい（WebGL2）", "WebGL2 版の静止時のちらつきが 0（sponza）", flick(f"{Q}/sponza", GL) == 0, {"staticFlickerPct": flick(f"{Q}/sponza", GL)})
g2t = summ(f"{Q}/toon", GL)["static"]["flicker"]["toonRampChangePct"]
claim("C20e", "望ましい（WebGL2）", "WebGL2 版のトゥーンの帯の切り替わりが、同じ計測の RC の 2 倍以下（sponza-dyn）", g2t <= 2 * tb["toon"]["rampChangePct"],
      {"gl2Pct": g2t, "rcPct": tb["toon"]["rampChangePct"]})

# ---- values reported side by side (no verdict) ----
gv, _ = ref("ref-sponza-gl2")
metrics["reported"] = {
    "referenceErrorB8": er, "gl2SponzaReferenceB8": {"b8": gv["blocks"]["b8"]["meanAbsRel"], "bias": gv["bias"]},
    "objectJumpsK16": ex5, "staticFlickerPct": fl5, "buildingJumpsK16": bld, "leak": lk,
    "objectBias": ob, "floorRatios": fr,
    "movingCameraGeo_t1_first": {k: summ(t1[0], RC)["movingGeo"]["chainExcess"][k] for k in ("excessPerFrame", "controlExcessPerFrame")},
}
for name, dirs in (("T1_rc", t1), ("T7_native", nat)):
    metrics.setdefault("load", {})[name] = [open(f"{d}/log.txt").readline().strip() for d in dirs]

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="docs/reference/measurements/finish/phase34-confirmation.json")
a = ap.parse_args()
res = {"phase": 34, "kind": "confirmation (確認実験): conditions and rules committed before the run, docs/spec/60-confirmation.md",
       "machine": "work machine, AMD Radeon 8060S (RADV), native Dawn/Vulkan; Brave 149 for the browser claims; the machine was busy (user could not free it): absolute GPU times are busy-machine values, the idle-machine judgement is not run (未実行)",
       "mde": round(MDE, 4), "claims": claims, "metrics": metrics}
with open(a.out, "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
for k, c in claims.items():
    print(f"{k:5s} {'成立' if c['holds'] else '不成立'}{' (MDE 内)' if c.get('withinMde') else ''}  {c['claim']}")
