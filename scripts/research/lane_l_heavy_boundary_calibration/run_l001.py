#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
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

import l001_analysis as analysis

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-l-heavy-boundary-calibration"
CONFIG = (
    ROOT
    / "research/lanes/lane-l-heavy-boundary-calibration/experiments"
    / "002-l001-config.json"
)
EXPECTED_CONFIG_BLOB_SHA = "f3ec006e1e4c0b236463289af73b5405fdc4d5d3"
J004_CONFIG = (
    ROOT
    / "research/lanes/lane-j-topology-backend-alternatives/experiments"
    / "005-formal-crossover-config.json"
)
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-l-heavy-boundary-calibration"
    / "001-heavy-boundary-same-variant-calibration"
)

EXPECTED_SOURCE_BLOBS = {
    "src/research/lane_l_heavy_boundary_calibration/l001_formal_process.cpp":
        "f8803228893cd3cd20a788919758e203563810e2",
    "src/research/lane_l_heavy_boundary_calibration/CMakeLists.txt":
        "dd605f90bc928718107ae9840ba69b128e3bb6d9",
    "scripts/research/lane_l_heavy_boundary_calibration/l001_analysis.py":
        "cb17b26073d9c256103064f3edd8236d9c51dbfd",
    "scripts/research/lane_l_heavy_boundary_calibration/test_l001_analysis.py":
        "3a86fa17dfde27f35df3348987bc2cf39c29752e",
    "scripts/research/lane_l_heavy_boundary_calibration/test_l001_protocol.py":
        "9a8f35e90f5b717244db0a20bf5c44435e3aa77e",
    "scripts/research/lane_l_heavy_boundary_calibration/test_l001_runtime_contract.py":
        "1b3a52cca7df954be35800d2f719c961698b5c73",
    "scripts/research/lane_j_topology_backend_alternatives/run_j004.py":
        "788153017adab4357e38e5cdaad57cef9471da45",
    "scripts/research/lane_j_topology_backend_alternatives/j004_analysis.py":
        "9dd6e87d2f5ba807410297d11d9fba32790af2b9",
    "src/research/lane_j_topology_backend_alternatives/formal_runtime/"
    "j004_formal_process.cpp":
        "5d66a377779a76e226864965702cf7d402e0f236",
}

