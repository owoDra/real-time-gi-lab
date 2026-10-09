#!/usr/bin/env python3
"""P1f: validate every duplicate owner's merged GPU radiance and storage result."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_p1_pilot as pilot
import run_p1d_hash_cost as p1d

PROTOCOL = "n006-p1f-owner-equivalence-v1"
EXPECTED_UNIQUE = p1d.EXPECTED_KEYS
EXPECTED_DUPLICATE = p1d.EXPECTED_DUPLICATES
EXPECTED_OWNERS = p1d.EXPECTED_OWNER_COUNT


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    if (payload.get("protocol_version") != PROTOCOL or
        payload.get("base_work_items") != EXPECTED_OWNERS * 32 or
        payload.get("owner_outputs") != EXPECTED_OWNERS * 4 or
        payload.get("visible_owners") != EXPECTED_OWNERS or
        payload.get("rays_per_probe") != 8 or
        payload.get("cascade_count") != 4 or
        payload.get("all_gpu_storage_slots_reconstructed") is not True):
        raise ValueError("P1f source/GPU storage contract failed")
    rows = payload.get("cascades")
    if not isinstance(rows, list) or len(rows) != 4:
        raise ValueError("P1f expected four cascade rows")
    seen = set()
    divergent_keys = 0
    divergent_outputs = 0
    for row in rows:
        cascade = row.get("cascade")
        if not isinstance(cascade, int) or cascade in seen or cascade not in range(4):
            raise ValueError("P1f missing or duplicate cascade")
        seen.add(cascade)
        unique = row.get("unique_probe_keys")
        count = row.get("owner_outputs")
        shared = row.get("shared_keys")
        if (unique != EXPECTED_UNIQUE[cascade] or
            count != EXPECTED_OWNERS or
            count - unique != EXPECTED_DUPLICATE[cascade] or
            not isinstance(shared, int) or not 0 <= shared <= unique or
            any(not isinstance(row.get(field), int) or row[field] < 0
                for field in (
                    "divergent_merged_keys", "divergent_owner_outputs",
                    "divergent_rounded_mean_keys", "zero_sample_outputs",
                    "missing_or_bad_gpu_storage_keys"
                ))):
            raise ValueError(f"P1f cardinality/diagnostic field contract failed at C{cascade}")
        if row["missing_or_bad_gpu_storage_keys"] or row["zero_sample_outputs"]:
            raise ValueError(f"P1f GPU storage or sample issue at C{cascade}")
        divergent_keys += row["divergent_merged_keys"]
        divergent_outputs += row["divergent_owner_outputs"]
    return {
        "unique_probe_keys": sum(EXPECTED_UNIQUE),
        "base_ray_inputs": payload["base_work_items"],
        "distinct_ray_inputs_if_canonical": sum(EXPECTED_UNIQUE) * 8,
        "duplicated_input_fraction":
            (payload["base_work_items"] - sum(EXPECTED_UNIQUE) * 8)
            / payload["base_work_items"],
        "divergent_merged_keys": divergent_keys,
        "divergent_owner_outputs": divergent_outputs,
        "fully_equivalent": (
            divergent_keys == 0 and divergent_outputs == 0 and
            all(x["divergent_rounded_mean_keys"] == 0 for x in rows)
        ),
        "per_cascade": sorted(rows, key=lambda x: x["cascade"]),
    }


def main() -> int:
    head = pilot.require_clean_branch()
    if not pilot.BINARY.is_file():
        raise RuntimeError("N006 binary missing; run 'mise run build'")
    config = json.loads(pilot.CONFIG_PATH.read_text(encoding="utf-8"))
    gpu = config["target_gpu"]
    scene = pilot.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or pilot.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza scene changed/missing")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (pilot.ROOT / "out/research/n006-interval-aware-allocation"
           / "p1f-owner-equivalence" / stamp)
    out.mkdir(parents=True, exist_ok=False)
    summary_file = out / "n006-p1f-owner-equivalence-summary.json"
    def save(summary: dict[str, Any]) -> None:
        summary_file.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary: dict[str, Any] = {
        "protocol_version": PROTOCOL,
        "phase": "P1f-nonformal-output-equivalence",
        "status": "in-progress", "formal": False, "gpu": gpu,
        "git": {"head": head, "branch": pilot.EXPECTED_BRANCH, "dirty": False},
        "scenario": "stable-topology-deforming",
        "scene_sha256": config["baseline"]["scene_sha256"],
        "reference_generated": False,
    }
    save(summary)
    cmd = [
        "bash", str(pilot.ROOT / "scripts/run_with_vulkan.sh"),
        str(pilot.BINARY),
        "--scene", str(scene), "--artifact-dir", str(out),
        "--scenario", "deforming-control", "--mode", "current",
        "--source-warmup-frames", "1", "--target-frames", "1",
        "--owner-budgets", "0", "--skip-reference",
        "--capture-probe-equivalence",
    ]
    proc = subprocess.run(cmd, cwd=pilot.ROOT, capture_output=True, text=True,
                          check=False)
    (out / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        summary["status"] = "incomplete-error-retained"
        summary["error"] = f"renderer exit={proc.returncode}; inspect {out / 'stderr.log'}"
        save(summary)
        raise RuntimeError(summary["error"])
    evidence = json.loads((out / pilot.EVIDENCE_NAME).read_text(encoding="utf-8"))
    frame = pilot.check_evidence(evidence, "current", 0, gpu)
    if frame["stats"]["visible_owners"] != EXPECTED_OWNERS or frame["stats"]["outputs"] != EXPECTED_OWNERS * 4:
        raise RuntimeError("renderer GPU output counts differ from P1c")
    payload = json.loads((out / "n006-probe-equivalence.json").read_text(encoding="utf-8"))
    result = validate(payload)
    summary.update({
        "status": "complete",
        "results": result,
        "frame_work_items": frame["stats"]["work_items"],
        "image": frame["image"],
        "source_evidence": pilot.EVIDENCE_NAME,
        "raw_equivalence": "n006-probe-equivalence.json",
    })
    save(summary)
    print(json.dumps({
        "status": summary["status"],
        "equivalent": result["fully_equivalent"],
        "divergent_keys": result["divergent_merged_keys"],
        "gpu_storage_reconstruction": "pass",
        "summary": str(summary_file),
    }, ensure_ascii=False, indent=2))
    return 0 if result["fully_equivalent"] else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print(f"N006 P1f owner equivalence diagnostic failed: {error}", file=sys.stderr)
        raise SystemExit(1)
