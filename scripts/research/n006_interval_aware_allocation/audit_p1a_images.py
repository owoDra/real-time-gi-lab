#!/usr/bin/env python3
"""Analyze completed N006 P1a image effects without running the GPU or overwriting evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
N004_SCRIPTS = ROOT / "scripts/research/lane_n_end_to_end_renderer"
sys.path.insert(0, str(N004_SCRIPTS))
import n001_contract  # noqa: E402

from run_p1_pilot import check_evidence, read_rms  # noqa: E402

GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
PILOT_VERSION = "n006-p1-causal-pilot-v1"
EVIDENCE_NAME = "n006-candidate-evidence.json"


def safe_file(root: Path, relative: str) -> Path:
    p = Path(relative)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe path in frozen evidence: {relative!r}")
    resolved = root / p
    if not resolved.is_file():
        raise ValueError(f"artifact not available: {resolved}")
    return resolved


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def effect_stats(
    baseline: Sequence[float],
    candidate: Sequence[float],
    reference: Sequence[float],
    *,
    width: int,
    height: int,
    tile_id: int,
) -> dict[str, int | float | bool | None]:
    n = width * height * 3
    if not 0 <= tile_id < width * height:
        raise ValueError("invalid tile index")
    if not (n > 0 and len(baseline) == len(candidate) == len(reference) == n):
        raise ValueError("image dimensions / channels differ")
    changed_channels = 0
    changed_pixels = 0
    beneficial_pixels = 0
    harmful_pixels = 0
    image_delta_sq = 0.0
    image_delta_abs = 0.0
    max_abs = 0.0
    baseline_sq = 0.0
    candidate_sq = 0.0
    tile_changed = False
    for pixel in range(width * height):
        any_changed = False
        b_sq = 0.0
        c_sq = 0.0
        for channel in range(3):
            index = pixel * 3 + channel
            b = float(baseline[index])
            c = float(candidate[index])
            ref = float(reference[index])
            if not (math.isfinite(b) and math.isfinite(c) and math.isfinite(ref)):
                raise ValueError("non-finite RGB sample")
            delta = c - b
            if delta != 0.0:
                any_changed = True
                changed_channels += 1
                image_delta_sq += delta * delta
                image_delta_abs += abs(delta)
                max_abs = max(max_abs, abs(delta))
            eb = (b - ref) ** 2
            ec = (c - ref) ** 2
            b_sq += eb
            c_sq += ec
        baseline_sq += b_sq
        candidate_sq += c_sq
        if any_changed:
            changed_pixels += 1
            if pixel == tile_id:
                tile_changed = True
            if c_sq < b_sq:
                beneficial_pixels += 1
            elif c_sq > b_sq:
                harmful_pixels += 1
    return {
        "changed_channels": changed_channels,
        "changed_pixels": changed_pixels,
        "changed_pixel_fraction": changed_pixels / (width * height),
        "source_tile_pixel_changed": tile_changed,
        "beneficial_pixels": beneficial_pixels,
        "harmful_pixels": harmful_pixels,
        "max_abs_channel_delta": max_abs,
        "image_delta_rgb_rms": math.sqrt(image_delta_sq / n),
        "image_delta_rgb_l1_mean": image_delta_abs / n,
        "baseline_rgb_rms": math.sqrt(baseline_sq / n),
        "candidate_rgb_rms": math.sqrt(candidate_sq / n),
        "global_rgb_rms_gain": math.sqrt(baseline_sq / n) - math.sqrt(candidate_sq / n),
    }


def audit(summary_path: Path) -> dict[str, Any]:
    summary_path = summary_path.resolve()
    campaign = summary_path.parent
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("protocol_version") != PILOT_VERSION
        or summary.get("status") != "complete"
        or summary.get("formal") is not False
        or summary.get("calibration_only") is not True
        or summary.get("phase") != "P1a-causal-feasibility-pilot-cli-repair"
        or summary.get("gpu") != GPU
        or summary.get("failures") != []
        or len(summary.get("interventions", [])) != 12):
        raise ValueError("input is not the completed N006 P1a CLI-repair campaign")
    prior = summary.get("reference_reuse", {})
    reference = safe_file(campaign, summary["reference"])
    if sha256_file(reference) != prior.get("reference_sha256"):
        raise ValueError("reused independent reference hash mismatch")

    current_root = campaign / "current"
    cur = json.loads((current_root / EVIDENCE_NAME).read_text(encoding="utf-8"))
    cur_frame = check_evidence(cur, "current", 0, GPU)
    base_path = safe_file(current_root, cur_frame["image"])
    base = n001_contract.read_pfm(base_path)
    ref = n001_contract.read_pfm(reference)
    if base.width != ref.width or base.height != ref.height:
        raise ValueError("base and reference shapes differ")
    repeat_path = campaign / "current-repeat" / EVIDENCE_NAME
    repeat = json.loads(repeat_path.read_text(encoding="utf-8"))
    repeat_frame = check_evidence(repeat, "current", 0, GPU)
    repeat_image = safe_file(campaign / "current-repeat", repeat_frame["image"])
    if not math.isclose(read_rms(repeat_image, base_path),
                        float(summary["baseline_image_repeat_rgb_rms"]),
                        rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("baseline repeat image mismatch")
    if not math.isclose(read_rms(base_path, reference),
                        float(summary["baseline_rgb_rms"]),
                        rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("baseline RGB RMS mismatch")
    if not math.isclose(float(prior["new_code_baseline_image_rms"]), 0.0, abs_tol=1e-8):
        raise ValueError("baseline reference-reuse drift unexpectedly high")

    rows = []
    seen = set()
    for item in summary["interventions"]:
        tile, cascade = item["tile_id"], item["cascade"]
        key = (tile, cascade)
        if key in seen or tile not in summary["tiles"] or cascade not in range(4):
            raise ValueError("duplicate or unexpected intervention")
        seen.add(key)
        label = f"tile-{tile:05d}-cascade-{cascade}"
        if item["artifact"] != label or item["extra_rays"] != 4:
            raise ValueError("frozen intervention label/ray count changed")
        target_dir = campaign / label
        evidence = json.loads((target_dir / EVIDENCE_NAME).read_text(encoding="utf-8"))
        frame = check_evidence(evidence, "targeted-extra-rays", 4, GPU)
        if (evidence.get("selected_tile_id") != tile
            or evidence.get("selected_cascade") != cascade):
            raise ValueError("actual targeted tile/cascade differs")
        candidate_image_path = safe_file(target_dir, frame["image"])
        candidate = n001_contract.read_pfm(candidate_image_path)
        if candidate.width != base.width or candidate.height != base.height:
            raise ValueError("candidate shape differs from reference")
        computed = effect_stats(
            base.pixels, candidate.pixels, ref.pixels,
            width=base.width, height=base.height, tile_id=tile)
        if not math.isclose(computed["global_rgb_rms_gain"],
                            item["rgb_rms_gain"], abs_tol=1e-12, rel_tol=1e-7):
            raise ValueError(f"global RMS gain discrepancy for {label}")
        rows.append({
            "tile_id": tile,
            "cascade": cascade,
            "actual_extra_rays": frame["extra"]["extra_rays_traced"],
            "global_rgb_rms_gain": computed["global_rgb_rms_gain"],
            "descriptive_gpu_us": frame["timing_us"]["complete_gi_gpu"],
            **{k: v for k, v in computed.items()
               if k not in ("baseline_rgb_rms", "candidate_rgb_rms", "global_rgb_rms_gain")},
            "candidate_sha256": sha256_file(candidate_image_path),
        })
    if seen != {(tile, c) for tile in summary["tiles"] for c in range(4)}:
        raise ValueError("incomplete frozen intervention matrix")
    return {
        "protocol_version": "n006-p1a-paired-image-audit-v1",
        "phase": "offline-diagnostic-only",
        "formal": False,
        "source_pilot": str(summary_path),
        "source_commit": summary["git"]["head"],
        "reference_sha256": sha256_file(reference),
        "baseline_sha256": sha256_file(base_path),
        "baseline_rgb_rms": float(summary["baseline_rgb_rms"]),
        "all_interventions_validated": len(rows) == 12,
        "interventions": rows,
        "zero_changed_pixel_interventions": sum(row["changed_pixels"] == 0 for row in rows),
        "nonzero_changed_pixel_interventions": sum(row["changed_pixels"] > 0 for row in rows),
        "note": "This is paired image sensitivity; it cannot establish predictive ranking or scheduling gain.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True,
                        help="Completed *-cli-repair/n006-p1-pilot-summary.json")
    parser.add_argument("--output", type=Path,
                        help="Optional new JSON path (must not already exist)")
    args = parser.parse_args()
    data = audit(args.summary)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.output or ROOT / "out/research/n006-interval-aware-allocation"
           / "p1a-image-audit" / stamp / "n006-p1a-image-audit.json").resolve()
    if out.exists():
        raise ValueError(f"refusing to overwrite existing audit: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "zero_changed_pixel_interventions": data["zero_changed_pixel_interventions"],
        "nonzero_changed_pixel_interventions": data["nonzero_changed_pixel_interventions"],
        "output": str(out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f"N006 P1a image audit failed: {error}", file=sys.stderr)
        raise SystemExit(1)