J004_RUNNER = (
    ROOT
    / "scripts/research/lane_j_topology_backend_alternatives/run_j004.py"
)
J004_SCRIPT_DIR = str(J004_RUNNER.parent)
if J004_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, J004_SCRIPT_DIR)
_spec = importlib.util.spec_from_file_location(
    "lane_j_run_j004_for_l001",
    J004_RUNNER,
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load frozen J004 runner")
j004 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(j004)


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


def host_snapshot() -> dict[str, object]:
    try:
        load = list(os.getloadavg())
    except OSError:
        load = [None, None, None]
    available = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                available = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    return {
        "loadavg_1m": load[0],
        "loadavg_5m": load[1],
        "loadavg_15m": load[2],
        "mem_available_bytes": available,
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


def flatten_process(row: dict[str, object]) -> dict[str, object]:
    out = {
        "environment": row["environment"],
        "profile": row["profile"],
        "track": row["track"],
        "comparison": row["comparison"],
        "block": row["block"],
        "process_id": row["process_id"],
    }
    for axis in ("gpu", "wall"):
        for key, value in row[axis].items():
            out[f"{axis}_{key}"] = value
    return out


def verify_sources(config: dict[str, object]) -> None:
    actual_config = git("hash-object", str(CONFIG.relative_to(ROOT)))
    if actual_config != EXPECTED_CONFIG_BLOB_SHA:
        raise RuntimeError(
            "L001 frozen config changed before target timing: "
            f"{actual_config} != {EXPECTED_CONFIG_BLOB_SHA}"
        )
    actual_j004_config = git("hash-object", str(J004_CONFIG.relative_to(ROOT)))
    expected_j004 = str(config["j004_import"]["j004_config_blob"])
    if actual_j004_config != expected_j004:
        raise RuntimeError(
            "J004 imported config changed before L001 timing: "
            f"{actual_j004_config} != {expected_j004}"
        )
    # Re-run the exact J004 v7 source/shader-tree freeze verification because
    # L001 intentionally executes that heavy-boundary implementation rather
    # than merely copying its top-level process source.
    j004.verify_frozen_sources()

    for path, expected in EXPECTED_SOURCE_BLOBS.items():
        actual = git("hash-object", path)
        if actual != expected:
            raise RuntimeError(
                f"L001 source drift for {path}: {actual} != {expected}"
            )


def validation_passed(
    validation: dict[str, object],
    config: dict[str, object],
) -> bool:
    if validation.get("passed") is not True:
        return False
    if validation.get("resolved_output_identity") is not True:
        return False
    allocation = validation.get("allocation_lifetime")
    if not isinstance(allocation, dict) or allocation.get("consistent") is not True:
        return False
    roles = validation.get("roles")
    if not isinstance(roles, dict) or set(roles) != {"A", "B"}:
        return False
    for role in ("A", "B"):
        record = roles[role]
        if not isinstance(record, dict):
            return False
        if record.get("workload_identity_match") is not True:
            return False
        for field in config["j002"]["required_correctness_zero_fields"]:
            if int(record.get(field, -1)) != 0:
                return False
    return True


def run_validation(
    executable: Path,
    root: Path,
    config: dict[str, object],
    environment: str,
    profile: str,
    track: str,
    profile_dir: Path,
    producer: Path,
    scene: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    process_id = f"{environment}-{profile}-{track}"
    process_root = root / "validation" / process_id
    process_root.mkdir(parents=True, exist_ok=False)

    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--environment",
        environment,
        "--profile-dir",
        str(profile_dir),
        "--producer-stream",
        str(producer),
        "--scene",
        str(scene),
        "--track",
        track,
        "--comparison",
        "control",
        "--validation-only",
        "--validation-variant",
        "control",
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

    validation_path = process_root / "l001-validation.json"
    if proc.returncode != 0:
        detail = "validation artifact unavailable"
        if validation_path.is_file():
            detail = validation_path.read_text(encoding="utf-8")
        raise RuntimeError(
            f"L001 validation failed for {process_id}; timing forbidden; "
            f"validation={detail}"
        )

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not validation_passed(validation, config):
        raise RuntimeError(
            f"L001 validation artifact rejected {process_id}"
        )
    if validation.get("environment") != environment:
        raise RuntimeError(f"{process_id}: environment identity mismatch")
    if validation.get("track") != track:
        raise RuntimeError(f"{process_id}: track identity mismatch")

    device = json.loads(
        (process_root / "l001-device.json").read_text(encoding="utf-8")
    )
    if device.get("environment") != environment:
        raise RuntimeError(f"{process_id}: device environment mismatch")
    if device.get("device") != config["target_gpu"]:
        raise RuntimeError(
            f"{process_id}: wrong GPU {device.get('device')!r}"
        )
    return validation, device


def run_timing_process(
    executable: Path,
    root: Path,
    config: dict[str, object],
    environment: str,
    profile: str,
    track: str,
    block: int,
    profile_dir: Path,
    producer: Path,
    scene: Path,
) -> tuple[list[dict[str, object]], dict[str, object], dict[str, object]]:
    time.sleep(float(config["timing"]["settle_seconds"]))
    start_order = str(config["timing"]["start_order_by_block"][block])
    process_id = f"{environment}-{profile}-{track}-b{block:02d}"
    process_root = root / "processes" / process_id
    process_root.mkdir(parents=True, exist_ok=False)

    command = [
        "bash",
        str(ROOT / "scripts/run_with_vulkan.sh"),
        str(executable),
        "--environment",
        environment,
        "--profile-dir",
        str(profile_dir),
        "--producer-stream",
        str(producer),
        "--scene",
        str(scene),
        "--track",
        track,
        "--comparison",
        "control",
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
            f"L001 timing process {process_id} failed; "
            "campaign is invalid and must not be timing-rerun"
        )

    rows: list[dict[str, object]] = []
    control_variant = str(config["controls"][track])
    raw_rows = read_csv(process_root / "l001-samples.csv")
    expected_rows = (
        int(config["timing"]["warmup_pairs"])
        + int(config["timing"]["measured_pairs"])
    ) * 2
    if len(raw_rows) != expected_rows:
        raise RuntimeError(
            f"{process_id}: expected {expected_rows} sample rows, "
            f"got {len(raw_rows)}"
        )
    for raw in raw_rows:
        if raw["variant"] != control_variant:
            raise RuntimeError(
                f"{process_id}: non-control variant entered L001 timing"
            )
        gpu_us = float(raw["gpu_us"])
        wall_us = float(raw["complete_wall_us"])
        if not math.isfinite(gpu_us) or gpu_us <= 0.0:
            raise RuntimeError(f"{process_id}: invalid GPU timestamp sample")
        if not math.isfinite(wall_us) or wall_us <= 0.0:
            raise RuntimeError(f"{process_id}: invalid CPU wall sample")
        if wall_us < gpu_us:
            raise RuntimeError(
                f"{process_id}: complete CPU wall is smaller than GPU timestamp"
            )
        enriched: dict[str, object] = dict(raw)
        enriched.update({
            "environment": environment,
            "profile": profile,
            "track": track,
            "comparison": "control",
            "block": block,
            "process_id": process_id,
            "start_order": start_order,
            "timed_memory_decision_use": "diagnostic-only",
        })
        rows.append(enriched)

    device = json.loads(
        (process_root / "l001-device.json").read_text(encoding="utf-8")
    )
    if device.get("environment") != environment:
        raise RuntimeError(f"{process_id}: device environment mismatch")
    if device.get("device") != config["target_gpu"]:
        raise RuntimeError(
            f"{process_id}: wrong GPU {device.get('device')!r}"
        )

    observation = {
        "environment": environment,
        "profile": profile,
        "track": track,
        "block": block,
        "process_id": process_id,
        "start_order": start_order,
        "before": before,
        "after": after,
    }
    return rows, observation, device


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
        raise RuntimeError(f"L001 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("L001 requires a clean worktree")

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config.get("plan_version") != "lane-l-l001-v1":
        raise RuntimeError("L001 requires frozen plan lane-l-l001-v1")
    if config.get("architecture_ranking_allowed") is not False:
        raise RuntimeError("L001 architecture ranking must remain forbidden")
    verify_sources(config)

    timing = config["timing"]
    if bool(timing["accepted_timing_validation"]):
        raise RuntimeError("accepted L001 timing must disable validation layers")
    if config["axis_roles"]["primary_performance"] != "gpu_timestamp":
        raise RuntimeError("L001 primary axis drifted")
    if config["axis_roles"]["cpu_wall"] != "diagnostic-health-provenance-only":
        raise RuntimeError("L001 CPU-wall role drifted")
    if timing["sample_exclusion"] != "forbidden":
        raise RuntimeError("L001 sample exclusion policy drifted")
    if int(timing["instability_rerun_budget"]) != 0:
        raise RuntimeError("L001 instability rerun budget must be zero")
    if int(timing["completed_campaign_rerun_budget"]) != 0:
        raise RuntimeError("L001 completed campaign rerun budget must be zero")
    if int(timing["warmup_pairs"]) != 4 or int(timing["measured_pairs"]) != 12:
        raise RuntimeError("L001 paired sample shape drifted")
    if int(timing["fresh_process_blocks"]) != 8:
        raise RuntimeError("L001 fresh-process block count drifted")
    if int(config["recurring_boundary"]["batch_transitions"]) != 16:
        raise RuntimeError("L001 recurring boundary drifted")
    if bool(config["optional_single_runtime_diagnostic"]["enabled"]):
        raise RuntimeError("L001 optional single-runtime diagnostic was not frozen in")
    gate = config["gpu_control_health"]
    if (
        float(gate["control_max_abs_process_median_ratio"]) != 1.02
        or float(gate["control_process_median_span_ratio"]) != 1.03
        or float(gate["control_max_within_process_order_bias_ratio"]) != 1.02
    ):
        raise RuntimeError("L001 frozen J004 control-health gate drifted")

    completed = sorted(CAMPAIGN_ROOT.glob("*/l001-summary.json"))
    if completed:
        joined = ", ".join(
            str(path.parent.relative_to(ROOT)) for path in completed
        )
        raise RuntimeError(
            "L001 completed-campaign rerun budget is zero; existing summary: "
            + joined
        )

    j004_config = json.loads(J004_CONFIG.read_text(encoding="utf-8"))
    materialized_root, manifest, producer, scene = j004.load_materialized(
        j004_config
    )

    executable = args.build_dir / "phos-lane-l-l001-formal-process"
    if not executable.is_file():
        raise RuntimeError(f"missing executable: {executable}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    root = args.artifact_dir or (Path(env_root) if env_root else None)
    if root is None:
        root = CAMPAIGN_ROOT / stamp
    root.mkdir(parents=True, exist_ok=bool(env_root))

    (root / "l001-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "l001-input-provenance.json").write_text(
        json.dumps(
            {
                "materialized_root": str(materialized_root),
                "manifest_sha256": j004.sha256_file(
                    materialized_root / "j002-materialized-manifest.json"
                ),
                "producer_stream": str(producer),
                "producer_stream_sha256": j004.sha256_file(producer),
                "scene": str(scene),
                "scene_sha256": j004.sha256_file(scene),
                "j002_manifest": manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "l001-source-provenance.json").write_text(
        json.dumps(
            {
                "git_commit": git("rev-parse", "HEAD"),
                "l001_config_blob": EXPECTED_CONFIG_BLOB_SHA,
                "l001_frozen_blobs": EXPECTED_SOURCE_BLOBS,
                "j004_source_tree": git(
                    "rev-parse",
                    "HEAD:src/research/lane_j_topology_backend_alternatives",
                ),
                "j004_formal_shader_tree": git(
                    "rev-parse",
                    "HEAD:shaders/research/lane_j_topology_backend_alternatives/formal_runtime",
                ),
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
        (root / "l001-vulkaninfo-summary.txt").write_text(
            proc.stdout,
            encoding="utf-8",
        )

    profiles = [str(item["name"]) for item in config["j002"]["profiles"]]
    environments = [str(item["id"]) for item in config["environments"]]
    tracks = list(config["controls"].keys())

    validation_rows: list[dict[str, object]] = []
    validation_devices: list[dict[str, object]] = []
    progress: dict[str, object] = {
        "state": "validating",
        "git_commit": git("rev-parse", "HEAD"),
        "plan_version": config["plan_version"],
        "completed_validations": [],
        "completed_processes": [],
    }

    def save_progress() -> None:
        (root / "l001-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    save_progress()
    try:
        for environment in environments:
            for profile in profiles:
                profile_dir = materialized_root / profile
                for track in tracks:
                    progress["current"] = {
                        "phase": "validation",
                        "environment": environment,
                        "profile": profile,
                        "track": track,
                    }
                    save_progress()
                    validation, device = run_validation(
                        executable,
                        root,
                        config,
                        environment,
                        profile,
                        track,
                        profile_dir,
                        producer,
                        scene,
                    )
                    validation_rows.append({
                        "environment": environment,
                        "profile": profile,
                        "track": track,
                        "variant": config["controls"][track],
                        "passed": validation["passed"],
                        "resolved_output_identity":
                            validation["resolved_output_identity"],
                        "allocation_lifetime_consistent":
                            validation["allocation_lifetime"]["consistent"],
                        "role_a_resolved_digest":
                            validation["roles"]["A"]["resolved_digest"],
                        "role_b_resolved_digest":
                            validation["roles"]["B"]["resolved_digest"],
                    })
                    validation_devices.append(device)
                    progress["completed_validations"].append(
                        f"{environment}/{profile}/{track}"
                    )
                    save_progress()

        if not same_device(validation_devices):
            raise RuntimeError(
                "L001 validation device/driver/API provenance changed"
            )

        progress["state"] = "timing"
        save_progress()
        all_rows: list[dict[str, object]] = []
        observations: list[dict[str, object]] = []
        timing_devices: list[dict[str, object]] = []

        for profile in profiles:
            profile_dir = materialized_root / profile
            for track in tracks:
                environment_orders = config["timing"]["environment_order_by_block"]
                if len(environment_orders) != int(
                    config["timing"]["fresh_process_blocks"]
                ):
                    raise RuntimeError(
                        "L001 environment-order block count drifted"
                    )
                for block, environment_order in enumerate(environment_orders):
                    if (
                        set(environment_order) != set(environments)
                        or len(environment_order) != len(environments)
                    ):
                        raise RuntimeError(
                            f"L001 environment order drifted at block {block}"
                        )
                    for environment in environment_order:
                        process_id = (
                            f"{environment}-{profile}-{track}-b{block:02d}"
                        )
                        progress["current"] = {
                            "phase": "timing",
                            "environment": environment,
                            "profile": profile,
                            "track": track,
                            "block": block,
                        }
                        save_progress()
                        rows, obs, device = run_timing_process(
                            executable,
                            root,
                            config,
                            environment,
                            profile,
                            track,
                            block,
                            profile_dir,
                            producer,
                            scene,
                        )
                        all_rows.extend(rows)
                        observations.append(obs)
                        timing_devices.append(device)
                        progress["completed_processes"].append(process_id)
                        save_progress()

    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    devices = validation_devices + timing_devices
    if not same_device(devices):
        raise RuntimeError(
            "L001 device/driver/API provenance changed during campaign"
        )

    process_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in all_rows:
        process_groups[str(row["process_id"])].append(row)

    process_rows: list[dict[str, object]] = []
    for process_id, rows in process_groups.items():
        summary = analysis.summarize_process(rows)
        first = rows[0]
        summary.update({
            "environment": first["environment"],
            "profile": first["profile"],
            "track": first["track"],
            "comparison": "control",
            "block": first["block"],
            "process_id": process_id,
        })
        process_rows.append(summary)

    accepted = analysis.summarize_l001(process_rows, config)

    write_csv(root / "l001-validation-summary.csv", validation_rows)
    write_csv(root / "l001-raw.csv", all_rows)
    write_csv(
        root / "l001-process-summary.csv",
        [flatten_process(row) for row in process_rows],
    )
    (root / "l001-host-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "l001-devices.json").write_text(
        json.dumps(devices, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "schema_version": 1,
        "plan_version": config["plan_version"],
        "git_commit": git("rev-parse", "HEAD"),
        "branch": EXPECTED_BRANCH,
        "target_gpu": config["target_gpu"],
        "all_samples_retained": True,
        "sample_exclusion": "none",
        "instability_rerun_budget": 0,
        "completed_campaign_rerun_budget": 0,
        "device_provenance_consistent": True,
        "architecture_ranking_performed": False,
        "timed_memory_decision_use": "diagnostic-only",
        "validation_count": len(validation_rows),
        "timing_process_count": len(process_rows),
        "result": accepted,
    }
    (root / "l001-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    progress["state"] = "complete"
    progress.pop("current", None)
    save_progress()
    print(f"L001 artifacts: {root}")
    print(json.dumps(accepted, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
