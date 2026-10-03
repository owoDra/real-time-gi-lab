#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import n002_contract as contract

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/002-n002-config.json"
DEFAULT_BINARY = ROOT / "build/phos-n002"
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
VALIDATION_ERROR_RE = re.compile(
    r"Validation Error|\bVUID-[A-Za-z0-9_-]+|\bUNASSIGNED-[A-Za-z0-9_-]+"
)


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value).resolve()
    return (
        ROOT
        / "out/research/lane-n-end-to-end-renderer/002-current-architecture-baseline-core/manual"
    ).resolve()


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
            f"N002 target evidence requires research-lane-n-end-to-end-renderer, got {branch!r}"
        )
    if len(commit) != 40:
        raise contract.ContractError("N002 target evidence requires a full Git commit SHA")
    if dirty:
        raise contract.ContractError("N002 target evidence requires a clean worktree")
    return {"branch": branch, "commit": commit, "dirty": False}


def scene_provenance(config: dict) -> tuple[Path, dict[str, object]]:
    scene = (ROOT / config["scene"]["path"]).resolve()
    if not scene.is_file():
        raise contract.ContractError(f"N002 scene is missing: {scene}")
    actual = contract.sha256_file(scene)
    expected = config["scene"]["sha256"]
    if actual != expected:
        raise contract.ContractError(
            f"N002 scene digest mismatch: expected {expected}, got {actual}"
        )

    try:
        gltf = json.loads(scene.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise contract.ContractError(f"N002 could not parse scene glTF: {error}") from error

    scene_root = scene.parent.resolve()
    buffers: list[dict[str, object]] = []
    for index, entry in enumerate(gltf.get("buffers", [])):
        if not isinstance(entry, dict):
            raise contract.ContractError(f"N002 glTF buffer[{index}] is not an object")
        uri = entry.get("uri")
        if not isinstance(uri, str) or not uri:
            raise contract.ContractError(
                f"N002 glTF buffer[{index}] must use a local external URI"
            )
        if uri.lower().startswith("data:") or "://" in uri:
            raise contract.ContractError(
                f"N002 glTF buffer[{index}] must be a local external file"
            )
        relative = Path(unquote(uri))
        if relative.is_absolute() or ".." in relative.parts:
            raise contract.ContractError(
                f"N002 glTF buffer[{index}] escapes the scene directory"
            )
        path = (scene_root / relative).resolve()
        if not path.is_relative_to(scene_root) or not path.is_file():
            raise contract.ContractError(
                f"N002 glTF buffer[{index}] is missing or outside scene directory: {uri}"
            )
        buffers.append(
            {
                "index": index,
                "uri": uri,
                "bytes": path.stat().st_size,
                "sha256": contract.sha256_file(path),
            }
        )

    bundle_payload = {"scene_sha256": actual, "buffers": buffers}
    bundle_sha256 = contract.sha256_bytes(
        contract.canonical_json_bytes(bundle_payload)
    )
    return scene, {**bundle_payload, "bundle_sha256": bundle_sha256}


def validation_error_count(stderr: str) -> int:
    return sum(1 for line in stderr.splitlines() if VALIDATION_ERROR_RE.search(line))


def lifetime_error_count(memory: dict[str, object]) -> int:
    values: dict[str, int] = {}
    for key, value in memory.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return 1
        values[key] = value
    peak = values.get("true_lifetime_peak")
    if peak is None:
        return 1
    components = [value for key, value in values.items() if key != "true_lifetime_peak"]
    return 0 if components and peak >= max(components) else 1


def is_nixos(os_release: Path = Path("/etc/os-release")) -> bool:
    try:
        lines = os_release.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key == "ID":
            return value.strip().strip('"\'') == "nixos"
    return False


def renderer_command(binary: Path, root: Path, scene: Path) -> list[str]:
    command = [
        str(binary),
        "--artifact-dir",
        str(root),
        "--scene",
        str(scene),
    ]
    if not is_nixos():
        return command
    if not VULKAN_WRAPPER.is_file():
        raise contract.ContractError(
            f"N002 requires the NixOS Vulkan launcher but it is missing: {VULKAN_WRAPPER}"
        )
    return ["bash", str(VULKAN_WRAPPER), *command]


def finalize_runtime_artifact(
    root: Path,
    config: dict,
    git_identity: dict[str, object],
    scene_identity: dict[str, object],
    validation_errors: int,
) -> dict:
    runtime_path = root / "n002-runtime.json"
    if not runtime_path.is_file():
        raise contract.ContractError("N002 runtime did not produce n002-runtime.json")
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    if runtime.get("schema_version") != 1 or runtime.get("phase") != "core-baseline":
        raise contract.ContractError("N002 runtime identity mismatch")

    playback = contract.build_playback_manifest(config)
    runtime_frames = runtime.get("frames")
    if not isinstance(runtime_frames, list) or len(runtime_frames) != len(playback["frames"]):
        raise contract.ContractError("N002 runtime frame count does not match frozen playback")

    frames: list[dict[str, object]] = []
    for expected, raw in zip(playback["frames"], runtime_frames, strict=True):
        if raw.get("frame") != expected["frame"] or raw.get("scenario") != expected["kind"]:
            raise contract.ContractError("N002 runtime frame order/scenario mismatch")
        quality = raw.get("quality")
        memory = raw.get("memory_bytes")
        if not isinstance(quality, dict) or not isinstance(memory, dict):
            raise contract.ContractError("N002 runtime quality/memory payload malformed")
        frames.append(
            {
                "frame": expected["frame"],
                "scene_state_sha256": expected["state_sha256"],
                "output_hdr": raw.get("output_hdr"),
                "reference_hdr": raw.get("reference_hdr"),
                "reference": raw.get("reference"),
                "correctness": {
                    "traversal_runtime_errors": int(
                        quality.get("traversal_runtime_errors", 1)
                    ),
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
        "phase": "core-baseline",
        "git": git_identity,
        "device": runtime.get("device"),
        "scene_sha256": config["scene"]["sha256"],
        "scene_bundle": scene_identity,
        "playback_sha256": playback["playback_sha256"],
        "validation_layer_error_lines": validation_errors,
        "frames": frames,
    }
    (root / "n002-provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = contract.validate_target_artifact(root, config)
    result["scene_bundle_sha256"] = scene_identity["bundle_sha256"]
    result["scene_external_buffer_count"] = len(scene_identity["buffers"])
    (root / "n002-validation-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def run_target(root: Path, binary: Path, config: dict) -> int:
    git_identity = require_clean_lane_n()
    scene, scene_identity = scene_provenance(config)
    if not binary.is_file():
        raise contract.ContractError(
            f"N002 target binary is missing: {binary}; build phos-n002 first"
        )

    root.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        renderer_command(binary, root, scene),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    (root / "n002-renderer-stdout.log").write_text(proc.stdout, encoding="utf-8")
    (root / "n002-renderer-stderr.log").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N002 renderer/reference process failed with exit code {proc.returncode}"
        )

    result = finalize_runtime_artifact(
        root,
        config,
        git_identity,
        scene_identity,
        validation_error_count(proc.stderr),
    )
    print("N002 core target artifact validation: PASS")
    print(f"playback_sha256={result['playback_sha256']}")
    print(f"scene_bundle_sha256={result['scene_bundle_sha256']}")
    print("N002 remains incomplete until topology-changing/high-churn is integrated.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lane N N002 core current-architecture end-to-end runner"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "target", "validate-target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--target-artifact", type=Path)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    playback = contract.build_playback_manifest(config)

    if args.phase == "contract":
        root = artifact_dir(args.artifact_dir)
        root.mkdir(parents=True, exist_ok=True)
        summary = {
            "schema_version": 1,
            "status": "pass",
            "phase": "core-baseline",
            "n002_complete": False,
            "pending_scenarios": ["topology-changing-high-churn"],
            "playback_sha256": playback["playback_sha256"],
        }
        (root / "n002-contract-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("N002 core GPU-independent contract validation: PASS")
        print(f"playback_sha256={playback['playback_sha256']}")
        return 0

    if args.phase == "target":
        return run_target(artifact_dir(args.artifact_dir), args.binary.resolve(), config)

    if args.target_artifact is None:
        parser.error("--target-artifact is required for --phase validate-target")
    target_root = args.target_artifact.resolve()
    result = contract.validate_target_artifact(target_root, config)
    (target_root / "n002-validation-summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("N002 core target artifact validation: PASS")
    print("N002 remains incomplete until topology-changing/high-churn is integrated.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N002 contract error: {error}", file=sys.stderr)
        raise SystemExit(2)
