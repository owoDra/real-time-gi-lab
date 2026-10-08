#!/usr/bin/env python3
"""Audit existing N006 P1d per-stage timing from six raw evidence files. No GPU."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1d_hash_cost as p1d
import run_p1_pilot as pilot

ROOT = Path(__file__).resolve().parents[3]
PIPELINE = (
    "producer_gpu", "ray_prepare_gpu", "traversal_gpu", "radiance_gpu",
    "merge_gpu", "storage_update_gpu", "resolve_gpu",
)
DYNAMIC_PARTS = (
    "geometry_transfer_gpu", "instance_transfer_gpu",
    "blas_update_gpu", "tlas_update_gpu",
)
CPU_DIAGNOSTICS = ("dynamic_update_wall",)
STAGES = PIPELINE + DYNAMIC_PARTS + CPU_DIAGNOSTICS
AUDIT_PROTOCOL = "n006-p1d-offline-stage-audit-v1"
SOURCE_HEAD = "2b862de49b8627e7d8bdbd4d91c312400c161019"


def select_summary(explicit: Path | None) -> Path:
    if explicit:
        result = explicit.resolve()
    else:
        root = ROOT / "out/research/n006-interval-aware-allocation/p1d-hash-cost"
        paths = sorted(root.glob("*/n006-p1d-hash-cost-summary.json"))
        if len(paths) != 1:
            raise ValueError(f"found {len(paths)} P1d runs; use --summary PATH")
        result = paths[0].resolve()
    if not result.is_file():
        raise ValueError(f"missing source summary: {result}")
    return result


def under(directory: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"untrusted relative filename: {relative!r}")
    absolute = directory / path
    if not absolute.is_file():
        raise ValueError(f"missing retained raw evidence: {absolute}")
    return absolute


def finite_us(data: dict[str, Any], name: str) -> float:
    value = data.get(name)
    if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"invalid GPU/CPU timing {name}: {value!r}")
    return float(value)


def load_raw(campaign: Path, index: int, mode: str, expected: dict[str, Any], gpu: str) -> dict[str, Any]:
    root = campaign / f"pair-{index}-{mode}"
    file = under(root, "n006-candidate-evidence.json")
    raw = json.loads(file.read_text(encoding="utf-8"))
    if (raw.get("device", {}).get("name") != gpu
        or raw.get("mode") != "current"
        or raw.get("scenario") != "deforming-control"
        or raw.get("source_warmup_frames") != 1
        or raw.get("reference_generation") != "skipped"):
        raise ValueError(f"invalid original raw run contract: pair-{index}-{mode}")
    frame = pilot.check_evidence(raw, "current", 0, gpu)
    if frame.get("stats", {}).get("visible_owners") != p1d.EXPECTED_OWNER_COUNT:
        raise ValueError("unexpected owner count")
    timing = frame.get("timing_us")
    if not isinstance(timing, dict):
        raise ValueError("missing raw timing")
    for key in (*STAGES, "complete_gi_gpu", "complete_renderer_gpu"):
        finite_us(timing, key)
    if not math.isclose(timing["complete_gi_gpu"], expected["complete_gi_gpu_us"],
                        rel_tol=0, abs_tol=1e-8):
        raise ValueError("raw complete-GI time differs from frozen summary")
    if not math.isclose(timing["complete_renderer_gpu"], expected["complete_renderer_gpu_us"],
                        rel_tol=0, abs_tol=1e-8):
        raise ValueError("raw complete-renderer time differs from frozen summary")
    image = under(root, frame["image"])
    image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
    if image_hash != expected["image_sha256"]:
        raise ValueError("original raw image SHA-256 mismatch")
    probe = frame.get("extra", {}).get("gpu_hash_probe", {})
    if mode == "hash":
        p1d.validate_hash(probe)
        expected_probe = expected["gpu_hash"]
        for field in ("unique_keys", "duplicate_outputs", "hash_slots",
                      "scratch_bytes", "collision_steps", "failed_inserts",
                      "invalid_keys", "unique_by_cascade", "duplicate_by_cascade"):
            if probe[field] != expected_probe[field]:
                raise ValueError(f"hash evidence mismatch: {field}")
        if not math.isclose(probe["complete_hash_gpu_us"],
                            expected_probe["complete_hash_gpu_us"],
                            rel_tol=0, abs_tol=1e-8):
            raise ValueError("hash GPU stage time changed")
    elif probe.get("executed"):
        raise ValueError("control executed hash stage")
    return {
        "timing": {key: finite_us(timing, key)
                   for key in (*STAGES, "complete_gi_gpu", "complete_renderer_gpu")},
        "hash_gpu_us": float(probe["complete_hash_gpu_us"]) if mode == "hash" else 0.0,
        "sha256_evidence": hashlib.sha256(file.read_bytes()).hexdigest(),
        "image_sha256": image_hash,
    }


def compare(current: dict[str, Any], hashed: dict[str, Any]) -> dict[str, Any]:
    c = current["timing"]
    h = hashed["timing"]
    stage_delta = {stage: h[stage] - c[stage] for stage in STAGES}
    full_delta = h["complete_gi_gpu"] - c["complete_gi_gpu"]
    hash_gpu = hashed["hash_gpu_us"]
    pipeline_delta = sum(stage_delta[stage] for stage in PIPELINE)
    return {
        "complete_gi_delta_us": full_delta,
        "complete_renderer_delta_us":
            h["complete_renderer_gpu"] - c["complete_renderer_gpu"],
        "hash_stage_including_clear_us": hash_gpu,
        "pipeline_stage_delta_us": stage_delta,
        "subtotal_selected_nonoverlapping_pipeline_delta_us": pipeline_delta,
        "unattributed_complete_gi_delta_us":
            full_delta - hash_gpu - pipeline_delta,
        "note": ("Unattributed is an arithmetic residual that also includes "
                 "unexported frame/init/visibility/invalidations, dynamic "
                 "maintenance and differences in measured intervals; "
                 "it is NOT a measured standalone GPU stage. CPU wall "
                 "must not be summed into GPU timestamps."),
    }


def audit(summary_path: Path) -> dict[str, Any]:
    campaign = summary_path.resolve().parent
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("protocol_version") != p1d.PROTOCOL
        or summary.get("status") != "complete"
        or summary.get("failures") != []
        or summary.get("formal") is not False
        or summary.get("reference_generated") is not False
        or summary.get("git", {}).get("head") != SOURCE_HEAD
        or summary.get("gpu") != "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"
        or len(summary.get("pairs", [])) != 3):
        raise ValueError("wrong or incomplete P1d campaign")
    gpu = summary["gpu"]
    pairs = []
    for index, record in enumerate(summary["pairs"]):
        if (record.get("index") != index or
            tuple(record.get("order", ())) != p1d.ORDER[index]):
            raise ValueError("P1d pair order not frozen order")
        current = load_raw(campaign, index, "current", record["current"], gpu)
        hashed = load_raw(campaign, index, "hash", record["hash"], gpu)
        if current["image_sha256"] != hashed["image_sha256"]:
            raise ValueError("hash changed P1d image")
        delta = compare(current, hashed)
        if not math.isclose(
            delta["complete_gi_delta_us"],
            record["paired_complete_gi_delta_us"], abs_tol=1e-8, rel_tol=0
        ):
            raise ValueError("P1d pair complete delta changed")
        pairs.append({
            "index": index,
            "order": record["order"],
            "current_raw": current,
            "hash_raw": hashed,
            **delta,
        })
    if not math.isclose(
        statistics.median(x["complete_gi_delta_us"] for x in pairs),
        summary["median_complete_gi_delta_us"], abs_tol=1e-8, rel_tol=0
    ):
        raise ValueError("P1d median complete-GI delta differs")
    return {
        "protocol_version": AUDIT_PROTOCOL,
        "status": "complete",
        "formal": False,
        "source_summary": str(summary_path),
        "source_head": SOURCE_HEAD,
        "gpu": gpu,
        "pairs": pairs,
        "median_hash_stage_us":
            statistics.median(x["hash_stage_including_clear_us"] for x in pairs),
        "median_complete_gi_delta_us":
            statistics.median(x["complete_gi_delta_us"] for x in pairs),
        "median_unattributed_complete_gi_delta_us":
            statistics.median(x["unattributed_complete_gi_delta_us"] for x in pairs),
        "disclaimer": ("Offline stage accounting is diagnostic. It neither "
                       "proves root cause nor measures a faster deduplicated renderer."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = select_summary(args.summary)
    result = audit(source)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = (args.output or ROOT / "out/research/n006-interval-aware-allocation"
            / "p1d-stage-audit" / stamp
            / "n006-p1d-stage-audit.json").resolve()
    if dest.exists():
        raise ValueError("refusing to overwrite an existing audit file")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({
        "status": "complete",
        "pairs": len(result["pairs"]),
        "median_hash_stage_us": result["median_hash_stage_us"],
        "median_complete_gi_delta_us": result["median_complete_gi_delta_us"],
        "median_unattributed_complete_gi_delta_us":
            result["median_unattributed_complete_gi_delta_us"],
        "output": str(dest),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f"N006 P1d offline stage audit failed: {error}", file=sys.stderr)
        raise SystemExit(1)
