#!/usr/bin/env python3
"""N006 P1b non-formal internal-causality probe, with no new reference tracing."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import audit_p1a_images as audit
import run_p1_pilot as pilot

TARGETS = ((22890, 0), (22890, 3))
WARMUP = 1
TRACE_SCHEMA = "n006-p1b-influence-probe-v1"
PRIOR_HEAD = "4871623797b8ba0b155447f63697bd3340829ee3"


def find_prior(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    root = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1-causal-pilot")
    paths = sorted(root.glob("*-cli-repair/n006-p1-pilot-summary.json"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one prior repaired P1a campaign, found {len(paths)}; supply --prior-summary")
    return paths[0].resolve()


def trace_check(trace: dict[str, Any], tile: int, cascade: int) -> dict[str, Any]:
    if not trace.get("available"):
        raise RuntimeError("selected output has no influence trace")
    if (trace.get("tile_id") != tile or trace.get("cascade") != cascade
        or trace.get("base_ray_count") != 8
        or trace.get("extra_ray_count") != 4
        or not isinstance(trace.get("shared_probe_outputs"), int)
        or trace["shared_probe_outputs"] < 1):
        raise RuntimeError("target trace identity or ray-count contract failed")
    before_sum = int(trace["before_storage_sum16"])
    after_sum = int(trace["after_storage_sum16"])
    count = int(trace["shared_probe_outputs"])
    if (trace.get("observed_storage_sum16") != after_sum
        or trace.get("observed_storage_outputs") != count
        or not math.isclose(float(trace["before_storage_mean16"]),
                            before_sum / count, abs_tol=1e-9)
        or not math.isclose(float(trace["after_storage_mean16"]),
                            after_sum / count, abs_tol=1e-9)):
        raise RuntimeError("target influence storage aggregation mismatch")
    return {
        "ray_integer_total_changed": (
            int(trace["extra_radiance_sum16"]) != 0),
        "output_mean_16bit_changed": (
            int(trace["base_output_mean16"]) != int(trace["target_output_mean16"])),
        "storage_probe_sum_16bit_changed": before_sum != after_sum,
        "shared_probe_outputs": count,
        "raw": trace,
    }


def run_frame(out: Path, scene: Path, gpu: str,
              tile: int | None = None,
              cascade: int | None = None) -> dict[str, Any]:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"artifact already exists: {out}")
    out.mkdir(parents=True, exist_ok=True)
    mode = "current" if tile is None else "targeted-extra-rays"
    cmd = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY),
        "--artifact-dir", str(out),
        "--scene", str(scene),
        "--scenario", "deforming-control",
        "--mode", mode,
        "--source-warmup-frames", str(WARMUP),
        "--target-frames", "1",
        "--owner-budgets", "0" if tile is None else "1",
        "--skip-reference",
    ]
    if tile is not None:
        if cascade is None:
            raise RuntimeError("cascade missing for targeted intervention")
        cmd += ["--selected-tile-id", str(tile),
                "--selected-cascade", str(cascade)]
    process = subprocess.run(
        cmd, text=True, capture_output=True, cwd=pilot.ROOT, check=False)
    (out / "stdout.log").write_text(process.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        raise RuntimeError(
            f"probe run {mode}/{tile}/{cascade} failed with {process.returncode}: {out / 'stderr.log'}")
    data = json.loads((out / pilot.EVIDENCE_NAME).read_text(encoding="utf-8"))
    frame = pilot.check_evidence(data, mode, 0 if tile is None else 4, gpu)
    return {
        "image": out / frame["image"],
        "trace": frame["extra"].get("influence_trace"),
        "frame": frame,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-summary", type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run 'mise run build'")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    gpu = config["target_gpu"]
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("missing or different Sponza asset")

    prior_path = find_prior(args.prior_summary)
    prior_summary = json.loads(prior_path.read_text(encoding="utf-8"))
    if (prior_summary.get("git", {}).get("head") != PRIOR_HEAD
        or prior_summary.get("reference_reuse", {}).get("prior_head")
            != "2c54edd39ba2dca93c2a90cc062414fec65aecb2"):
        raise RuntimeError("unexpected P1a original campaign lineage")
    previous = audit.audit(prior_path)  # Checks all 12 image/evidence files and reference.
    if previous["source_commit"] != PRIOR_HEAD or not previous["all_interventions_validated"]:
        raise RuntimeError("prior causal campaign audit failed")
    prior_root = prior_path.parent
    original_base = prior_root / "current" / "frames/candidate-000.pfm"
    original_reference = prior_root / previous_ref(prior_summary)
    fixed_prior = {(int(x["tile_id"]), int(x["cascade"])): x
                   for x in previous["interventions"]}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.artifact_dir or
           pilot.ROOT / "out/research/n006-interval-aware-allocation"
           / "p1b-influence" / stamp).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("P1b destination must be new/empty")
    out.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "protocol_version": TRACE_SCHEMA,
        "formal": False,
        "phase": "P1b-internal-causality-diagnostic",
        "status": "in-progress",
        "gpu": gpu,
        "git": {"branch": pilot.EXPECTED_BRANCH, "head": head, "dirty": False},
        "prior_summary": str(prior_path),
        "prior_head": PRIOR_HEAD,
        "reference_sha256": previous["reference_sha256"],
        "reference_regenerated": False,
        "warmup_frames": WARMUP,
        "target_matrix": [{"tile_id": t, "cascade": c} for t, c in TARGETS],
        "cases": [],
        "failures": [],
    }
    summary_file = out / "n006-p1b-influence-summary.json"

    def save() -> None:
        summary_file.write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        current = run_frame(out / "current-short-warmup", scene, gpu)
        if current["trace"] is None or current["trace"].get("available"):
            raise RuntimeError("current mode must not emit a targeted probe trace")
        image_drift = pilot.read_rms(current["image"], original_base)
        summary["short_warmup_baseline_image_rms"] = image_drift
        save()
        if image_drift != 0.0:
            raise RuntimeError(
                f"short warmup produced different current image ({image_drift}); "
                "forensic comparisons invalid, preserve artifacts")
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        summary["failures"].append({"case": "baseline-compatibility", "error": str(error)})
        summary["status"] = "blocked-baseline-drift"
        save()
        raise

    for tile, cascade in TARGETS:
        label = f"tile-{tile:05d}-cascade-{cascade}"
        try:
            sample = run_frame(out / label, scene, gpu, tile, cascade)
            trace = trace_check(sample["trace"], tile, cascade)
            change_from_p1a = pilot.read_rms(
                sample["image"], prior_root / label / "frames/candidate-000.pfm")
            gain_vs_original = (
                float(prior_summary["baseline_rgb_rms"])
                - pilot.read_rms(sample["image"], original_reference))
            original_gain = float(fixed_prior[(tile, cascade)]["global_rgb_rms_gain"])
            if change_from_p1a != 0.0 or not math.isclose(
                gain_vs_original, original_gain, rel_tol=1e-6, abs_tol=1e-12):
                raise RuntimeError(
                    "new instrumented image not bit-identical to preserved P1a target")
            summary["cases"].append({
                "tile_id": tile,
                "cascade": cascade,
                "new_image_vs_p1a_rgb_rms": change_from_p1a,
                "prior_final_changed_pixels": int(fixed_prior[(tile, cascade)]["changed_pixels"]),
                "prior_global_rgb_rms_gain": original_gain,
                "influence": trace,
            })
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            summary["failures"].append({"case": label, "error": str(error)})
        save()

    summary["status"] = "complete" if not summary["failures"] else "incomplete-errors-retained"
    save()
    print(json.dumps({
        "status": summary["status"],
        "instrumented_cases": len(summary["cases"]),
        "failures": len(summary["failures"]),
        "summary": str(summary_file),
    }, ensure_ascii=False, indent=2))
    return 0 if not summary["failures"] else 3


def previous_ref(prior_summary: dict[str, Any]) -> str:
    path = Path(prior_summary["reference"])
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError("unsafe saved reference path")
    return str(path)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"N006 P1b influence diagnostic failed: {error}", file=sys.stderr)
        raise SystemExit(1)
