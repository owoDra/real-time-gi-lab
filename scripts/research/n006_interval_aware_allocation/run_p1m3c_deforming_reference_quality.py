#!/usr/bin/env python3
"""P1m3c: prospective deforming-only reference eligibility BEFORE +4 work.

A past moving-rigid CPU reference was black; first determine whether original
N001 independent CPU reference images have sufficient actual radiance signal.
Only then run bounded M0 preselected Q8 +4 treatments and signed quality.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from diagnose_p1m3b_reference_capture import rgb_diagnostic
from run_p1m1a_canonical_probe_pilot import image_delta, read_pfm_payload
from run_p1m3b_moving_rigid_signed_quality import (
    MAX_CASES, MIN_SPP, MAX_SPP, NOISE_RULE,
    reference_pair, rgb_rms, run_case, safe_image,
    select_prospective_holdout,
)

SCENARIO = "deforming-control"
PROTOCOL = "n006-p1m3c-deforming-reference-eligibility-quality-v1"
RESULT_NAME = "n006-p1m3c-deforming-reference-quality-summary.json"


def reference_preflight(folder: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    frame = evidence["frames"][0]
    checks: dict[str, Any] = {}
    buffers = []
    for key in ("reference", "reference_independent"):
        meta = frame.get(key)
        if not isinstance(meta, dict) or meta.get("converged") is not True:
            raise ValueError(f"P1m3c missing converged {key} metadata")
        spp = meta.get("spp")
        if type(spp) is not int or not MIN_SPP <= spp <= MAX_SPP:
            raise ValueError(f"P1m3c {key} invalid N001 reference SPP")
        for field, upper in (("replicate_p99_abs_luminance", 0.001),
                             ("replicate_p99_relative_luminance", 0.01)):
            val = meta.get(field)
            if (type(val) not in (float,int) or
                not math.isfinite(float(val)) or val < 0 or val > upper):
                raise ValueError(f"P1m3c {key} N001 convergence invalid")
        file = safe_image(folder, meta.get("path"))
        blob = file.read_bytes()
        buf = read_pfm_payload(file)
        metrics = rgb_diagnostic(buf)
        checks[key] = {**metrics, **meta,
                       "PFM_SHA256": hashlib.sha256(blob).hexdigest()}
        buffers.append(buf)
    checks["reference_A_B_exact_identical"] = buffers[0] == buffers[1]
    checks["reference_A_B_RMS"] = rgb_rms(buffers[0], buffers[1])
    checks["eligible"] = (
        all(checks[key]["positive_rgb_pixels"] > 0 and
            checks[key]["nonfinite_rgb_pixels"] == 0 and
            checks[key]["negative_rgb_pixels"] == 0
            for key in ("reference", "reference_independent")) and
        checks["reference_A_B_RMS"] > 0 and
        not checks["reference_A_B_exact_identical"]
    )
    return checks


def main() -> int:
    head = pilot.require_clean_branch()
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise ValueError("P1m3c Sponza geometry fingerprint drift")
    if not pilot.BINARY.is_file():
        raise ValueError("P1m3c renderer missing")
    root = (pilot.ROOT / "out/research/n006-interval-aware-allocation" /
            "p1m3c-deforming-reference-q8" /
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    root.mkdir(parents=True, exist_ok=False)
    report_path = root / RESULT_NAME
    report: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "scenario": SCENARIO, "formal": False,
        "reference_eligibility_passed": False,
        "signed_quality_gain_established": False,
        "P1_predictor_go": False, "P2_scheduler_go": False,
        "gpu": cfg["target_gpu"], "scene_sha256": cfg["baseline"]["scene_sha256"],
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "reference_preflight": None, "references": None,
        "controls": [], "selection": None,
        "cases": [], "qualifying_quality_cells": [], "failures": [],
        "max_candidate_interventions": MAX_CASES,
        "quality_noise_rule": NOISE_RULE,
    }
    def save() -> None:
        report_path.write_text(
            json.dumps(report,sort_keys=True,indent=2) + "\n",
            encoding="utf-8")
    save()
    try:
        control0, base, evidence, folder = run_case(
            root, scene, cfg["target_gpu"], "Q8_control_reference",
            0, True, scenario=SCENARIO)
        report["controls"].append({k:v for k,v in control0.items()
                                   if k != "key_rows"})
        # Black/identical CPU references are NOT a zero-noise ideal.
        preflight = reference_preflight(folder, evidence)
        report["reference_preflight"] = preflight
        control_pfm = safe_image(folder, evidence["frames"][0]["image"])
        report["Q8_control_signal"] = rgb_diagnostic(read_pfm_payload(control_pfm))
        save()
        if not preflight["eligible"]:
            report["status"] = "reference-ineligible-retained"
            report["next_gate"] = (
                "STOP before extra-ray comparisons; reference method cannot "
                "label this dynamic state. New validated independent reference "
                "transport study needed, do not treat black as ideal.")
            save()
            print(json.dumps({
                "status": report["status"],
                "reference_preflight": preflight,
                "summary": str(report_path)}, indent=2))
            return 0
        references, R_A, R_B = reference_pair(folder, evidence)
        report["reference_eligibility_passed"] = True
        report["references"] = references
        save()
        control1, again, _e1, _f1 = run_case(
            root, scene, cfg["target_gpu"], "Q8_control_repeat",
            0, False, scenario=SCENARIO)
        report["controls"].append({k:v for k,v in control1.items()
                                   if k != "key_rows"})
        save()
        if (base != again or
            control0["image_sha256"] != control1["image_sha256"] or
            control0["coverage_sha256"] != control1["coverage_sha256"] or
            control0["key_rows"] != control1["key_rows"]):
            raise ValueError("P1m3c independent Q8 controls differ")
        selection = select_prospective_holdout(control0["key_rows"])
        report["selection"] = {
            **selection, "M0_rows_SHA256": control0["coverage_sha256"],
            "control_PFM_SHA256": control0["image_sha256"],
        }
        save()  # Critical: freeze M0 selected keys before any extra rays.
        baselineA, baselineB = rgb_rms(base,R_A),rgb_rms(base,R_B)
        report["references"]["baseline_RGB_RMS_A"] = baselineA
        report["references"]["baseline_RGB_RMS_B"] = baselineB
        noise = references["RMS_reference_A_vs_B"]
        for row in selection["selected"]:
            key = row["token"]
            label = f"q8_{row['stratum']}_{row['cascade']}_{key}"
            case, cand, _ec, _fc = run_case(
                root, scene, cfg["target_gpu"], label, key, False,
                scenario=SCENARIO)
            if (case["coverage_sha256"] != control0["coverage_sha256"] or
                case["selected_key_row"] != {
                    x: row[x] for x in (
                        "token", "consumer_pixels", "producer_owner_outputs")
                }):
                raise ValueError("P1m3c canonical key or scene coverage mismatch")
            delta = image_delta(base,cand)
            if (delta["changed_rgb_pixels"] == 0) != (
                case["image_sha256"] == control0["image_sha256"]):
                raise ValueError("P1m3c full PFM SHA differs from changed RGB")
            candA, candB = rgb_rms(cand,R_A), rgb_rms(cand,R_B)
            gainA, gainB = baselineA-candA, baselineB-candB
            case.pop("key_rows",None)
            case.update({
                "selection": row, "image_delta_vs_Q8_control": delta,
                "baseline_RMS_A": baselineA,"baseline_RMS_B": baselineB,
                "candidate_RMS_A": candA,"candidate_RMS_B": candB,
                "signed_gain_A":gainA,"signed_gain_B":gainB,
                "reference_RMS_noise_bound":noise,
                "signed_gain_ref_sensitivity":abs(gainA-gainB),
                "reproduced":False, "quality_signal":False,
            })
            report["cases"].append(case)
            save()
            if delta["changed_rgb_pixels"]:
                repeat, image, _r, _d = run_case(
                    root, scene, cfg["target_gpu"], label+"_repeat",key,False,
                    scenario=SCENARIO)
                if (image != cand or
                    repeat["image_sha256"] != case["image_sha256"] or
                    repeat["coverage_sha256"] != case["coverage_sha256"] or
                    repeat["selected_key_row"] != case["selected_key_row"] or
                    repeat["canonical_m1_trace"]["base_radiance_sum16"] !=
                    case["canonical_m1_trace"]["base_radiance_sum16"] or
                    repeat["canonical_m1_trace"]["extra_radiance_sum16"] !=
                    case["canonical_m1_trace"]["extra_radiance_sum16"]):
                    raise ValueError("P1m3c changed image failed independent replication")
                case["reproduced"] = True
                case["repeat_PFM_SHA256"] = repeat["image_sha256"]
            if row["stratum"] == "global_zero_negative" and delta["changed_rgb_pixels"]:
                raise ValueError("P1m3c zero-consumer negative affected image")
            case["quality_signal"] = (
                case["reproduced"] and gainA > noise and gainB > noise)
            if case["quality_signal"]:
                report["qualifying_quality_cells"].append({
                    "token":key,"cascade":row["cascade"],
                    "signed_gain_A":gainA,"signed_gain_B":gainB,
                    "reference_RMS_noise_bound":noise})
            save()
        positives = [x for x in report["cases"]
                     if x["selection"]["stratum"] == "max_positive"]
        if not any(x["image_delta_vs_Q8_control"]["changed_rgb_pixels"]
                   for x in positives):
            report["status"] = "image-null-stop"
        elif not report["qualifying_quality_cells"]:
            report["status"] = "quality-not-detectable-stop"
        else:
            report["status"] = "quality-signal-unvalidated"
        report["reference_noise_exceeding_signal_seen"] = bool(
            report["qualifying_quality_cells"])
        # A single same-geometry trajectory cannot establish global quality gain.
        report["signed_quality_gain_established"] = False
        report["next_gate"] = (
            "Independent other geometry and repeated sign/ROI validation; "
            "P1 predictor/P2 scheduler NO GO."
            if report["qualifying_quality_cells"] else
            "STOP Q8 4-ray consumer-key P1 predictor expansion on this "
            "trajectory; no post-hoc key/direction/reference changes."
        )
        save()
        print(json.dumps({
            "status":report["status"],
            "cases":len(report["cases"]),
            "quality_signals":len(report["qualifying_quality_cells"]),
            "summary":str(report_path),
        },indent=2))
        return 0
    except (OSError,ValueError,KeyError,RuntimeError,TypeError) as exc:
        report["status"] = "invalid-retained"
        report["failures"].append({"error":str(exc)})
        save()
        print(f"[P1m3c] invalid {exc}: {report_path}",file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError,ValueError,KeyError,RuntimeError,TypeError) as exc:
        print(f"[P1m3c] setup error {exc}",file=sys.stderr)
        raise SystemExit(1)
