#!/usr/bin/env python3
"""P1j-B: opt-in direct compact ray-work bindings, strict 10-case parity audit."""
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
from run_p1j_lean_hash import (
    LEAN_HASH_SLOTS, LEAN_SCRATCH_BYTES, validate_lean_case,
)

PROTOCOL = "n006-p1j-b-direct-compact-v1"


def validate_direct_case(
    case: dict[str, Any], raw: dict[str, Any]
) -> dict[str, Any]:
    lean = validate_lean_case(case, raw)
    frames = raw["frames"]
    baseline = frames[0]["extra"]["canonical"]
    candidate = frames[1]["extra"]["canonical"]
    if baseline.get("executed") is not False:
        raise ValueError("P1j-B current baseline unexpectedly canonical")
    if candidate.get("copyback_executed") is not False:
        raise ValueError("P1j-B compact work was copied back, not consumed directly")
    if candidate["hash_slots"] != LEAN_HASH_SLOTS or (
        candidate["scratch_bytes"] != LEAN_SCRATCH_BYTES
    ):
        raise ValueError("P1j-B compact GPU allocation unexpected")
    return {
        **lean,
        "copyback_executed": False,
        "direct_compact_work": True,
        "note": ("Direct bind/copy-elimination correctness, not a matched "
                 "performance speedup or reduced compact-buffer allocation."),
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("N006 executable missing; run mise run build")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza asset absent or digest mismatch")
    gpu = config["target_gpu"]
    dest = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
            / "p1j-b-direct-compact" /
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    dest.mkdir(parents=True, exist_ok=False)
    file = dest / "n006-p1j-b-direct-compact-summary.json"
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL,
        "status": "in-progress",
        "formal": False,
        "gpu": gpu,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "scene_sha256": config["baseline"]["scene_sha256"],
        "hash_slots": LEAN_HASH_SLOTS,
        "expected_extra_scratch_bytes": LEAN_SCRATCH_BYTES,
        "matrix": [{"variant": v, "scenario": s} for v,s in MATRIX],
        "results": [], "failures": [], "reference_generated": False,
    }

    def checkpoint() -> None:
        file.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
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
            "--mode", "current", "--source-warmup-frames", "32",
            "--target-frames", "2", "--motion-fractions", "1,1",
            "--owner-budgets", "0,0", "--skip-reference",
            "--canonical-probe-pilot", "--canonical-matrix-case",
            "--canonical-lean-hash", "--canonical-zero-copy",
        ]
        try:
            process = subprocess.run(command, cwd=pilot.ROOT,
                text=True, capture_output=True, check=False)
            (output / "stdout.log").write_text(process.stdout, encoding="utf-8")
            (output / "stderr.log").write_text(process.stderr, encoding="utf-8")
            if process.returncode:
                raise RuntimeError(
                    f"renderer exit {process.returncode}; inspect {output / 'stderr.log'}")
            evidence_path = output / pilot.EVIDENCE_NAME
            raw = json.loads(evidence_path.read_text(encoding="utf-8"))
            parity = validate_p1i(raw, output, gpu, variant, scenario)
            case = validate_direct_case(parity, raw)
            case["case_index"] = index
            case["raw_evidence_sha256"] = hashlib.sha256(
                evidence_path.read_bytes()).hexdigest()
            result["results"].append(case)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as err:
            result["failures"].append({
                "case_index": index, "variant": variant,
                "scenario": scenario, "error": str(err),
                "stderr": str(output / "stderr.log"),
            })
            result["status"] = "invalid-retained"
            checkpoint()
            raise
        checkpoint()
    result["status"] = "complete"
    result["all_cases_byte_identical"] = True
    result["cases_complete"] = len(result["results"])
    checkpoint()
    print(json.dumps({
        "status": "complete",
        "cases": result["cases_complete"],
        "copyback_executed": False,
        "summary": str(file),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as err:
        print(f"N006 P1j-B direct compact pilot failed: {err}", file=sys.stderr)
        raise SystemExit(1)
