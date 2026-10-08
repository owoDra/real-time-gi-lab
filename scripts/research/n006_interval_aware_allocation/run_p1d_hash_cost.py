#!/usr/bin/env python3
"""N006 P1d: paired current-frame GPU unique-probe hash overhead preflight."""
from __future__ import annotations

import hashlib
import json
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot

PROTOCOL = "n006-p1d-unique-hash-preflight-v1"
EXPECTED_KEYS = (1853, 815, 284, 77)
EXPECTED_DUPLICATES = (2319, 3357, 3888, 4095)
EXPECTED_OWNER_COUNT = 4172
ORDER = (("current", "hash"), ("hash", "current"), ("current", "hash"))


def validate_hash(probe: dict[str, Any]) -> None:
    if not probe.get("executed"):
        raise ValueError("hash pass was not executed")
    if tuple(probe.get("unique_by_cascade", [])) != EXPECTED_KEYS:
        raise ValueError("GPU hash unique key counts differ from P1c")
    if tuple(probe.get("duplicate_by_cascade", [])) != EXPECTED_DUPLICATES:
        raise ValueError("GPU hash duplicate counts differ from P1c")
    if (probe.get("unique_keys") != sum(EXPECTED_KEYS) or
        probe.get("duplicate_outputs") != sum(EXPECTED_DUPLICATES) or
        probe.get("invalid_keys") != 0 or
        probe.get("failed_inserts") != 0):
        raise ValueError("GPU hash total count/correctness mismatch")
    slots = int(probe["hash_slots"])
    if slots <= 2 * sum(EXPECTED_KEYS) or slots & (slots - 1):
        raise ValueError("GPU hash slot capacity invalid")
    if int(probe["scratch_bytes"]) < slots * 4 + 16 * 4:
        raise ValueError("GPU scratch memory reporting invalid")
    if not 0 < float(probe["complete_hash_gpu_us"]) < 1_000_000:
        raise ValueError("invalid GPU timestamp for complete hash stage")


def capture(mode: str, out: Path, scene: Path, gpu: str) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=False)
    command = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY), "--scene", str(scene), "--artifact-dir", str(out),
        "--scenario", "deforming-control", "--mode", "current",
        "--source-warmup-frames", "1", "--target-frames", "1",
        "--owner-budgets", "0", "--skip-reference",
    ]
    if mode == "hash":
        command.append("--capture-gpu-unique-hash")
    proc = subprocess.run(command, capture_output=True, text=True,
                          cwd=pilot.ROOT, check=False)
    (out / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"{mode}: renderer exit {proc.returncode}; {out / 'stderr.log'}")
    evidence = json.loads((out / "n006-candidate-evidence.json").read_text(encoding="utf-8"))
    if evidence.get("device", {}).get("name") != gpu:
        raise RuntimeError(f"{mode}: incorrect GPU")
    frame = pilot.check_evidence(evidence, "current", 0, gpu)
    if frame["stats"]["visible_owners"] != EXPECTED_OWNER_COUNT:
        raise RuntimeError(f"{mode}: owner count drifted from P1c")
    if frame["stats"]["work_items"] != EXPECTED_OWNER_COUNT * 32:
        raise RuntimeError(f"{mode}: work count drifted from P1c")
    hash_probe = frame["extra"].get("gpu_hash_probe", {})
    if mode == "hash":
        validate_hash(hash_probe)
    elif hash_probe.get("executed"):
        raise RuntimeError("current control unexpectedly ran GPU hash stage")
    image = out / frame["image"]
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    return {
        "mode": mode,
        "image_sha256": digest,
        "image": str(image.relative_to(out)),
        "complete_gi_gpu_us": float(frame["timing_us"]["complete_gi_gpu"]),
        "complete_renderer_gpu_us": float(frame["timing_us"]["complete_renderer_gpu"]),
        "gpu_hash": hash_probe if mode == "hash" else None,
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 binary: run 'mise run build'")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("wrong or missing Sponza input")
    gpu = config["target_gpu"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = pilot.ROOT / "out/research/n006-interval-aware-allocation/p1d-hash-cost" / stamp
    out.mkdir(parents=True, exist_ok=False)
    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "gpu": gpu,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "scenario": "stable-topology-deforming",
        "scene_sha256": config["baseline"]["scene_sha256"],
        "source_warmup_frames": 1, "target_frames": 1,
        "reference_generated": False,
        "exact_reference_counts": {"unique": list(EXPECTED_KEYS),
                                   "duplicates": list(EXPECTED_DUPLICATES)},
        "run_order": ORDER,
        "pairs": [], "failures": [],
    }
    path = out / "n006-p1d-hash-cost-summary.json"

    def checkpoint():
        path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    checkpoint()
    for index, ordered in enumerate(ORDER):
        results = {}
        try:
            for mode in ordered:
                results[mode] = capture(mode, out / f"pair-{index}-{mode}", scene, gpu)
            if results["hash"]["image_sha256"] != results["current"]["image_sha256"]:
                raise RuntimeError("hash stage changed current final PFM bytes")
            summary["pairs"].append({
                "index": index,
                "order": list(ordered),
                "current": results["current"],
                "hash": results["hash"],
                "paired_complete_gi_delta_us": (
                    results["hash"]["complete_gi_gpu_us"] -
                    results["current"]["complete_gi_gpu_us"]),
                "hash_extra_gpu_us": results["hash"]["gpu_hash"]["complete_hash_gpu_us"],
                "identical_image_sha256": results["current"]["image_sha256"],
            })
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
            summary["failures"].append({
                "pair": index, "error": str(error),
                "unfinished_pair_order": list(ordered),
            })
            checkpoint()
            break
        checkpoint()

    if len(summary["pairs"]) == 3 and not summary["failures"]:
        summary["status"] = "complete"
        summary["median_hash_gpu_us"] = statistics.median(
            x["hash_extra_gpu_us"] for x in summary["pairs"])
        summary["median_complete_gi_delta_us"] = statistics.median(
            x["paired_complete_gi_delta_us"] for x in summary["pairs"])
        summary["hash_scratch_bytes"] = summary["pairs"][0]["hash"]["gpu_hash"]["scratch_bytes"]
    else:
        summary["status"] = "incomplete-errors-retained"
    checkpoint()
    print(json.dumps({
        "status": summary["status"], "finished_pairs": len(summary["pairs"]),
        "failures": len(summary["failures"]), "summary": str(path),
    }, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "complete" else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f"N006 P1d GPU hash preflight failed: {error}", file=sys.stderr)
        raise SystemExit(1)
