#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import n001_contract as contract

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/001-n001-config.json"
DEFAULT_BINARY = ROOT / "build/phos-n001"
VALIDATION_ERROR_RE = re.compile(r"Validation Error|\bVUID-[A-Za-z0-9_-]+|\bUNASSIGNED-[A-Za-z0-9_-]+")


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value).resolve()
    return (ROOT / "out/research/lane-n-end-to-end-renderer/001-renderer-reference-bringup/manual").resolve()


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise contract.ContractError(
            f"git {' '.join(args)} failed: {proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def require_clean_lane_n() -> dict[str, object]:
    branch = git("branch", "--show-current")
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    if branch != "research-lane-n-end-to-end-renderer":
        raise contract.ContractError(
            f"N001 target evidence requires research-lane-n-end-to-end-renderer, got {branch!r}"
        )
    if len(commit) != 40:
        raise contract.ContractError("N001 target evidence requires a full Git commit SHA")
    if dirty:
        raise contract.ContractError("N001 target evidence requires a clean worktree")
    return {"branch": branch, "commit": commit, "dirty": False}


def validate_scene(config: dict) -> Path:
    scene = (ROOT / config["scene"]["path"]).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N001 scene is missing: {scene}")
    actual = contract.sha256_file(scene)
    expected = config["scene"]["sha256"]
    if actual != expected:
        raise contract.ContractError(
            f"N001 scene digest mismatch: expected {expected}, got {actual}"
        )
    return scene


def validation_error_count(stderr: str) -> int:
    return sum(1 for line in stderr.splitlines() if VALIDATION_ERROR_RE.search(line))


def lifetime_error_count(memory: dict[str, object]) -> int:
    try:
        values = {
            key: int(value)
            for key, value in memory.items()
            if isinstance(value, int) and not isinstance(value, bool)
        }
    except (TypeError, ValueError):
        return 1
    if set(values) != set(memory):
        return 1
    if any(value < 0 for value in values.values()):
        return 1
    peak = values.get("true_lifetime_peak", -1)
    if peak < 0:
        return 1
    device_components = [
        value
        for key, value in values.items()
        if key != "true_lifetime_peak"
    ]
    return 0 if device_components and peak >= max(device_components) else 1


def finalize_runtime_artifact(
    root: Path,
    config: dict,
    git_identity: dict[str, object],
    validation_errors: int,
) -> dict:
    runtime_path = root / "n001-runtime.json"
    if not runtime_path.is_file():
        raise contract.ContractError("N001 runtime did not produce n001-runtime.json")
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if runtime.get("schema_version") != 1:
        raise contract.ContractError("N001 runtime schema_version mismatch")

    playback = contract.build_playback_manifest(config)
    runtime_frames = runtime.get("frames")
    if not isinstance(runtime_frames, list) or len(runtime_frames) != len(playback["frames"]):
        raise contract.ContractError("N001 runtime frame count does not match frozen playback")

    frames = []
    for expected, raw in zip(playback["frames"], runtime_frames, strict=True):
        if raw.get("frame") != expected["frame"]:
            raise contract.ContractError("N001 runtime frame order/index mismatch")
        quality = raw.get("quality")
        memory = raw.get("memory_bytes")
        if not isinstance(quality, dict) or not isinstance(memory, dict):
            raise contract.ContractError("N001 runtime quality/memory payload is malformed")
        frames.append(
            {
                "frame": expected["frame"],
                "scene_state_sha256": expected["state_sha256"],
                "output_hdr": raw.get("output_hdr"),
                "reference_hdr": raw.get("reference_hdr"),
                "reference": raw.get("reference"),
                "correctness": {
                    "traversal_runtime_errors": int(quality.get("traversal_runtime_errors", 1)),
                    "oob_errors": validation_errors,
                    "storage_failures": int(quality.get("storage_failures", 1)),
                    "lifetime_errors": lifetime_error_count(memory),
                    "alignment_valid": True,
                },
                "timing_us": raw.get("timing_us"),
                "memory_bytes": memory,
            }
        )

    provenance = {
        "schema_version": 1,
        "git": git_identity,
        "device": runtime.get("device"),
        "scene_sha256": config["scene"]["sha256"],
        "playback_sha256": playback["playback_sha256"],
        "validation_layer_error_lines": validation_errors,
        "frames": frames,
    }
    (root / "n001-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = contract.validate_target_artifact(root, config)
    (root / "n001-validation-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def run_target(root: Path, binary: Path, config: dict) -> int:
    git_identity = require_clean_lane_n()
    scene = validate_scene(config)
    if not binary.is_file():
        raise contract.ContractError(
            f"N001 target binary is missing: {binary}; build phos-n001 first"
        )

    root.mkdir(parents=True, exist_ok=True)
    command = [
        str(binary),
        "--artifact-dir",
        str(root),
        "--scene",
        str(scene),
    ]
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    (root / "n001-renderer-stdout.log").write_text(proc.stdout, encoding="utf-8")
    (root / "n001-renderer-stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N001 renderer/reference process failed with exit code {proc.returncode}"
        )

    errors = validation_error_count(proc.stderr)
    result = finalize_runtime_artifact(
        root, config, git_identity, errors
    )
    print("N001 target artifact validation: PASS")
    print(f"playback_sha256={result['playback_sha256']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N001 renderer/reference contract, target runner, and artifact validator"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--phase", choices=("contract", "target", "validate-target"), required=True
    )
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--target-artifact", type=Path)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())

    if args.phase == "contract":
        root = artifact_dir(args.artifact_dir)
        root.mkdir(parents=True, exist_ok=True)
        summary = contract.make_contract_smoke(root, config)
        (root / "n001-contract-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("N001 GPU-independent contract validation: PASS")
        print(f"playback_sha256={summary['playback_sha256']}")
        return 0

    if args.phase == "target":
        return run_target(
            artifact_dir(args.artifact_dir),
            args.binary.resolve(),
            config,
        )

    if args.target_artifact is None:
        parser.error("--target-artifact is required for --phase validate-target")
    result = contract.validate_target_artifact(args.target_artifact.resolve(), config)
    output = args.target_artifact.resolve() / "n001-validation-summary.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("N001 target artifact validation: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N001 contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
