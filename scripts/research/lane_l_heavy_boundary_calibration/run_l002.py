#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import l002_analysis as analysis
import run_l001 as l001


ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-l-heavy-boundary-calibration"
CONFIG = (
    ROOT
    / "research/lanes/lane-l-heavy-boundary-calibration/experiments"
    / "005-l002-config.json"
)
L001_CONFIG = (
    ROOT
    / "research/lanes/lane-l-heavy-boundary-calibration/experiments"
    / "002-l001-config.json"
)
EXPECTED_CONFIG_BLOB_SHA = "b7b20a53de965f198ac5b117645b07626204bbab"
EXPECTED_SOURCE_BLOBS = {
    "scripts/research/lane_l_heavy_boundary_calibration/l002_analysis.py":
        "a4ed4c540ca7588c35491470e437b96696daf113",
    "scripts/research/lane_l_heavy_boundary_calibration/test_l002_analysis.py":
        "c81220db8f8dc01a50567762a21322de051d566a",
    "scripts/research/lane_l_heavy_boundary_calibration/test_l002_protocol.py":
        "1c846c80bdf3ebcb535a3dd4a729efad61d0db77",
    "scripts/research/lane_l_heavy_boundary_calibration/run_l001.py":
        "f5990abdb4225a469c7c48e807655a3d81647b1e",
}
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-l-heavy-boundary-calibration"
    / "002-heavy-boundary-detectable-floor"
)


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


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def flatten_control_process(row: dict[str, object]) -> dict[str, object]:
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
            "L002 frozen config changed before target timing: "
            f"{actual_config} != {EXPECTED_CONFIG_BLOB_SHA}"
        )

    for path, expected in EXPECTED_SOURCE_BLOBS.items():
        actual = git("hash-object", path)
        if actual != expected:
            raise RuntimeError(
                f"L002 source drift for {path}: {actual} != {expected}"
            )

    l001_config = json.loads(L001_CONFIG.read_text(encoding="utf-8"))
    l001.verify_sources(l001_config)

    if config["l001_import"]["outcome"] != "measurement-limited":
        raise RuntimeError("L002 entry requires frozen L001 measurement-limited outcome")
    if config["l001_import"]["entry_condition_satisfied"] is not True:
        raise RuntimeError("L002 entry condition must remain explicitly satisfied")


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
        raise RuntimeError(f"L002 must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("L002 requires a clean worktree")

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config.get("plan_version") != "lane-l-l002-v1":
        raise RuntimeError("L002 requires frozen plan lane-l-l002-v1")
    if config.get("architecture_ranking_allowed") is not False:
        raise RuntimeError("L002 architecture ranking must remain forbidden")
    verify_sources(config)

    timing = config["timing"]
    if bool(timing["accepted_timing_validation"]):
        raise RuntimeError("accepted L002 timing must disable validation layers")
    if timing["sample_exclusion"] != "forbidden":
        raise RuntimeError("L002 sample exclusion policy drifted")
    if int(timing["instability_rerun_budget"]) != 0:
        raise RuntimeError("L002 instability rerun budget must be zero")
    if int(timing["completed_campaign_rerun_budget"]) != 0:
        raise RuntimeError("L002 completed campaign rerun budget must be zero")
    if (
        int(timing["warmup_pairs"]) != 4
        or int(timing["measured_pairs"]) != 12
        or int(timing["fresh_process_blocks"]) != 8
    ):
        raise RuntimeError("L002 paired sample shape drifted")
    if int(config["recurring_boundary"]["batch_transitions"]) != 16:
        raise RuntimeError("L002 recurring boundary drifted")
    if config["axis_roles"]["primary_performance"] != "gpu_timestamp":
        raise RuntimeError("L002 primary axis drifted")

    synthetic = config["synthetic_effect_calibration"]
    factor_shape = [
        (str(item["id"]), int(item["percent"]), float(item["factor"]))
        for item in synthetic["factors"]
    ]
    if factor_shape != [
        ("plus20", 20, 1.20),
        ("plus10", 10, 1.10),
        ("plus5", 5, 1.05),
    ]:
        raise RuntimeError("L002 synthetic effect ladder drifted")
    if synthetic["injection_domain"] != "analysis-only-gpu-timestamp-b-role":
        raise RuntimeError("L002 injection domain drifted")
    if bool(synthetic["measured_gpu_work_modified"]):
        raise RuntimeError("L002 must not modify measured GPU work")

    gate = config["detection_gate"]
    if float(gate["minimum_positive_pair_fraction"]) != 0.75:
        raise RuntimeError("L002 minimum positive-pair fraction drifted")
    if gate["contiguous_order"] != ["plus20", "plus10", "plus5"]:
        raise RuntimeError("L002 contiguous order drifted")
    if not bool(
        gate["control_noise_envelope"][
            "injected_factor_must_exceed_envelope_strictly"
        ]
    ):
        raise RuntimeError("L002 factor/noise relation must remain strict")

    completed = sorted(CAMPAIGN_ROOT.glob("*/l002-summary.json"))
    if completed:
        joined = ", ".join(
            str(path.parent.relative_to(ROOT)) for path in completed
        )
        raise RuntimeError(
            "L002 completed-campaign rerun budget is zero; existing summary: "
            + joined
        )

    j004_config = json.loads(l001.J004_CONFIG.read_text(encoding="utf-8"))
    materialized_root, manifest, producer, scene = l001.j004.load_materialized(
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

    (root / "l002-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "l002-input-provenance.json").write_text(
        json.dumps(
            {
                "materialized_root": str(materialized_root),
                "manifest_sha256": l001.j004.sha256_file(
                    materialized_root / "j002-materialized-manifest.json"
                ),
                "producer_stream": str(producer),
                "producer_stream_sha256": l001.j004.sha256_file(producer),
                "scene": str(scene),
                "scene_sha256": l001.j004.sha256_file(scene),
                "j002_manifest": manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "l002-source-provenance.json").write_text(
        json.dumps(
            {
                "git_commit": git("rev-parse", "HEAD"),
                "l002_config_blob": EXPECTED_CONFIG_BLOB_SHA,
                "l002_frozen_blobs": EXPECTED_SOURCE_BLOBS,
                "l001_config_blob": git(
                    "hash-object", str(L001_CONFIG.relative_to(ROOT))
                ),
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
        (root / "l002-vulkaninfo-summary.txt").write_text(
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
        (root / "l002-progress.json").write_text(
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
                    validation, device = l001.run_validation(
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
                    validation_rows.append(
                        {
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
                        }
                    )
                    validation_devices.append(device)
                    progress["completed_validations"].append(
                        f"{environment}/{profile}/{track}"
                    )
                    save_progress()

        if not l001.same_device(validation_devices):
            raise RuntimeError(
                "L002 validation device/driver/API provenance changed"
            )

        progress["state"] = "timing"
        save_progress()
        all_rows: list[dict[str, object]] = []
        observations: list[dict[str, object]] = []
        timing_devices: list[dict[str, object]] = []

        for profile in profiles:
            profile_dir = materialized_root / profile
            for track in tracks:
                environment_orders = timing["environment_order_by_block"]
                if len(environment_orders) != int(timing["fresh_process_blocks"]):
                    raise RuntimeError(
                        "L002 environment-order block count drifted"
                    )
                for block, environment_order in enumerate(environment_orders):
                    if (
                        set(environment_order) != set(environments)
                        or len(environment_order) != len(environments)
                    ):
                        raise RuntimeError(
                            f"L002 environment order drifted at block {block}"
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
                        rows, observation, device = l001.run_timing_process(
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
                        observations.append(observation)
                        timing_devices.append(device)
                        progress["completed_processes"].append(process_id)
                        save_progress()
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    devices = validation_devices + timing_devices
    if not l001.same_device(devices):
        raise RuntimeError(
            "L002 device/driver/API provenance changed during campaign"
        )

    process_groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in all_rows:
        process_groups[str(row["process_id"])].append(row)

    process_rows: list[dict[str, object]] = []
    for process_id, rows in process_groups.items():
        process_summary = analysis.summarize_control_process(rows)
        first = rows[0]
        process_summary.update(
            {
                "environment": first["environment"],
                "profile": first["profile"],
                "track": first["track"],
                "comparison": "control",
                "block": first["block"],
                "process_id": process_id,
            }
        )
        process_rows.append(process_summary)

    result = analysis.summarize_l002(all_rows, config)
    synthetic_rows = result.pop("synthetic_process_rows")

    write_csv(root / "l002-validation-summary.csv", validation_rows)
    write_csv(root / "l002-raw.csv", all_rows)
    write_csv(
        root / "l002-process-summary.csv",
        [flatten_control_process(row) for row in process_rows],
    )
    write_csv(root / "l002-synthetic-process-summary.csv", synthetic_rows)
    (root / "l002-host-observations.json").write_text(
        json.dumps(observations, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "l002-devices.json").write_text(
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
        "synthetic_injection_is_analysis_only": True,
        "validation_count": len(validation_rows),
        "timing_process_count": len(process_rows),
        "raw_row_count": len(all_rows),
        "result": result,
    }
    (root / "l002-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    progress["state"] = "complete"
    progress.pop("current", None)
    save_progress()
    print(f"L002 artifacts: {root}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
