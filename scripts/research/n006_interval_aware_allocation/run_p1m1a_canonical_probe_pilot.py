#!/usr/bin/env python3
"""N006 P1m1a: single canonical +4 ray correctness, NOT signed HDR quality.

Four separately warmed GPU processes: frozen base, frozen static/C3
zero/low/high M0 calibration keys. Never P2 scheduling or a heldout test.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any

import run_p1_pilot as pilot
from run_p1m0_consumer_coverage import FROZEN_M0, audit_coverage
from run_p1l_a1b_sampled_hit import (
    SCENE_EXPECTATIONS, SOURCE_WARMUPS, TARGET_WARMUPS,
    expected_sha, HASH_SLOTS,
)

PROTOCOL = "n006-p1m1a-canonical-key-extra-preflight-v1"
SCENE = "static"
VARIANT = "lane-e-final-software"
TIMEOUT = 600
# Frozen from original independently accepted M0 raw summary on clean 8a5cb25.
# Do not reseat keys after observing causal effects.
CALIBRATION_C3 = {
    "zero": (3221225474, 0, 3),
    "low_positive": (3223322625, 93, 3),
    "high_positive": (3223324678, 875, 125),
}
CASES = ("control", "zero", "low_positive", "high_positive")


def verify_envelope(data: dict[str, Any], label: str, gpu: str,
                    require_ray_fate: bool = False) -> dict[str, Any]:
    owners, cascades = SCENE_EXPECTATIONS[SCENE]
    expected_outputs = sum(cascades)
    expected_base_work = expected_outputs * 8
    intervention = label != "control"
    selected_token = CALIBRATION_C3[label][0] if intervention else 0
    if (data.get("protocol_version") != "n006-p1-intervention-v1" or
        data.get("mode") != "current" or
        data.get("scenario") != SCENE or data.get("variant") != VARIANT or
        data.get("source_warmup_frames") != SOURCE_WARMUPS or
        data.get("source_warmups_correct") is not True or
        data.get("target_state_warmup", {}).get("frames") != TARGET_WARMUPS or
        data.get("target_state_warmup", {}).get("correct") is not True or
        data.get("target_state_warmup", {}).get("last_visible_owners") != owners or
        data.get("source", {}).get("internal_correctness") is not True or
        data.get("device", {}).get("name") != gpu or
        data.get("reference_generation") != "skipped" or
        data.get("p1m0_consumer_coverage") is not True or
        data.get("p1m0_pretrace_coverage") is not False or
        data.get("p1m1_canonical_token") != selected_token):
        raise ValueError(f"P1m1a {label}: renderer/scene/source/gate drift")
    frames = data.get("frames")
    if not isinstance(frames, list) or len(frames) != 1:
        raise ValueError(f"P1m1a {label}: expected exactly one frame")
    frame = frames[0]
    stats = frame.get("stats", {})
    extra = frame.get("extra", {})
    can = extra.get("canonical", {})
    trace = extra.get("canonical_m1", {})
    hits = frame.get("hit_diagnostics", {})
    if (frame.get("index") != 0 or frame.get("motion_fraction") != 1.0 or
        frame.get("owner_budget") != 0 or
        frame.get("internal_correctness") is not True or
        not isinstance(hits, dict) or
        hits.get("substantive_mismatches") != 0 or
        stats.get("visible_owners") != owners or
        stats.get("outputs") != expected_outputs or
        stats.get("work_items") != expected_base_work + (4 if intervention else 0) or
        stats.get("storage_updates") != expected_outputs or
        stats.get("storage_failures") != 0 or stats.get("overflow") != 0 or
        extra.get("base_prefix_correct") is not True or
        extra.get("extra_work_correct") is not True or
        extra.get("base_traced_rays") != expected_base_work or
        extra.get("extra_rays_traced") != (4 if intervention else 0) or
        can.get("executed") is not True or
        can.get("copyback_executed") is not True or
        can.get("canonical_outputs") != expected_outputs or
        can.get("canonical_work_items") != expected_base_work or
        can.get("hash_slots") != HASH_SLOTS or
        can.get("weighted_owner_total") != owners * 4 or
        can.get("owner_weight_errors") != 0 or
        can.get("invalid_keys") != 0 or
        can.get("failed_inserts") != 0 or
        can.get("index_overflows") != 0 or
        can.get("unique_by_cascade") != list(cascades)):
        raise ValueError(f"P1m1a {label}: ray/base/owner/storage/parity error")
    cov = audit_coverage(frame.get("p1m0_consumer_coverage"), SCENE)
    fingerprint, matched, used_keys = FROZEN_M0[SCENE]
    if (cov["key_rows_sha256"] != fingerprint or
        cov["matched_lookups"] != matched or
        cov["keys_with_consumers"] != used_keys):
        raise ValueError(f"P1m1a {label}: original M0 key/coverage fingerprint mismatch")
    if intervention:
        token, pixels, multiplicity = CALIBRATION_C3[label]
        selected_rows = [
            r for r in frame["p1m0_consumer_coverage"]["key_rows"]
            if r["token"] == token]
        if len(selected_rows) != 1 or selected_rows[0] != {
            "token": token, "consumer_pixels": pixels,
            "producer_owner_outputs": multiplicity,
        }:
            raise ValueError(f"P1m1a {label}: frozen stratum key changed")
        if (trace.get("executed") is not True or
            trace.get("selected_token") != token or
            type(trace.get("output_id")) is not int or
            trace["output_id"] >= expected_outputs or
            trace.get("base_ray_count") != 8 or
            trace.get("extra_ray_count") != 4 or
            trace.get("merged_sample_count") != 12 or
            type(trace.get("base_radiance_sum16")) is not int or
            type(trace.get("extra_radiance_sum16")) is not int or
            trace.get("baseline_mean16") !=
                (trace["base_radiance_sum16"] + 4) // 8 or
            trace.get("candidate_mean16") !=
                (trace["base_radiance_sum16"] +
                 trace["extra_radiance_sum16"] + 6) // 12 or
            not isinstance(trace.get("extra_injection_gpu_us"), (int, float)) or
            trace["extra_injection_gpu_us"] <= 0):
            raise ValueError(f"P1m1a {label}: 8+4 causal trace invalid")
        if require_ray_fate:
            fields = (
                "base_hit_count", "extra_hit_count", "extra_miss_count",
                "base_positive_radiance_rays", "extra_positive_radiance_rays",
                "extra_hit_zero_radiance_rays",
            )
            if any(type(trace.get(k)) is not int or trace[k] < 0
                   for k in fields):
                raise ValueError("P1m1c missing/noninteger ray-fate fields")
            if (trace["base_hit_count"] > 8 or
                trace["extra_hit_count"] + trace["extra_miss_count"] != 4 or
                trace["extra_positive_radiance_rays"] +
                    trace["extra_hit_zero_radiance_rays"] != trace["extra_hit_count"] or
                trace["base_positive_radiance_rays"] > trace["base_hit_count"] or
                trace["extra_positive_radiance_rays"] >
                    trace["extra_radiance_sum16"] or
                trace["base_positive_radiance_rays"] >
                    trace["base_radiance_sum16"]):
                raise ValueError("P1m1c GPU hit/radiance sample closure failed")
            # Pre-registered fidelity to M1a exactly: all 3 frozen interventions
            # had zero new radiance. A mismatch here means a changed trajectory,
            # workload or nondeterminism, not grounds to reselect tokens.
            if trace["extra_radiance_sum16"] != 0:
                raise ValueError("P1m1c original frozen M1a zero energy not reproduced")
    elif trace != {"executed": False}:
        raise ValueError("P1m1a control unexpectedly injected extra rays")
    return {
        "label": label, "selected_token": selected_token,
        "accepted_base_secondary_rays": expected_base_work,
        "actual_traced_secondary_rays": stats["work_items"],
        "accepted_canonical_keys": expected_outputs,
        "coverage_sha256": cov["key_rows_sha256"],
        "cpu_hit_oracle_mismatches": hits["substantive_mismatches"],
        "canonical_m1_trace": trace,
    }


def read_pfm_payload(path: Path) -> bytes:
    with path.open("rb") as f:
        if f.readline() != b"PF\n" or f.readline().strip() != b"320 180" or (
            f.readline().strip() != b"-1.0"
        ):
            raise ValueError("P1m1a unexpected PFM header/endianness/size")
        raw = f.read()
    if len(raw) != 320 * 180 * 3 * 4:
        raise ValueError("P1m1a PFM RGB float32 payload size mismatch")
    return raw


def image_delta(base: bytes, changed: bytes) -> dict[str, Any]:
    if len(base) != len(changed):
        raise ValueError("P1m1a PFM base/treatment sizes differ")
    if base == changed:
        return {"changed_rgb_pixels": 0, "changed_channel_values": 0,
                "max_abs_rgb_delta": 0.0, "not": "signed HDR quality"}
    pixels = 0
    channels = 0
    max_delta = 0.0
    for offset in range(0, len(base), 12):
        if base[offset:offset+12] == changed[offset:offset+12]:
            continue
        pixels += 1
        for channel in range(3):
            a = offset + 4 * channel
            if base[a:a+4] != changed[a:a+4]:
                channels += 1
                x = struct.unpack_from("<f", base, a)[0]
                y = struct.unpack_from("<f", changed, a)[0]
                if not (math.isfinite(x) and math.isfinite(y)):
                    raise ValueError("P1m1a nonfinite treatment PFM delta")
                max_delta = max(max_delta, abs(x-y))
    return {"changed_rgb_pixels": pixels, "changed_channel_values": channels,
            "max_abs_rgb_delta": max_delta, "not": "signed HDR quality"}


def main(*, protocol_version: str = PROTOCOL,
         output_tag: str = "p1m1a-canonical-key-pilot",
         summary_file_name: str = "n006-p1m1a-canonical-key-pilot-summary.json",
         require_ray_fate: bool = False) -> int:
    head = pilot.require_clean_branch()
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise ValueError("P1m1a Sponza missing or fingerprint drift")
    if not pilot.BINARY.is_file():
        raise ValueError("P1m1a intervention binary missing; mise run build")
    root = (pilot.ROOT / "out/research/n006-interval-aware-allocation" /
            output_tag /
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    root.mkdir(parents=True, exist_ok=False)
    summary_file = root / summary_file_name
    result: dict[str, Any] = {
        "protocol_version": protocol_version, "status": "in-progress",
        "formal": False, "reference_generated": False,
        "predictive_quality_established": False,
        "scene": SCENE, "case_matrix": list(CASES),
        "calibration_only": True, "candidate_rays_per_selected_key": 4,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "source_scene_sha256": cfg["baseline"]["scene_sha256"],
        "target_gpu": cfg["target_gpu"], "cases": [], "failures": [],
    }
    def save() -> None:
        summary_file.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
    save()
    base_payload: bytes | None = None
    for label in CASES:
        folder = root / label
        folder.mkdir()
        cmd = [
            "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
            str(pilot.BINARY), "--scene", str(scene),
            "--artifact-dir", str(folder), "--scenario", SCENE,
            "--variant", VARIANT, "--mode", "current",
            "--source-warmup-frames", "32",
            "--target-state-warmup-frames", "8", "--target-frames", "1",
            "--skip-reference", "--canonical-lean-hash",
            "--p1m0-consumer-coverage",
        ]
        if label != "control":
            cmd += ["--p1m1-canonical-token", str(CALIBRATION_C3[label][0])]
        print(f"[P1m1a] {label}: control or exact +4 rays; "
              f"log={folder.resolve() / 'stderr.log'}", flush=True)
        try:
            stdout = folder / "stdout.log"
            stderr = folder / "stderr.log"
            try:
                with stdout.open("wb") as o, stderr.open("wb") as e:
                    run = subprocess.run(
                        cmd, cwd=pilot.ROOT, stdout=o, stderr=e,
                        timeout=TIMEOUT, check=False)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(
                    f"{label} timeout {TIMEOUT}s, stderr tail:\n"
                    + stderr.read_text(encoding="utf-8", errors="replace")[-5000:]
                ) from exc
            if run.returncode:
                raise RuntimeError(
                    f"{label} renderer exit {run.returncode}; stderr tail:\n"
                    + stderr.read_text(encoding="utf-8", errors="replace")[-5000:])
            raw = (folder / pilot.EVIDENCE_NAME).read_bytes()
            data = json.loads(raw)
            checked = verify_envelope(
                data, label, cfg["target_gpu"],
                require_ray_fate=require_ray_fate)
            frame = data["frames"][0]
            image_rel = Path(frame["image"])
            if image_rel.is_absolute() or ".." in image_rel.parts:
                raise ValueError("P1m1a path traversal in candidate PFM")
            image = folder / image_rel
            image_sha = hashlib.sha256(image.read_bytes()).hexdigest()
            if label == "control":
                if image_sha != expected_sha(VARIANT, SCENE):
                    raise ValueError("P1m1a base canonical HDR does not match accepted SHA")
                base_payload = read_pfm_payload(image)
                checked["image_delta_vs_control"] = None
            else:
                if base_payload is None:
                    raise ValueError("P1m1a control payload unavailable")
                checked["image_delta_vs_control"] = image_delta(
                    base_payload, read_pfm_payload(image))
            if require_ray_fate and label != "control":
                diff = checked["image_delta_vs_control"]
                if (diff["changed_rgb_pixels"] != 0 or
                    diff["changed_channel_values"] != 0 or
                    image_sha != expected_sha(VARIANT, SCENE)):
                    raise ValueError(
                        "P1m1c original frozen 3/3 null image SHA not reproduced")
            checked["pfm_sha256"] = image_sha
            checked["raw_renderer_evidence_sha256"] = hashlib.sha256(raw).hexdigest()
            result["cases"].append(checked)
            save()
        except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
            result["status"] = "invalid-retained"
            result["failures"].append({
                "case": label, "error": str(exc),
                "stderr": str((folder / "stderr.log").resolve())})
            save()
            print(f"[P1m1a] failure summary: {summary_file}", file=sys.stderr)
            raise
    result["status"] = (
        "ray-fate-audit-complete" if require_ray_fate
        else "mechanism-preflight-complete")
    result["next_gate"] = (
        "diagnose added-ray misses vs hits with zero radiance before freezing "
        "a distinct nonzero-signal sampling protocol; no P2 GO"
        if require_ray_fate else
        "independent converged HDR reference and paired signed marginal "
        "gain with calibrated repeat noise on independent trajectories")
    save()
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "summary": str(summary_file)}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        print(f"P1m1a failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
