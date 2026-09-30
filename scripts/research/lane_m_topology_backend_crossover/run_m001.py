#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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

SCRIPT_DIR = Path(__file__).resolve().parent
J_DIR = SCRIPT_DIR.parent / "lane_j_topology_backend_alternatives"
sys.path.insert(0, str(J_DIR))

import run_j004 as j004  # noqa: E402
import m001_analysis as analysis  # noqa: E402


ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-m-topology-backend-crossover"
CONFIG = (
    ROOT
    / "research/lanes/lane-m-topology-backend-crossover/experiments"
    / "001-topology-backend-crossover-config.json"
)
EXPECTED_CONFIG_BLOB_SHA = "b1f2164df9ad2c9e154b328cfe332196cfd909f8"
EXPECTED_J_SOURCE_TREE_SHA = "757da6c85c697a42cbebe918f96cf59008772805"
EXPECTED_J_FORMAL_SHADER_TREE_SHA = "83e6f0f5286e7edb14b15a3e722dca379e126ce5"
EXPECTED_CORE_BLOBS = {
    "src/research/lane_m_topology_backend_crossover/m001_contract.hpp":
        "223ada4919082cdc8231c0bd4bdf4c5f4b0dff88",
    "src/research/lane_m_topology_backend_crossover/m001_contract.cpp":
        "8ac4ca846d3c670125160e7c6fcbf0ef16d0f2c5",
    "src/research/lane_m_topology_backend_crossover/m001_clustered_adapter.hpp":
        "df9facbfb4e36ba01fc42b1040c545e3b89b5fa6",
    "src/research/lane_m_topology_backend_crossover/m001_clustered_adapter.cpp":
        "3d3dd5e667af7f17521d77ea20751b0146a0bcac",
    "src/research/lane_m_topology_backend_crossover/m001_contract_test.cpp":
        "c28ad6b6894263e79c574cea56da2ea044a9ff6f",
    "src/research/lane_m_topology_backend_crossover/CMakeLists.txt":
        "9835f0f84819e217983d2b88efbd1bf4fb633fda",
    "shaders/research/lane_m_topology_backend_crossover/"
    "m001_clustered_traversal.comp.glsl":
        "2e71427f13ebb8fb1cc6a5a7295dd95dc552b647",
    "scripts/research/lane_m_topology_backend_crossover/m001_analysis.py":
        "45c5bfb24afaa26f2c8d19177bf97e996cdb46fc",
    "scripts/research/lane_m_topology_backend_crossover/test_m001_analysis.py":
        "242ed088a6b172126c9da89ea12458fa407dd9a7",
    "scripts/research/lane_m_topology_backend_crossover/test_m001_protocol.py":
        "d66c8d8b57da228be79469eb941af6e365c20cb2",
    "CMakeLists.txt":
        "6ebf86f9c882d9eb2d5d65b6e5649df7485df396",
    "scripts/research/run_experiment.py":
        "ae891d42fe3ef804256f87d1d44988d3515ef7fe",
}
CAMPAIGN_ROOT = (
    ROOT
    / "out/research/lane-m-topology-backend-crossover"
    / "001-topology-backend-crossover"
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def source_fingerprint() -> dict[str, object]:
    return {
        "config_blob": git("hash-object", str(CONFIG.relative_to(ROOT))),
        "j_source_tree": git(
            "rev-parse",
            "HEAD:src/research/lane_j_topology_backend_alternatives",
        ),
        "j_formal_shader_tree": git(
            "rev-parse",
            "HEAD:shaders/research/lane_j_topology_backend_alternatives/formal_runtime",
        ),
        "core_blobs": {
            path: git("hash-object", path)
            for path in EXPECTED_CORE_BLOBS
        },
    }


def verify_frozen_sources() -> None:
    actual = source_fingerprint()
    if actual["config_blob"] != EXPECTED_CONFIG_BLOB_SHA:
        raise RuntimeError("Lane M frozen config drifted")
    if actual["j_source_tree"] != EXPECTED_J_SOURCE_TREE_SHA:
        raise RuntimeError("Lane M qualified J/E/G source tree drifted")
    if actual["j_formal_shader_tree"] != EXPECTED_J_FORMAL_SHADER_TREE_SHA:
        raise RuntimeError("Lane M qualified formal shader tree drifted")
    for path, expected in EXPECTED_CORE_BLOBS.items():
        value = actual["core_blobs"][path]
        if value != expected:
            raise RuntimeError(
                f"Lane M frozen source drift for {path}: {value} != {expected}"
            )


def validate_config(config: dict[str, object]) -> None:
    if config["plan_version"] != "lane-m-m001-v1":
        raise RuntimeError("unexpected Lane M plan version")
    if config["accepted_target_timing_started"] is not False:
        raise RuntimeError("prospective freeze must precede accepted timing")
    if float(config["imported_capability"]["demonstrated_effect_floor"]) != 0.20:
        raise RuntimeError("Lane M must use Lane L's 20% demonstrated floor")
    gate = config["performance_gate"]
    if (
        float(gate["threshold"]) != 0.20
        or float(gate["promotion_ratio_max"]) != 0.80
        or float(gate["regression_ratio_min"]) != 1.20
        or float(gate["minimum_directional_pair_fraction"]) != 0.75
    ):
        raise RuntimeError("Lane M performance gate drifted")
    memory = config["memory_gate"]
    if (
        float(memory["persistent_ratio_max"]) != 1.25
        or float(memory["true_peak_ratio_max"]) != 1.25
        or memory["allocation_lifetime_accounting_complete"] is not True
    ):
        raise RuntimeError("Lane M memory hard guard drifted")
    timing = config["timing"]
    if (
        int(timing["warmup_pairs"]) != 4
        or int(timing["measured_pairs"]) != 12
        or int(timing["fresh_process_blocks"]) != 8
        or int(config["recurrent_boundary"]["batch_transitions"]) != 16
    ):
        raise RuntimeError("Lane M Lane-L sample shape drifted")
    if (
        timing["sample_exclusion"] != "forbidden"
        or int(timing["instability_rerun_budget"]) != 0
        or int(timing["completed_campaign_rerun_budget"]) != 0
        or bool(timing["accepted_timing_validation"])
    ):
        raise RuntimeError("Lane M exclusion/rerun/validation policy drifted")
    if int(config["j002"]["validation_ray_prefix_count"]) != 0:
        raise RuntimeError("Lane M validation must replay all frozen A001 rays")


def scenario_map(config: dict[str, object]) -> dict[str, dict[str, object]]:
    return {
        str(item["id"]): item
        for item in config["scenarios"]
    }


def expected_variant(
    config: dict[str, object],
    track: str,
    comparison: str,
    role: str,
) -> str:
    incumbent = str(config["tracks"][track]["incumbent"])
    lbvh = str(config["candidates"]["lbvh"])
    clustered = str(config["candidates"]["clustered"])
    if comparison == "control":
        return incumbent
    if comparison == "lbvh":
        return incumbent if role == "A" else lbvh
    if comparison == "clustered":
        return incumbent if role == "A" else clustered
    if comparison == "lbvh-control":
        return lbvh
    if comparison == "clustered-vs-lbvh":
        return lbvh if role == "A" else clustered
    raise RuntimeError(f"unknown Lane M comparison: {comparison}")


def run_validation(
    executable: Path,
    root: Path,
    config: dict[str, object],
    scenario: str,
    track: str,
    variant: str,
    profile_dir: Path,
    producer: Path,
    scene: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    process_id = f"validation-{scenario}-{track}-{variant}"
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
        "--scenario",
        scenario,
        "--track",
        track,
        "--comparison",
        "control",
        "--validation-only",
        "--validation-variant",
        variant,
        "--validation-rays",
        "0",
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
    if proc.returncode != 0:
        raise RuntimeError(
            f"Lane M validation failed: {scenario}/{track}/{variant}"
        )

    validation = json.loads(
        (process_root / "j004-validation.json").read_text(encoding="utf-8")
    )
    if validation.get("passed") is not True:
        raise RuntimeError(
            f"Lane M validation artifact rejected: {scenario}/{track}/{variant}"
        )
    for field in config["correctness"]["required_zero_fields"]:
        if int(validation.get(field, -1)) != 0:
            raise RuntimeError(
                f"{scenario}/{track}/{variant}: {field} is non-zero or missing"
            )
    for field in (
        "workload_identity_match",
        "geometry_input_identity_match",
        "allocation_lifetime_accounting_complete",
    ):
        if validation.get(field) is not True:
            raise RuntimeError(
                f"{scenario}/{track}/{variant}: {field} did not pass"
            )

    spec = scenario_map(config)[scenario]
    expected_updates = 8 if bool(spec["topology_mutation_required"]) else 0
    if (
        int(validation.get("topology_mutation_count", -1)) != expected_updates
        or int(validation.get("backend_rebuild_count", -1)) != expected_updates
    ):
        raise RuntimeError(
            f"{scenario}/{track}/{variant}: mutation/rebuild evidence mismatch"
        )
    if int(validation["allocation_count"]) != int(validation["free_count"]):
        raise RuntimeError(
            f"{scenario}/{track}/{variant}: allocation/free lifetime mismatch"
        )
    if (
        int(validation["live_allocations_before"])
        != int(validation["live_allocations_after"])
    ):
        raise RuntimeError(
            f"{scenario}/{track}/{variant}: live allocation count changed"
        )

    device = json.loads(
        (process_root / "j004-device.json").read_text(encoding="utf-8")
    )
    return validation, device


def run_timing_process(
    executable: Path,
    root: Path,
    config: dict[str, object],
    scenario: str,
    track: str,
    comparison: str,
    block: int,
    profile_dir: Path,
    producer: Path,
    scene: Path,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    time.sleep(float(config["timing"]["settle_seconds"]))
    start_order = str(config["timing"]["start_order_by_block"][block])
    process_id = f"{scenario}-{track}-{comparison}-b{block:02d}"
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
        "--scenario",
        scenario,
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
        str(config["recurrent_boundary"]["batch_transitions"]),
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
    if proc.returncode != 0:
        raise RuntimeError(
            f"Lane M formal process failed: {process_id}; campaign invalid"
        )

    rows = read_csv(process_root / "j004-samples.csv")
    expected_rows = 2 * (
        int(config["timing"]["warmup_pairs"])
        + int(config["timing"]["measured_pairs"])
    )
    if len(rows) != expected_rows:
        raise RuntimeError(
            f"{process_id}: expected {expected_rows} rows, got {len(rows)}"
        )

    spec = scenario_map(config)[scenario]
    expected_updates = (
        int(config["recurrent_boundary"]["batch_transitions"])
        if bool(spec["topology_mutation_required"])
        else 0
    )
    enriched: list[dict[str, object]] = []
    for raw in rows:
        role = str(raw["role"])
        if role not in {"A", "B"}:
            raise RuntimeError(f"{process_id}: invalid role")
        if raw["variant"] != expected_variant(
            config, track, comparison, role
        ):
            raise RuntimeError(f"{process_id}: role/variant identity mismatch")
        for field in config["recurrent_boundary"]["required_boundary_fields"]:
            if field not in raw or raw[field] == "":
                raise RuntimeError(
                    f"{process_id}: missing boundary field {field}"
                )
            value = float(raw[field])
            if not math.isfinite(value) or value < 0:
                raise RuntimeError(
                    f"{process_id}: invalid boundary field {field}"
                )
        if float(raw["gpu_us"]) <= 0 or float(raw["complete_wall_us"]) <= 0:
            raise RuntimeError(f"{process_id}: non-positive complete timing")
        if int(raw["storage_failures"]) != 0:
            raise RuntimeError(f"{process_id}: storage failure")
        if (
            int(raw["topology_mutation_count"]) != expected_updates
            or int(raw["backend_rebuild_count"]) != expected_updates
        ):
            raise RuntimeError(f"{process_id}: sample mutation identity mismatch")
        if int(raw["allocation_lifetime_complete"]) != 1:
            raise RuntimeError(f"{process_id}: incomplete allocation lifetime")
        if int(raw["allocation_count"]) != int(raw["free_count"]):
            raise RuntimeError(f"{process_id}: unbalanced allocation/free count")
        if (
            int(raw["live_allocations_before"])
            != int(raw["live_allocations_after"])
        ):
            raise RuntimeError(f"{process_id}: live allocation count changed")
        if int(raw["persistent_bytes"]) <= 0:
            raise RuntimeError(f"{process_id}: zero persistent memory")
        if int(raw["true_peak_resident_bytes"]) <= 0:
            raise RuntimeError(f"{process_id}: zero true peak")
        if (
            int(raw["old_new_overlap_bytes"])
            > int(raw["true_peak_resident_bytes"])
        ):
            raise RuntimeError(f"{process_id}: overlap exceeds true lifetime peak")

        row: dict[str, object] = dict(raw)
        row.update({
            "scenario": scenario,
            "track": track,
            "comparison": comparison,
            "block": block,
            "process_id": process_id,
        })
        enriched.append(row)

    device = json.loads(
        (process_root / "j004-device.json").read_text(encoding="utf-8")
    )
    return enriched, device


def artifact_root(phase: str) -> Path:
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return CAMPAIGN_ROOT / f"{phase}-{stamp}"


def find_validation_summary() -> Path:
    summaries = sorted(CAMPAIGN_ROOT.glob("*/m001-validation-summary.json"))
    if len(summaries) != 1:
        raise RuntimeError(
            "Lane M formal timing requires exactly one completed frozen "
            f"validation summary, found {len(summaries)}"
        )
    return summaries[0]


def run_validation_phase(
    executable: Path,
    config: dict[str, object],
) -> int:
    if list(CAMPAIGN_ROOT.glob("*/m001-validation-summary.json")):
        raise RuntimeError("Lane M completed validation already exists")

    materialized, manifest, producer, scene = j004.load_materialized(config)
    root = artifact_root("validation")
    root.mkdir(
        parents=True,
        exist_ok=bool(os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")),
    )
    rows: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []

    for scenario, spec in scenario_map(config).items():
        profile_dir = materialized / str(spec["profile"])
        resolved: list[int] = []
        for track in ("primary", "software"):
            for variant in ("control", "lbvh", "clustered"):
                validation, device = run_validation(
                    executable,
                    root,
                    config,
                    scenario,
                    track,
                    variant,
                    profile_dir,
                    producer,
                    scene,
                )
                rows.append({
                    "scenario": scenario,
                    "track": track,
                    "variant": variant,
                    **validation,
                })
                resolved.append(int(validation["resolved_digest"]))
                devices.append(device)
        if len(set(resolved)) != 1:
            raise RuntimeError(
                f"{scenario}: resolved-output identity differs across variants"
            )

    if not j004.same_device(devices):
        raise RuntimeError(
            "Lane M validation device/driver/API/timestamp provenance changed"
        )

    summary = {
        "schema_version": 1,
        "plan_version": config["plan_version"],
        "git_commit": git("rev-parse", "HEAD"),
        "source_fingerprint": source_fingerprint(),
        "input_manifest_sha256": j004.sha256_file(
            materialized / "j002-materialized-manifest.json"
        ),
        "producer_stream_sha256": j004.sha256_file(producer),
        "scene_sha256": j004.sha256_file(scene),
        "device_provenance": devices[0],
        "device_driver_api_timestamp_provenance_match": True,
        "resolved_output_identity_match": True,
        "geometry_input_identity_match": True,
        "workload_identity_match": True,
        "passed": True,
        "rows": rows,
        "j002_manifest": manifest,
    }
    (root / "m001-validation-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Lane M validation artifacts: {root}")
    return 0


def formal_attempt_exists() -> bool:
    for path in CAMPAIGN_ROOT.glob("*/m001-progress.json"):
        try:
            progress = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if progress.get("phase_mode") == "formal":
            return True
    return False


def build_outcomes(
    first: dict[str, object],
    direct: dict[str, object],
) -> dict[str, object]:
    outcomes: dict[str, object] = {}
    for scenario, by_track in first["results"].items():
        if scenario == "stable-no-change-guard":
            continue
        outcomes[scenario] = {}
        for track, record in by_track.items():
            eligible = [
                name
                for name, value in record["candidates"].items()
                if bool(value.get("promotion_eligible"))
            ]
            if not eligible:
                decision = "Lane E incumbent retained"
            elif len(eligible) == 1:
                decision = f"{eligible[0]} promoted"
            else:
                direct_record = direct.get("results", {}).get(
                    scenario, {}
                ).get(track)
                if direct_record is None:
                    raise RuntimeError(
                        "direct crossover evidence missing after dual promotion"
                    )
                classification = direct_record["performance"]["classification"]
                if classification == ">=20% detected improvement":
                    decision = "clustered promoted over LBVH"
                elif classification == "detected >=20% regression":
                    decision = "LBVH promoted over clustered"
                else:
                    decision = (
                        "LBVH and clustered both promoted vs incumbent; "
                        "direct difference <20% / measurement-limited; do not rank"
                    )
            outcomes[scenario][track] = {
                "eligible_candidates": eligible,
                "decision": decision,
            }
    return outcomes


def run_formal_phase(
    executable: Path,
    config: dict[str, object],
) -> int:
    if list(CAMPAIGN_ROOT.glob("*/m001-summary.json")):
        raise RuntimeError(
            "Lane M completed-campaign rerun budget is zero"
        )
    if formal_attempt_exists():
        raise RuntimeError(
            "Lane M formal attempt already exists; interruption/rerun is "
            "fail-closed under the frozen zero-rerun policy"
        )

    validation_path = find_validation_summary()
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if validation.get("passed") is not True:
        raise RuntimeError("Lane M frozen validation did not pass")
    if validation.get("git_commit") != git("rev-parse", "HEAD"):
        raise RuntimeError(
            "Lane M source changed after validation; accepted timing forbidden"
        )
    if validation.get("source_fingerprint") != source_fingerprint():
        raise RuntimeError(
            "Lane M frozen source fingerprint differs from validation"
        )

    materialized, manifest, producer, scene = j004.load_materialized(config)
    root = artifact_root("formal")
    root.mkdir(
        parents=True,
        exist_ok=bool(os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")),
    )
    progress: dict[str, object] = {
        "phase_mode": "formal",
        "state": "first-stage",
        "git_commit": git("rev-parse", "HEAD"),
        "completed_processes": [],
    }

    def save_progress() -> None:
        (root / "m001-progress.json").write_text(
            json.dumps(progress, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    save_progress()
    raw: list[dict[str, object]] = []
    devices: list[dict[str, object]] = []
    try:
        scenarios = scenario_map(config)
        for scenario, spec in scenarios.items():
            profile_dir = materialized / str(spec["profile"])
            for track in ("primary", "software"):
                orders = config["timing"]["comparison_order_by_block"]
                for block, order in enumerate(orders):
                    for comparison in order:
                        progress["current"] = {
                            "stage": "first",
                            "scenario": scenario,
                            "track": track,
                            "comparison": comparison,
                            "block": block,
                        }
                        save_progress()
                        rows, device = run_timing_process(
                            executable,
                            root,
                            config,
                            scenario,
                            track,
                            comparison,
                            block,
                            profile_dir,
                            producer,
                            scene,
                        )
                        raw.extend(rows)
                        devices.append(device)
                        progress["completed_processes"].append(
                            f"{scenario}/{track}/{comparison}/b{block:02d}"
                        )
                        save_progress()

        first = analysis.summarize_first_stage(raw)

        direct_pairs: list[tuple[str, str]] = []
        for scenario, by_track in first["results"].items():
            if scenario == "stable-no-change-guard":
                continue
            for track, record in by_track.items():
                candidates = record["candidates"]
                if (
                    bool(candidates["lbvh"].get("promotion_eligible"))
                    and bool(candidates["clustered"].get("promotion_eligible"))
                ):
                    direct_pairs.append((scenario, track))

        direct_raw: list[dict[str, object]] = []
        progress["state"] = "conditional-direct"
        save_progress()
        direct_orders = config["conditional_direct_crossover"][
            "comparison_order_by_block"
        ]
        for scenario, track in direct_pairs:
            spec = scenarios[scenario]
            profile_dir = materialized / str(spec["profile"])
            for block, order in enumerate(direct_orders):
                for comparison in order:
                    progress["current"] = {
                        "stage": "direct",
                        "scenario": scenario,
                        "track": track,
                        "comparison": comparison,
                        "block": block,
                    }
                    save_progress()
                    rows, device = run_timing_process(
                        executable,
                        root,
                        config,
                        scenario,
                        track,
                        comparison,
                        block,
                        profile_dir,
                        producer,
                        scene,
                    )
                    direct_raw.extend(rows)
                    devices.append(device)
                    progress["completed_processes"].append(
                        f"{scenario}/{track}/{comparison}/b{block:02d}"
                    )
                    save_progress()

        direct = (
            analysis.summarize_direct_stage(direct_raw)
            if direct_raw
            else {"process_rows": [], "results": {}}
        )
    except BaseException:
        progress["state"] = "invalid-or-interrupted"
        save_progress()
        raise

    validation_device = validation["device_provenance"]
    if not j004.same_device([validation_device, *devices]):
        progress["state"] = "invalid-provenance"
        save_progress()
        raise RuntimeError(
            "Lane M device/driver/API/timestamp provenance changed"
        )

    outcomes = build_outcomes(first, direct)
    all_raw = raw + direct_raw
    write_csv(root / "m001-raw.csv", all_raw)
    write_csv(
        root / "m001-process-summary.csv",
        first["process_rows"] + direct["process_rows"],
    )
    (root / "m001-input-provenance.json").write_text(
        json.dumps(
            {
                "validation_summary": str(validation_path.relative_to(ROOT)),
                "materialized_root": str(materialized),
                "manifest_sha256": j004.sha256_file(
                    materialized / "j002-materialized-manifest.json"
                ),
                "producer_stream_sha256": j004.sha256_file(producer),
                "scene_sha256": j004.sha256_file(scene),
                "j002_manifest": manifest,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": 1,
        "plan_version": config["plan_version"],
        "git_commit": git("rev-parse", "HEAD"),
        "source_fingerprint": source_fingerprint(),
        "all_samples_retained": True,
        "sample_exclusion": "none",
        "instability_rerun_budget": 0,
        "completed_campaign_rerun_budget": 0,
        "device_provenance_consistent": True,
        "primary_axis": "gpu_timestamp",
        "cpu_wall_role": "diagnostic-health-provenance-only",
        "first_stage": first["results"],
        "conditional_direct": direct["results"],
        "outcomes": outcomes,
        "architecture_ranking_below_20_percent_performed": False,
    }
    (root / "m001-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    progress["state"] = "complete"
    progress.pop("current", None)
    save_progress()
    print(f"Lane M formal artifacts: {root}")
    print(json.dumps(outcomes, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("validation", "formal"),
        required=True,
    )
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"),
    )
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"Lane M must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("Lane M execution requires a clean worktree")

    verify_frozen_sources()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    validate_config(config)

    executable = args.build_dir / "phos-lane-m-m001-formal-process"
    if not executable.is_file():
        raise RuntimeError(f"missing Lane M executable: {executable}")

    if args.phase == "validation":
        return run_validation_phase(executable, config)
    return run_formal_phase(executable, config)


if __name__ == "__main__":
    raise SystemExit(main())
