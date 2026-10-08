#!/usr/bin/env python3
"""Repair-only P1a continuation: reuse verified pre-fix reference, preserve old failure evidence.

This never overwrites a historical campaign and is not formal predictive evidence.
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot

ORIGINAL_HEAD = "2c54edd39ba2dca93c2a90cc062414fec65aecb2"
EXPECTED_ERROR = "renderer targeted-extra-rays failed (exit 2)"


def relative_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError("invalid file reference from prior campaign")
    full = root / path
    if not full.is_file():
        raise RuntimeError(f"missing prior artifact: {full}")
    return full


def load_old_campaign(old: Path, gpu: str, scene_hash: str) -> dict[str, Any]:
    if not old.is_dir():
        raise RuntimeError(f"prior campaign missing: {old}")
    summary = json.loads((old / "n006-p1-pilot-summary.json").read_text(encoding="utf-8"))
    if (summary.get("protocol_version") != pilot.PILOT_VERSION or
        summary.get("status") != "incomplete-errors-retained" or
        summary.get("formal") is not False or
        summary.get("calibration_only") is not True or
        summary.get("git", {}).get("head") != ORIGINAL_HEAD or
        summary.get("gpu") != gpu or
        summary.get("scene_digest") != scene_hash or
        summary.get("scenario") != "stable-topology-deforming" or
        summary.get("interventions") != []):
        raise RuntimeError("prior pilot provenance/status mismatch; refusing reference reuse")

    baseline = json.loads((old / "current" / pilot.EVIDENCE_NAME).read_text(encoding="utf-8"))
    repeat = json.loads((old / "current-repeat" / pilot.EVIDENCE_NAME).read_text(encoding="utf-8"))
    base_frame = pilot.check_evidence(baseline, "current", 0, gpu)
    repeat_frame = pilot.check_evidence(repeat, "current", 0, gpu)
    ref_meta = base_frame.get("reference")
    if (not isinstance(ref_meta, dict) or
        not ref_meta.get("converged") or
        not isinstance(ref_meta.get("spp"), int) or
        ref_meta["spp"] < 512):
        raise RuntimeError("prior independent reference is not converged")

    reference = relative_file(old / "current", ref_meta["path"])
    base_image = relative_file(old / "current", base_frame["image"])
    repeat_image = relative_file(old / "current-repeat", repeat_frame["image"])
    rms = pilot.read_rms(base_image, reference)
    rms_repeat = pilot.read_rms(repeat_image, reference)
    rms_pair = pilot.read_rms(base_image, repeat_image)
    for name, actual in [
        ("baseline_rgb_rms", rms),
        ("baseline_repeat_rgb_rms", rms_repeat),
        ("baseline_image_repeat_rgb_rms", rms_pair),
    ]:
        if not math.isclose(actual, float(summary[name]), rel_tol=1e-10, abs_tol=1e-12):
            raise RuntimeError(f"previous {name} evidence has changed")

    visible = json.loads(
        (old / "current" / "n006-visible-tiles.json").read_text(encoding="utf-8"))
    if visible.get("width") != 320 or visible.get("height") != 180:
        raise RuntimeError("visible-tile capture dimensions changed")
    tiles = pilot.deterministic_tiles(visible["tile_ids"], 3)
    if summary.get("tiles") != tiles:
        raise RuntimeError("frozen selection changed")
    expected_labels = {
        f"tile-{tile:05d}-cascade-{cascade}"
        for tile in tiles for cascade in range(4)
    }
    old_failures = summary.get("failures", [])
    if (len(old_failures) != 12 or
        {item.get("label") for item in old_failures} != expected_labels or
        not all(EXPECTED_ERROR in item.get("error", "") for item in old_failures)):
        raise RuntimeError("prior failure set differs from accepted CLI-parser failure")
    return {
        "baseline_frame": base_frame,
        "reference_meta": ref_meta,
        "tiles": tiles,
        "original_rms": rms,
        "repeat_rms": rms_repeat,
        "repeat_pair_rms": rms_pair,
        "reference_sha256": pilot.sha256(reference),
    }


def require_fixed_cli() -> None:
    # In the broken binary, this produced "usage" and exit 2. Do not repeat
    # expensive reference work until the rebuilt executable parses both flags.
    import subprocess
    proc = subprocess.run(
        [str(pilot.BINARY), "--selected-tile-id", "22890",
         "--selected-cascade", "2"],
        text=True, capture_output=True, check=False,
    )
    if proc.returncode != 1 or "invalid N006 candidate arguments" not in proc.stderr:
        raise RuntimeError("binary not rebuilt with targeted CLI parser fix")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failed-campaign", required=True, type=Path)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary; run 'mise run build'")
    require_fixed_cli()
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    gpu = config["target_gpu"]
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("missing or changed Sponza scene")

    old = args.failed_campaign.resolve()
    previous = load_old_campaign(old, gpu, config["baseline"]["scene_sha256"])
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.artifact_dir or
           pilot.ROOT / "out/research/n006-interval-aware-allocation/p1-causal-pilot" /
           (stamp + "-cli-repair")).resolve()
    if out == old or (out.exists() and any(out.iterdir())):
        raise RuntimeError("destination must be a new, empty directory")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(old / "current", out / "current")
    shutil.copytree(old / "current-repeat", out / "current-repeat")

    reference = out / "current" / previous["reference_meta"]["path"]
    baseline_image = out / "current" / previous["baseline_frame"]["image"]
    # New-code baseline must match the pre-fix baseline before trusting reused
    # reference. This is a fresh GPU run, but deliberately skips reference.
    verify = pilot.run(pilot.BINARY, scene, out / "current-verify", "current", gpu)
    verify_image = out / "current-verify" / verify["frame"]["image"]
    baseline_drift = pilot.read_rms(verify_image, baseline_image)
    if baseline_drift > 1e-8:
        raise RuntimeError(
            f"baseline image drift {baseline_drift}; old reference reuse forbidden")

    summary: dict[str, Any] = {
        "protocol_version": pilot.PILOT_VERSION,
        "phase": "P1a-causal-feasibility-pilot-cli-repair",
        "formal": False,
        "status": "in-progress",
        "git": {"branch": pilot.EXPECTED_BRANCH, "head": head, "dirty": False},
        "gpu": gpu,
        "scenario": "stable-topology-deforming",
        "scene_digest": config["baseline"]["scene_sha256"],
        "reference": str(reference.relative_to(out)),
        "reference_spp": previous["reference_meta"]["spp"],
        "calibration_only": True,
        "selection": "visible-tile-spatial-quantiles-independent-of-error",
        "tiles": previous["tiles"],
        "baseline_rgb_rms": previous["original_rms"],
        "baseline_repeat_rgb_rms": previous["repeat_rms"],
        "baseline_image_repeat_rgb_rms": previous["repeat_pair_rms"],
        "baseline_run_to_run_rms_delta": abs(
            previous["original_rms"] - previous["repeat_rms"]),
        "reference_reuse": {
            "prior_campaign": str(old),
            "prior_head": ORIGINAL_HEAD,
            "reason": "12 CLI parsing exits at original pilot; baseline/reference passed",
            "reference_sha256": previous["reference_sha256"],
            "new_code_baseline_image_rms": baseline_drift,
            "new_code_compatibility_tolerance": 1e-8,
            "source_artifacts_preserved": True,
        },
        "interventions": [],
        "failures": [],
    }
    summary_path = out / "n006-p1-pilot-summary.json"

    def checkpoint() -> None:
        summary_path.write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    checkpoint()
    for tile in previous["tiles"]:
        for cascade in range(4):
            label = f"tile-{tile:05d}-cascade-{cascade}"
            try:
                tested = pilot.run(
                    pilot.BINARY, scene, out / label, "targeted-extra-rays",
                    gpu, tile, cascade)
                actual = pilot.read_rms(
                    out / label / tested["frame"]["image"], reference)
                summary["interventions"].append({
                    "tile_id": tile,
                    "cascade": cascade,
                    "extra_rays": 4,
                    "rgb_rms": actual,
                    "rgb_rms_gain": previous["original_rms"] - actual,
                    "gain_per_ray": (previous["original_rms"] - actual) / 4,
                    "gpu_complete_gi_us_descriptive":
                        tested["frame"]["timing_us"]["complete_gi_gpu"],
                    "artifact": label,
                })
            except (OSError, ValueError, RuntimeError) as error:
                summary["failures"].append({"label": label, "error": str(error)})
            checkpoint()

    summary["status"] = ("complete" if not summary["failures"]
                         else "incomplete-errors-retained")
    checkpoint()
    print(json.dumps({
        "status": summary["status"],
        "interventions": len(summary["interventions"]),
        "failures": len(summary["failures"]),
        "summary": str(summary_path),
        "reused_reference": True,
    }, indent=2))
    return 0 if not summary["failures"] else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"N006 P1a repair failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
