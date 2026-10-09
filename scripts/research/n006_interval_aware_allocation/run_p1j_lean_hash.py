#!/usr/bin/env python3
"""N006 P1j-A: 10-case lean-hash canonical probe correctness/memory preflight."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
from run_p1i_cross_backend import MATRIX, validate as validate_p1i

PROTOCOL = "n006-p1j-lean-hash-v1"
LEAN_HASH_SLOTS = 32768
LEGACY_SCRATCH_BYTES = 8421464
LEAN_SCRATCH_BYTES = 4489304


def validate_lean_case(
    case: dict[str, Any], raw: dict[str, Any]
) -> dict[str, Any]:
    frames = raw.get("frames", [])
    if len(frames) != 2:
        raise ValueError("P1j-A missing original/canonical target frames")
    baseline = frames[0].get("extra", {}).get("canonical", {})
    canonical = frames[1].get("extra", {}).get("canonical", {})
    if baseline.get("executed") is not False:
        raise ValueError("P1j-A original current frame unexpectedly canonical")
    if (
        canonical.get("executed") is not True
        or canonical.get("hash_slots") != LEAN_HASH_SLOTS
        or canonical.get("scratch_bytes") != LEAN_SCRATCH_BYTES
        or case.get("additional_scratch_bytes") != LEAN_SCRATCH_BYTES
        or not isinstance(canonical.get("collision_steps"), int)
        or isinstance(canonical["collision_steps"], bool)
        or canonical["collision_steps"] < 0
    ):
        raise ValueError("P1j-A lean hash slot/scratch/collision accounting failed")
    return {
        **case,
        "hash_slots": canonical["hash_slots"],
        "hash_collision_steps": canonical["collision_steps"],
        "previous_scratch_bytes": LEGACY_SCRATCH_BYTES,
        "lean_scratch_bytes": LEAN_SCRATCH_BYTES,
        "scratch_saved_bytes": LEGACY_SCRATCH_BYTES - LEAN_SCRATCH_BYTES,
        "scratch_saved_fraction":
            (LEGACY_SCRATCH_BYTES - LEAN_SCRATCH_BYTES) / LEGACY_SCRATCH_BYTES,
        "note": ("The delta is measured N006 scratch allocation, "
                 "NOT measured whole-renderer resident memory saving. "
                 "Cold sequential target frames, NOT a speedup study."),
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("missing N006 executable; run mise run build")
    cfg = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / cfg["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != cfg["baseline"]["scene_sha256"]:
        raise RuntimeError("accepted Sponza scene changed/missing")
    gpu = cfg["target_gpu"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1j-lean-hash" / stamp)
    dest.mkdir(parents=True, exist_ok=False)
    summary_file = dest / "n006-p1j-lean-hash-summary.json"
    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL, "status": "in-progress",
        "formal": False, "reference_generated": False, "gpu": gpu,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "scene_sha256": cfg["baseline"]["scene_sha256"],
        "hash_slots": LEAN_HASH_SLOTS,
        "expected_scratch_bytes": LEAN_SCRATCH_BYTES,
        "case_matrix": [{"variant": v, "scenario": s} for v, s in MATRIX],
        "results": [], "failures": [],
    }

    def checkpoint() -> None:
        summary_file.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
    checkpoint()

    for index, (variant, scenario) in enumerate(MATRIX):
        output = dest / f"case-{index:02d}-{variant}-{scenario}"
        output.mkdir(parents=True, exist_ok=False)
        command = [
            "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
            str(pilot.BINARY), "--scene", str(scene),
            "--artifact-dir", str(output),
            "--scenario", scenario, "--variant", variant,
            "--mode", "current",
            "--source-warmup-frames", "32",
            "--target-frames", "2", "--motion-fractions", "1,1",
            "--owner-budgets", "0,0",
            "--skip-reference", "--canonical-probe-pilot",
            "--canonical-matrix-case", "--canonical-lean-hash",
        ]
        try:
            result = subprocess.run(
                command, cwd=pilot.ROOT,
                capture_output=True, text=True, check=False)
            (output / "stdout.log").write_text(result.stdout, encoding="utf-8")
            (output / "stderr.log").write_text(result.stderr, encoding="utf-8")
            if result.returncode:
                raise RuntimeError(
                    f"renderer exit {result.returncode}; inspect {output / 'stderr.log'}")
            evidence_file = output / pilot.EVIDENCE_NAME
            raw = json.loads(evidence_file.read_text(encoding="utf-8"))
            parity = validate_p1i(raw, output, gpu, variant, scenario)
            record = validate_lean_case(parity, raw)
            record["case_index"] = index
            record["raw_evidence_sha256"] = hashlib.sha256(
                evidence_file.read_bytes()).hexdigest()
            summary["results"].append(record)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            summary["failures"].append({
                "case_index": index,
                "variant": variant, "scenario": scenario,
                "error": str(error),
                "stderr": str(output / "stderr.log"),
            })
            summary["status"] = "invalid-retained"
            checkpoint()
            raise
        checkpoint()

    summary["status"] = "complete"
    summary["all_cases_byte_identical"] = True
    summary["cases_complete"] = len(summary["results"])
    checkpoint()
    print(json.dumps({
        "status": "complete",
        "cases": summary["cases_complete"],
        "lean_hash_slots": LEAN_HASH_SLOTS,
        "saved_scratch_bytes": LEGACY_SCRATCH_BYTES - LEAN_SCRATCH_BYTES,
        "summary": str(summary_file),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        print(f"N006 P1j-A lean hash preflight failed: {error}", file=sys.stderr)
        raise SystemExit(1)
