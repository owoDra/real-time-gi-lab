#!/usr/bin/env python3
"""Non-formal N006 P1 causal feasibility pilot. Does not select or tune a scheduler."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
THIS_DIR = Path(__file__).resolve().parent
N004_DIR = ROOT / "scripts/research/lane_n_end_to_end_renderer"
sys.path.insert(0, str(N004_DIR))
import n001_contract  # noqa: E402

CONFIG_PATH = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/004-n004-weakness-atlas-v2-config.json"
EXPECTED_BRANCH = "research-n006-interval-aware-allocation"
EVIDENCE_NAME = "n006-candidate-evidence.json"
PILOT_VERSION = "n006-p1-causal-pilot-v1"
BINARY = ROOT / "build/release/phos-n006-intervention"


def git(*parts: str) -> str:
    proc = subprocess.run(
        ["git", *parts], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or "git error")
    return proc.stdout.strip()


def require_clean_branch() -> str:
    branch = git("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise RuntimeError(f"expected {EXPECTED_BRANCH}, got {branch!r}")
    if git("status", "--porcelain"):
        raise RuntimeError("worktree must be clean before causal pilot")
    return git("rev-parse", "HEAD")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def deterministic_tiles(tile_ids: list[int], count: int) -> list[int]:
    if count < 1 or len(tile_ids) < count:
        raise ValueError("invalid eligible tile population or tile-count")
    if len(tile_ids) != len(set(tile_ids)):
        raise ValueError("duplicate visible tile IDs")
    ids = sorted(tile_ids)
    # Predetermined spatial-order quantiles; neither signal nor error-derived.
    indices = [((2 * i + 1) * len(ids)) // (2 * count) for i in range(count)]
    return [ids[min(j, len(ids) - 1)] for j in indices]


def read_rms(image: Path, reference: Path) -> float:
    actual = n001_contract.read_pfm(image)
    target = n001_contract.read_pfm(reference)
    if (actual.width, actual.height) != (target.width, target.height):
        raise RuntimeError("current/intervention reference dimensions differ")
    if len(actual.pixels) != len(target.pixels):
        raise RuntimeError("RGB payload length differs")
    if not actual.pixels:
        raise RuntimeError("empty HDR image")
    if any(not math.isfinite(float(a)) or not math.isfinite(float(b))
           for a, b in zip(actual.pixels, target.pixels, strict=True)):
        raise RuntimeError("non-finite HDR payload")
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b
                         in zip(actual.pixels, target.pixels, strict=True))
                     / len(actual.pixels))


def check_evidence(data: dict[str, Any], mode: str, expected_extra: int, gpu: str) -> dict:
    if data.get("protocol_version") != "n006-p1-intervention-v1":
        raise RuntimeError("N006 intervention evidence protocol mismatch")
    if data.get("mode") != mode or data.get("scenario") != "deforming-control":
        raise RuntimeError("unexpected N006 mode/scenario")
    if data.get("device", {}).get("name") != gpu:
        raise RuntimeError("wrong GPU")
    if not data.get("source", {}).get("internal_correctness"):
        raise RuntimeError("source correctness invalid")
    frames = data.get("frames", [])
    if len(frames) != 1:
        raise RuntimeError("expected exactly one target frame")
    frame = frames[0]
    extra = frame.get("extra", {})
    if (not frame.get("internal_correctness") or
        not extra.get("base_prefix_correct") or
        not extra.get("extra_work_correct") or
        frame.get("hit_diagnostics", {}).get("substantive_mismatches") != 0 or
        frame.get("stats", {}).get("overflow") != 0 or
        frame.get("stats", {}).get("storage_failures") != 0):
        raise RuntimeError("intervention correctness failed")
    if extra.get("extra_rays_traced") != expected_extra or (
        expected_extra and extra.get("selected_owner_count") != 1
    ):
        raise RuntimeError("actual extra work not as planned")
    return frame


def run(
    binary: Path, scene: Path, out: Path, mode: str, gpu: str,
    tile: int | None = None, cascade: int | None = None,
    *, capture: bool = False, reference: bool = False,
) -> dict[str, Any]:
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"nonempty artifact path: {out}")
    out.mkdir(parents=True, exist_ok=True)
    command = [
        "bash", str(ROOT / "scripts/run_with_vulkan.sh"), str(binary),
        "--scene", str(scene), "--artifact-dir", str(out),
        "--scenario", "deforming-control", "--mode", mode,
        "--source-warmup-frames", "32", "--target-frames", "1",
        "--owner-budgets", "1" if tile is not None else "0",
    ]
    if tile is not None:
        if cascade is None:
            raise ValueError("cascade required for targeted intervention")
        command.extend(["--selected-tile-id", str(tile),
                        "--selected-cascade", str(cascade)])
    if not reference:
        command.append("--skip-reference")
    if capture:
        command.append("--capture-visible-tiles")
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    (out / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"renderer {mode} failed (exit {proc.returncode}): {out}/stderr.log")
    evidence_file = out / EVIDENCE_NAME
    if not evidence_file.is_file():
        raise RuntimeError(f"missing {evidence_file}")
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    frame = check_evidence(evidence, mode, 4 if tile is not None else 0, gpu)
    return {"evidence": evidence, "frame": frame}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tile-count", type=int, default=3)
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    commit = require_clean_branch()
    if not 1 <= args.tile_count <= 12:
        raise ValueError("pilot supports 1..12 spatial-quantile tiles")
    if not BINARY.is_file():
        raise RuntimeError("missing phos-n006-intervention; execute 'mise run build'")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    gpu = config["target_gpu"]
    scene = ROOT / config["baseline"]["scene"]
    if not scene.is_file() or sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("missing/wrong Sponza; execute 'mise run assets'")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (args.artifact_dir or
           ROOT / "out/research/n006-interval-aware-allocation/p1-causal-pilot" / stamp).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("pilot artifact directory must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    # First baseline makes an independent path-traced reference for this case.
    baseline = run(BINARY, scene, out / "current", "current", gpu,
                   capture=True, reference=True)
    ref_meta = baseline["frame"].get("reference")
    if not isinstance(ref_meta, dict) or not ref_meta.get("converged"):
        raise RuntimeError("canonical reference failed convergence")
    reference_path = out / "current" / ref_meta["path"]
    base_image = out / "current" / baseline["frame"]["image"]
    original_rms = read_rms(base_image, reference_path)
    # A second fresh-process current rendering bounds run-to-run noise.
    repeat = run(BINARY, scene, out / "current-repeat", "current", gpu)
    repeat_rms = read_rms(out / "current-repeat" / repeat["frame"]["image"],
                          reference_path)
    visible = json.loads((out / "current" / "n006-visible-tiles.json").read_text(encoding="utf-8"))
    tiles = deterministic_tiles(visible["tile_ids"], args.tile_count)
    summary: dict[str, Any] = {
        "protocol_version": PILOT_VERSION,
        "phase": "P1-causal-feasibility-pilot",
        "formal": False,
        "status": "in-progress",
        "git": {"branch": EXPECTED_BRANCH, "head": commit, "dirty": False},
        "gpu": gpu,
        "scenario": "stable-topology-deforming",
        "scene_digest": config["baseline"]["scene_sha256"],
        "reference": str(reference_path.relative_to(out)),
        "reference_spp": ref_meta["spp"],
        "calibration_only": True,
        "selection": "visible-tile-spatial-quantiles-independent-of-error",
        "tiles": tiles,
        "baseline_rgb_rms": original_rms,
        "baseline_repeat_rgb_rms": repeat_rms,
        "baseline_run_to_run_rms_delta": abs(original_rms - repeat_rms),
        "interventions": [],
        "failures": [],
    }
    summary_path = out / "n006-p1-pilot-summary.json"
    def checkpoint() -> None:
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    checkpoint()
    for tile in tiles:
        for cascade in range(4):
            label = f"tile-{tile:05d}-cascade-{cascade}"
            try:
                tested = run(BINARY, scene, out / label, "targeted-extra-rays",
                             gpu, tile, cascade)
                actual = read_rms(out / label / tested["frame"]["image"], reference_path)
                summary["interventions"].append({
                    "tile_id": tile, "cascade": cascade, "extra_rays": 4,
                    "rgb_rms": actual,
                    "rgb_rms_gain": original_rms - actual,
                    "gain_per_ray": (original_rms - actual) / 4,
                    "gpu_complete_gi_us_descriptive": tested["frame"]["timing_us"]["complete_gi_gpu"],
                    "artifact": label,
                })
            except (OSError, ValueError, RuntimeError) as error:
                summary["failures"].append({"label": label, "error": str(error)})
            checkpoint()
    summary["status"] = "complete" if not summary["failures"] else "incomplete-errors-retained"
    checkpoint()
    print(json.dumps({
        "status": summary["status"],
        "interventions": len(summary["interventions"]),
        "failures": len(summary["failures"]),
        "summary": str(summary_path),
    }, ensure_ascii=False, indent=2))
    return 0 if not summary["failures"] else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"N006 causal pilot failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
