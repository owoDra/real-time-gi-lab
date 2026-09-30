#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import j004_analysis as analysis
import j002_geometry as geometry

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-j-formal-crossover"
CONFIG = (
    ROOT
    / "research/lanes/lane-j-topology-backend-alternatives/experiments"
    / "005-formal-crossover-config.json"
)
EXPECTED_CONFIG_BLOB_SHA = "22951382f8a510bf176c7a427a12d7a2ae24e5d9"
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-j-topology-backend-alternatives"
    / "004-formal-crossover"
)

# Proves that "unchanged transient LBVH" and the retained hardened path use
# exactly the same recurrent F003 dynamic implementation in J004. Lane-G's
# hardening changed setup allocation lifetime; J004 holds static setup common.
EXPECTED_F003_BLOBS = {
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "f003_transient_lbvh.cpp": "17f55f17a35aaa5373074591af552636b1dfe82d",
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "f003_transient_lbvh.hpp": "ded4856b0fcb268ef8ca984338c073b4dace74eb",
    "shaders/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "f003_lbvh_builder.comp.glsl": "77db184be5fcee72fa6c4f5cf40cadf487dcedd4",
    "shaders/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "f003_dynamic_traversal.comp.glsl": "56c7e80d345cf890d0b73b16edb740c874ac8dff",
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "baseline/lane_b_traversal/b002_hwrt.cpp": "91456326f9d946aedec46ff479f5d68600ed14a2",
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "baseline/lane_b_traversal/b002_hwrt.hpp": "a00fbfbfd5b9b2fd3c36cd2ceed49c14d2c9f71c",
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "baseline/lane_b_traversal/b003_quantized_bvh8.hpp": "03ffe09f050f218cd18ffd6a22dfcfa5492000ed",
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "baseline/lane_b_traversal/b003_micro_bvh8.hpp": "4ff5a5ee799c112e0f5542ac24645b1a0faabe96",
}


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def host_snapshot() -> dict[str, object]:
    try:
        load = list(os.getloadavg())
    except OSError:
        load = [None, None, None]
    mem_available = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                mem_available = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    return {
        "loadavg_1m": load[0],
        "loadavg_5m": load[1],
        "loadavg_15m": load[2],
        "mem_available_bytes": mem_available,
        "monotonic_ns": time.monotonic_ns(),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def resolved_path(value: str | os.PathLike[str]) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def verify_frozen_sources() -> None:
    for relative, expected in EXPECTED_F003_BLOBS.items():
        actual = git("hash-object", relative)
        if actual != expected:
            raise RuntimeError(
                f"J004 recurrent F003 source drift for {relative}: "
                f"{actual} != {expected}"
            )


def load_materialized(
    config: dict[str, object],
) -> tuple[Path, dict[str, object], Path, Path]:
    root = resolved_path(str(config["j002"]["materialized_root"]))
    manifest_path = root / "j002-materialized-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"missing J002 materialized manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    producer = resolved_path(str(manifest["producer_stream_path"]))
    scene = resolved_path(str(manifest["scene"]))
    if not producer.is_file():
        raise RuntimeError(f"missing frozen producer stream: {producer}")
    if not scene.is_file():
        raise RuntimeError(f"missing frozen scene: {scene}")

    actual_producer_sha = sha256_file(producer)
    if actual_producer_sha != manifest["producer_stream_file_sha256"]:
        raise RuntimeError("J002 producer stream SHA256 changed")
    actual_scene_sha = sha256_file(scene)
    if actual_scene_sha != manifest["scene_sha256"]:
        raise RuntimeError("J002 scene SHA256 changed")

    expected_profiles = {
        str(item["name"])
        for item in config["j002"]["profiles"]
    }
    manifest_profiles = {
        str(item["name"])
        for item in manifest["profiles"]
    }
    if manifest_profiles != expected_profiles:
        raise RuntimeError("J002 materialized profile set drifted")

    manifest_by_name = {
        str(item["name"]): item
        for item in manifest["profiles"]
    }
    for profile in config["j002"]["profiles"]:
        name = str(profile["name"])
        profile_dir = root / name
        manifest_profile = manifest_by_name[name]
        expected_topology = str(profile["expected_topology_digest"])
        if str(manifest_profile.get("topology_digest")) != expected_topology:
            raise RuntimeError(
                f"J002 {name}: topology digest differs from frozen J004 input"
            )
        steps = manifest_profile.get("steps")
        if not isinstance(steps, list) or len(steps) != 8:
            raise RuntimeError(f"J002 {name}: expected exactly eight snapshots")
        by_index = {int(item["index"]): item for item in steps}
        if set(by_index) != set(range(8)):
            raise RuntimeError(f"J002 {name}: snapshot indices drifted")

        identities: list[dict[str, object]] = []
        for step in range(8):
            record = by_index[step]
            expected_file = f"{name}/step-{step:02d}.bin"
            if str(record.get("file")) != expected_file:
                raise RuntimeError(
                    f"J002 {name}/step-{step:02d}: snapshot path drifted"
                )
            snapshot = root / expected_file
            if not snapshot.is_file():
                raise RuntimeError(f"missing J002 snapshot: {snapshot}")
            triangles = geometry.read_snapshot(snapshot)
            actual_digest = geometry.snapshot_digest(triangles)
            if len(triangles) != int(record["primitive_count"]):
                raise RuntimeError(
                    f"J002 {name}/step-{step:02d}: primitive count drifted"
                )
            if actual_digest != str(record["snapshot_digest"]):
                raise RuntimeError(
                    f"J002 {name}/step-{step:02d}: geometry digest drifted"
                )
            identities.append({
                "primitive_count": len(triangles),
                "snapshot_digest": actual_digest,
            })
        for previous, current in zip(identities, identities[1:]):
            if previous["primitive_count"] == current["primitive_count"]:
                raise RuntimeError(
                    f"J002 {name}: adjacent primitive counts did not change"
                )
            if previous["snapshot_digest"] == current["snapshot_digest"]:
                raise RuntimeError(
                    f"J002 {name}: adjacent geometry snapshots did not change"
                )

    return root, manifest, producer, scene


def same_device(devices: list[dict[str, object]]) -> bool:
    if not devices:
        return False
    keys = (
        "device",
        "driver_name",
        "driver_info",
        "api_version",
        "driver_version",
        "vendor_id",
        "device_id",
        "timestamp_period_ns",
    )
    first = devices[0]
    if any(first.get(key) in (None, "") for key in keys):
        return False
    return all(
        all(device.get(key) == first.get(key) for key in keys)
        for device in devices
    )


def run_validation(
    executable: Path,
    root: Path,
    config: dict[str, object],
    profile: str,
    track: str,
    variant: str,
    profile_dir: Path,
    producer: Path,
    scene: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    process_id = f"validation-{profile}-{track}-{variant}"
    process_root = root / "validation" / process_id
    process_root.mkdir(parents=True, exist_ok=False)

    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--profile-dir",
        str(profile_dir),
        "--producer-stream",
        str(producer),
        "--scene",
        str(scene),
        "--track",
        track,
        "--validation-only",
        "--validation-variant",
        variant,
        "--validation-rays",
        str(config["j002"]["validation_ray_prefix_count"]),
        "--validation",
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(process_root)
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (process_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (process_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(
            f"J004 validation failed for {profile}/{track}/{variant}; "
            "formal timing is forbidden"
        )

    validation = json.loads(
        (process_root / "j004-validation.json").read_text(encoding="utf-8")
    )
    if not bool(validation.get("passed")):
        raise RuntimeError(
            f"J004 validation artifact rejected {profile}/{track}/{variant}"
        )
    for field in config["j002"]["required_correctness_zero_fields"]:
        if int(validation.get(field, -1)) != 0:
            raise RuntimeError(
                f"J004 validation {profile}/{track}/{variant}: "
                f"{field} is non-zero or missing"
            )
    if validation.get("workload_identity_match") is not True:
        raise RuntimeError(
            f"J004 validation {profile}/{track}/{variant}: "
            "workload identity did not match"
        )
    device = json.loads(
        (process_root / "j004-device.json").read_text(encoding="utf-8")
    )
    return validation, device


def run_timing_process(
    executable: Path,
    root: Path,
    config: dict[str, object],
    profile: str,
    track: str,
    comparison: str,
    block: int,
    profile_dir: Path,
    producer: Path,
    scene: Path,
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    dict[str, object],
]:
    time.sleep(float(config["timing"]["settle_seconds"]))
    start_order = str(config["timing"]["start_order_by_block"][block])
    process_id = f"{profile}-{track}-{comparison}-b{block:02d}"
    process_root = root / "processes" / process_id
    process_root.mkdir(parents=True, exist_ok=False)

    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--profile-dir",
        str(profile_dir),
        "--producer-stream",
        str(producer),
        "--scene",
        str(scene),
        "--track",
        track,
        "--comparison",
        comparison,
        "--start-order",
        start_order,
        "--warmup-pairs",
        str(config["timing"]["warmup_pairs"]),
        "--measured-pairs",
        str(config["timing"]["measured_pairs"]),
        "--batch-transitions",
        str(config["recurring_boundary"]["batch_transitions"]),
    ]
    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(process_root)

    before = host_snapshot()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = host_snapshot()
    (process_root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (process_root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)

    if proc.returncode != 0:
        raise RuntimeError(
            f"J004 formal process {process_id} failed; "
            "retain this campaign as invalid/interrupted and do not favorable-rerun"
        )

    raw_rows = read_csv(process_root / "j004-samples.csv")
    warmup_pairs = int(config["timing"]["warmup_pairs"])
    measured_pairs = int(config["timing"]["measured_pairs"])
    expected_rows = 2 * (warmup_pairs + measured_pairs)
    if len(raw_rows) != expected_rows:
        raise RuntimeError(
            f"{process_id}: expected {expected_rows} rows, got {len(raw_rows)}"
        )

    expected_a = (
        "lane-e-object-local-hwrt-rebuild"
        if track == "primary"
        else "lane-e-object-local-software-b003-rebuild"
    )
    expected_b = (
        expected_a
        if comparison == "control"
        else (
            "vanilla-software-bvh-rebuild"
            if comparison == "accounting"
            else "hardened-transient-lbvh"
        )
    )

    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        role = raw["role"]
        if role not in {"A", "B"}:
            raise RuntimeError(f"{process_id}: invalid role")
        expected_variant = expected_a if role == "A" else expected_b
        if raw["variant"] != expected_variant:
            raise RuntimeError(f"{process_id}: role/variant mismatch")

        for field in config["j002"]["required_boundary_fields"]:
            if field not in raw or raw[field] == "":
                raise RuntimeError(
                    f"{process_id}: required boundary field missing: {field}"
                )
            value = float(raw[field])
            if not math.isfinite(value) or value < 0.0:
                raise RuntimeError(
                    f"{process_id}: invalid boundary field {field}"
                )

        gpu = float(raw["gpu_us"])
        wall = float(raw["complete_wall_us"])
        if not math.isfinite(gpu) or gpu <= 0:
            raise RuntimeError(f"{process_id}: invalid GPU timestamp")
        if not math.isfinite(wall) or wall <= 0:
            raise RuntimeError(f"{process_id}: invalid complete CPU wall")
        if wall < gpu:
            raise RuntimeError(
                f"{process_id}: complete CPU wall is smaller than GPU time"
            )
        if int(raw["storage_failures"]) != 0:
            raise RuntimeError(f"{process_id}: storage failures are non-zero")
        if int(raw["max_resident_bytes"]) <= 0:
            raise RuntimeError(f"{process_id}: resident memory is zero")
        if int(raw["max_true_peak_resident_bytes"]) < int(raw["max_resident_bytes"]):
            raise RuntimeError(f"{process_id}: true peak is below live resident memory")
        classified = (
            int(raw["persistent_bytes"])
            + int(raw["transient_bytes"])
            + int(raw["scratch_bytes"])
        )
        if classified != int(raw["max_resident_bytes"]):
            raise RuntimeError(
                f"{process_id}: allocation lifetime classes do not sum to live residency"
            )
        if int(raw["old_new_overlap_bytes"]) > int(raw["true_peak_resident_bytes"]):
            raise RuntimeError(
                f"{process_id}: old/new overlap exceeds true peak residency"
            )

        enriched: dict[str, object] = dict(raw)
        enriched.update(
            {
                "profile": profile,
                "track": track,
                "comparison": comparison,
                "block": block,
                "process_id": process_id,
                "start_order": start_order,
            }
        )
        rows.append(enriched)

    device = json.loads(
        (process_root / "j004-device.json").read_text(encoding="utf-8")
    )
    observation = {
        "profile": profile,
        "track": track,
        "comparison": comparison,
        "block": block,
        "process_id": process_id,
        "start_order": start_order,
        "before": before,
        "after": after,
    }
    return rows, observation, device


def flatten_process(row: dict[str, object]) -> dict[str, object]:
    output = {
        "track": row["track"],
        "profile": row["profile"],
        "comparison": row["comparison"],
        "block": row["block"],
        "process_id": row["process_id"],
    }
    for axis in ("gpu", "wall"):
        for key, value in row[axis].items():
            output[f"{axis}_{key}"] = value
    return output


def final_outcome(
    summaries: dict[str, dict[str, object]],
    class_results: dict[str, dict[str, object]],
) -> tuple[str, bool]:
    retained = any(
        bool(class_result["retained"])
        for track in class_results.values()
        for class_result in track.values()
    )
    if retained:
        return "conditional topology backend accepted", True

    conclusive = True
    for track in summaries.values():
        for profile in track.values():
            control = profile["gpu_primary"]["control"]
            candidate = profile["gpu_primary"]["candidate"]
            if not bool(control["passed"]) or not bool(candidate["repeatable"]):
                conclusive = False
    return (
        "Lane E rebuild retained" if conclusive else "measurement-limited",
        False,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"J004 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("J004 formal campaign requires a clean worktree")

    config_blob = git("hash-object", str(CONFIG.relative_to(ROOT)))
    if config_blob != EXPECTED_CONFIG_BLOB_SHA:
        raise RuntimeError(
            "J004 execution config changed after freeze; target timing forbidden"
        )
    verify_frozen_sources()

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["plan_version"] != "lane-j-j004-formal-v2":
        raise RuntimeError("unexpected J004 plan version")
    if config["accepted_timing_validation"]:
        raise RuntimeError("accepted J004 timing must disable validation layers")
    if config["axis_roles"]["primary_performance"] != "gpu_timestamp":
        raise RuntimeError("J004 primary axis drifted")
    if config["axis_roles"]["cpu_wall"] != "diagnostic-health-provenance-only":
        raise RuntimeError("J004 CPU-wall role drifted")
    if int(config["timing"]["instability_rerun_budget"]) != 0:
        raise RuntimeError("J004 instability rerun budget must be zero")
    if int(config["timing"]["completed_campaign_rerun_budget"]) != 0:
        raise RuntimeError("J004 completed campaign rerun budget must be zero")
    if config["timing"]["sample_exclusion"] != "forbidden":
        raise RuntimeError("J004 sample exclusion policy drifted")
    if float(config["gpu_primary_criteria"]["promotion_ratio_max"]) > 0.95:
        raise RuntimeError("J004 promotion threshold is below Lane-K 5% floor")
    if int(config["j002"]["validation_ray_prefix_count"]) != 0:
        raise RuntimeError(
            "J004 accepted validation must check every frozen A001 replay ray"
        )
    if config["cpu_wall_health"]["decision_use"] != "diagnostic-health-provenance-only":
        raise RuntimeError("J004 CPU-wall decision role drifted")

    completed = [
        path
        for path in CAMPAIGN_ROOT.rglob("j004-summary.json")
        if path.is_file()
    ]
    if completed:
        joined = ", ".join(str(path.relative_to(ROOT)) for path in completed)
        raise RuntimeError(
            "J004 completed-campaign rerun budget is zero; existing summary: "
            + joined
        )

    materialized_root, manifest, producer, scene = load_materialized(config)
    executable = args.build_dir / "phos-lane-j-j004-formal-process"
    if not executable.is_file():
        raise RuntimeError(f"missing J004 executable: {executable}")

    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = args.artifact_dir or (Path(env_root) if env_root else None)
    if root is None:
        root = CAMPAIGN_ROOT / stamp
    root.mkdir(parents=True, exist_ok=bool(env_root))

    (root / "j004-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "j004-input-provenance.json").write_text(
        json.dumps(
            {
                "materialized_root": str(materialized_root),
                "manifest_sha256": sha256_file(
                    materialized_root / "j002-materialized-manifest.json"
                ),
                "producer_stream": str(producer),
                "producer_stream_sha256": sha256_file(producer),
                "scene": str(scene),
                "scene_sha256": sha256_file(scene),
                "j002_manifest": manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo:
        proc = subprocess.run(
            [vulkaninfo, "--summary"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        (root / "j004-vulkaninfo-summary.txt").write_text(
            proc.stdout, encoding="utf-8"
        )

    progress: dict[str, object] = {
        "state": "validating",
        "git_commit": git("rev-parse", "HEAD"),
        "plan_version": config["plan_version"],
        "completed_validations": [],
        "completed_processes": [],
    }

    def save_progress() -> None:
        (root / "j004-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    save_progress()
    validation_rows: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []
    try:
        for profile_entry in config["j002"]["profiles"]:
            profile = str(profile_entry["name"])
            profile_dir = materialized_root / profile
            validation_matrix = [
                ("primary", "control"),
                ("primary", "candidate"),
                ("software", "control"),
                ("software", "candidate"),
                ("software", "accounting"),
            ]
            profile_resolved_digests: list[int] = []
            for track, variant in validation_matrix:
                progress["current"] = {
                    "phase": "validation",
                    "profile": profile,
                    "track": track,
                    "variant": variant,
                }
                save_progress()
                validation, device = run_validation(
                    executable,
                    root,
                    config,
                    profile,
                    track,
                    variant,
                    profile_dir,
                    producer,
                    scene,
                )
                validation_rows.append(
                    {
                        "profile": profile,
                        "track": track,
                        **validation,
                    }
                )
                profile_resolved_digests.append(
                    int(validation["resolved_digest"])
                )
                devices.append(device)
                progress["completed_validations"].append(
                    f"{profile}/{track}/{variant}"
                )
                save_progress()

            if len(set(profile_resolved_digests)) != 1:
                raise RuntimeError(
                    f"J004 {profile}: C001 resolved-output digest differs "
                    "between same-workload variants; formal timing forbidden"
                )

        if not same_device(devices):
            raise RuntimeError(
                "J004 validation device/driver/API provenance changed"
            )

        (root / "j004-validation-summary.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "rows": validation_rows,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        progress["state"] = "timing"
        save_progress()

        raw_rows: list[dict[str, object]] = []
        observations: list[dict[str, object]] = []
        timing_devices: list[dict[str, object]] = []

        for track in ("primary", "software"):
            for profile_entry in config["j002"]["profiles"]:
                profile = str(profile_entry["name"])
                profile_dir = materialized_root / profile
                expected_comparisons = tuple(
                    config["timing"]["comparisons"][track]
                )
                orders = config["timing"]["comparison_orders"][track]
                if len(orders) != int(config["timing"]["fresh_process_blocks"]):
                    raise RuntimeError(
                        f"J004 {track}: comparison-order block count drifted"
                    )
                for block, order in enumerate(orders):
                    if set(order) != set(expected_comparisons) or len(order) != len(expected_comparisons):
                        raise RuntimeError(
                            f"J004 {track}/block-{block}: comparison order drifted"
                        )
                    for comparison in order:
                        progress["current"] = {
                            "phase": "timing",
                            "profile": profile,
                            "track": track,
                            "comparison": comparison,
                            "block": block,
                        }
                        save_progress()
                        rows, observation, device = run_timing_process(
                            executable,
                            root,
                            config,
                            profile,
                            track,
                            comparison,
                            block,
                            profile_dir,
                            producer,
                            scene,
                        )
                        raw_rows.extend(rows)
                        observations.append(observation)
                        timing_devices.append(device)
                        progress["completed_processes"].append(
                            observation["process_id"]
                        )
                        save_progress()

    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    if not same_device(devices + timing_devices):
        raise RuntimeError(
            "J004 device/driver/API provenance changed during campaign"
        )

    process_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in raw_rows:
        process_groups[str(row["process_id"])].append(row)
    process_rows = [
        analysis.summarize_process(rows)
        for rows in process_groups.values()
    ]

    profile_summaries: dict[str, dict[str, object]] = {}
    class_results: dict[str, dict[str, object]] = {}
    for track in ("primary", "software"):
        profile_summaries[track] = {}
        for profile_entry in config["j002"]["profiles"]:
            profile = str(profile_entry["name"])
            rows = [
                row
                for row in process_rows
                if row["track"] == track and row["profile"] == profile
            ]
            profile_summaries[track][profile] = analysis.summarize_profile(
                rows, config
            )
        class_results[track] = analysis.class_decisions(
            profile_summaries[track], config
        )

    outcome, j005_eligible = final_outcome(profile_summaries, class_results)

    accounting_processes: dict[str, list[dict[str, object]]] = {}
    for profile_entry in config["j002"]["profiles"]:
        profile = str(profile_entry["name"])
        accounting_processes[profile] = [
            row
            for row in process_rows
            if row["track"] == "software"
            and row["profile"] == profile
            and row["comparison"] == "accounting"
        ]

    write_csv(root / "j004-raw.csv", raw_rows)
    write_csv(
        root / "j004-process-summary.csv",
        [flatten_process(row) for row in process_rows],
    )
    (root / "j004-host-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "j004-devices.json").write_text(
        json.dumps(devices + timing_devices, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "plan_version": config["plan_version"],
        "git_commit": git("rev-parse", "HEAD"),
        "branch": EXPECTED_BRANCH,
        "target_gpu": config["target_gpu"],
        "clustered_two_level_bvh": "rejected-before-timing",
        "unchanged_transient_lbvh": (
            "recurrent-source-identical-to-hardened-path-no-separate-timing"
        ),
        "all_samples_retained": True,
        "sample_exclusion": "none",
        "instability_rerun_budget": 0,
        "completed_campaign_rerun_budget": 0,
        "device_provenance_consistent": True,
        "axis_roles": config["axis_roles"],
        "profile_summaries": profile_summaries,
        "class_decisions": class_results,
        "accounting_control": {
            "decision_use": "diagnostic/attribution-only",
            "process_counts": {
                profile: len(rows)
                for profile, rows in accounting_processes.items()
            },
            "process_median_gpu_ratios": {
                profile: [
                    float(row["gpu"]["median_ratio"])
                    for row in rows
                ]
                for profile, rows in accounting_processes.items()
            },
        },
        "outcome": outcome,
        "j005_eligible": j005_eligible,
    }
    (root / "j004-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    progress["state"] = "complete"
    progress.pop("current", None)
    save_progress()

    print(f"J004 artifacts: {root}")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
