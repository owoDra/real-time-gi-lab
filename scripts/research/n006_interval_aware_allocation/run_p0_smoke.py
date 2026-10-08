#!/usr/bin/env python3
"""N006 P0 GPU smoke test of the unmodified N005 renderer (NOT research evidence)."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRANCH = "research-n006-interval-aware-allocation"
PREDECESSOR = "3a098584ec76bcaa06e5166793b2946cd1f7eb25"
N004_CONFIG = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/004-n004-weakness-atlas-v2-config.json"
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
EVIDENCE_FILENAME = "n005-candidate-evidence.json"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "git command failed")
    return proc.stdout.strip()


def require_clean_lineage() -> str:
    branch = git("branch", "--show-current")
    if branch != BRANCH:
        raise RuntimeError(f"expected branch {BRANCH}, got {branch!r}")
    if git("status", "--porcelain"):
        raise RuntimeError("clean Git worktree required (artifacts must be ignored)")
    head = git("rev-parse", "HEAD")
    if not git("merge-base", "--is-ancestor", PREDECESSOR, head) == "":
        raise RuntimeError("expected N005 ancestor missing")
    return head


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def validate_evidence(data: dict, expected_gpu: str) -> dict:
    if data.get("protocol_version") != "n005-p2-candidate-evidence-v1":
        raise RuntimeError("unexpected existing N005 evidence schema")
    if data.get("mode") != "current" or data.get("scenario") != "static":
        raise RuntimeError("unexpected smoke-test mode/scenario")
    device = data.get("device", {})
    if device.get("name") != expected_gpu:
        raise RuntimeError(f"wrong GPU: {device.get('name')!r}; expected {expected_gpu!r}")
    source = data.get("source", {})
    frames = data.get("frames", [])
    if not source.get("internal_correctness") or len(frames) != 1:
        raise RuntimeError("source correctness or frame count failed")
    f = frames[0]
    if not f.get("internal_correctness"):
        raise RuntimeError("frame correctness failed")
    if f.get("owner_budget") != 0:
        raise RuntimeError("nonzero smoke-test owner budget")
    if f.get("extra", {}).get("extra_rays_traced") != 0:
        raise RuntimeError("current mode unexpectedly traced extra rays")
    if f.get("stats", {}).get("overflow") or f.get("stats", {}).get("storage_failures"):
        raise RuntimeError("overflow/storage failure")
    if f.get("hit_diagnostics", {}).get("substantive_mismatches") != 0:
        raise RuntimeError("substantive traversal mismatch")
    return {
        "status": "pass",
        "device": device,
        "complete_gi_gpu_us": f.get("timing_us", {}).get("complete_gi_gpu"),
        "visible_owners": f.get("stats", {}).get("visible_owners"),
        "base_work_items": f.get("stats", {}).get("work_items"),
        "source_correct": True,
        "frame_correct": True,
        "extra_rays": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="N006 P0 non-formal GPU smoke on the unchanged N005 current-mode renderer"
    )
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    head = require_clean_lineage()
    config = json.loads(N004_CONFIG.read_text(encoding="utf-8"))
    target = config["target_gpu"]
    scene = ROOT / config["baseline"]["scene"]
    if not scene.is_file():
        raise RuntimeError("Sponza missing: execute 'mise run assets' before the smoke")
    if sha256_file(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("Sponza SHA-256 mismatch; do not use incompatible scene")

    binary = ROOT / "build/release/phos-n005-candidate"
    if not binary.is_file():
        raise RuntimeError("missing phos-n005-candidate: execute 'mise run build'")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.artifact_dir or
           ROOT / "out/research/n006-interval-aware-allocation/p0-smoke" / stamp).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"artifact directory must be empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        "bash", str(VULKAN_WRAPPER), str(binary),
        "--scene", str(scene),
        "--artifact-dir", str(out),
        "--scenario", "static",
        "--mode", "current",
        "--source-warmup-frames", "1",
        "--target-frames", "1",
        "--owner-budgets", "0",
        "--skip-reference",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    (out / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"renderer failed (exit {proc.returncode}); see {out}/stderr.log")

    evidence_path = out / EVIDENCE_FILENAME
    if not evidence_path.is_file():
        raise RuntimeError(f"missing renderer evidence {evidence_path}")
    summary = validate_evidence(
        json.loads(evidence_path.read_text(encoding="utf-8")), target
    )
    summary.update({
        "schema_version": 1,
        "purpose": "non-formal-device-and-correctness-smoke",
        "git": {"branch": BRANCH, "head": head, "dirty": False},
        "predecessor": PREDECESSOR,
        "reference_generation": "skipped",
        "formal_quality_or_timing_claim": False,
        "sample_exclusion": "none",
    })
    summary_path = out / "n006-p0-smoke-summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "pass",
        "device": summary["device"]["name"],
        "complete_gi_gpu_us_descriptive_only": summary["complete_gi_gpu_us"],
        "summary": str(summary_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"N006 P0 smoke failed: {error}", file=sys.stderr)
        raise SystemExit(1)
