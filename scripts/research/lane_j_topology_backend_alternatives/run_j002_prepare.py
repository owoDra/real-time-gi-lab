#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import j002_contract as contract

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-j-topology-backend-alternatives"
CONFIG = (
    ROOT
    / "research/lanes/lane-j-topology-backend-alternatives/experiments"
    / "002-deterministic-topology-contract.json"
)


def git(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip())
    return process.stdout.strip()


def build_manifest(
    cfg: dict[str, Any],
    producer_stream: bytes | None = None,
) -> dict[str, Any]:
    factors = [
        float(value)
        for value in cfg["primitive_count_factors"]
    ]
    master_seed = int(cfg["master_topology_seed"])
    profiles: list[dict[str, Any]] = []

    for index, profile in enumerate(cfg["profiles"]):
        seed = contract.profile_seed(master_seed, index)
        steps = contract.topology_sequence(
            int(profile["base_primitive_count"]),
            factors,
            seed,
            float(profile["replacement_fraction"]),
            str(profile["locality"]),
        )
        digest = contract.topology_digest(
            str(profile["name"]),
            steps,
        )
        expected = profile.get("expected_topology_digest")
        if expected is not None and str(expected) != digest:
            raise ValueError(
                "J002 topology digest drift for "
                f"{profile['name']}: expected {expected}, got {digest}"
            )
        profiles.append({
            "name": profile["name"],
            "base_primitive_count": profile["base_primitive_count"],
            "replacement_fraction": profile["replacement_fraction"],
            "locality": profile["locality"],
            "profile_seed": seed,
            "topology_digest": digest,
            "steps": [
                {
                    "index": step.index,
                    "primitive_count": step.primitive_count,
                    "topology_seed": step.topology_seed,
                    "replacement_count": step.replacement_count,
                    "locality": step.locality,
                }
                for step in steps
            ],
        })

    producer = (
        None
        if producer_stream is None
        else contract.parse_lane_a_stream(producer_stream)
    )
    manifest = {
        "schema_version": 1,
        "plan_version": cfg["plan_version"],
        "formal_timing_decision": False,
        "producer_contract": cfg["producer_contract"],
        "hit_contract": cfg["hit_contract"],
        "storage_contract": cfg["storage_contract"],
        "changed_object_id": cfg["changed_object_id"],
        "immutable_owner_ids": cfg["immutable_owner_ids"],
        "candidate_set": cfg["candidate_set"],
        "required_boundary_fields": cfg["required_boundary_fields"],
        "required_correctness_zero_fields":
            cfg["required_correctness_zero_fields"],
        "producer_stream": producer,
        "producer_stream_ready": producer is not None,
        "profiles": profiles,
    }
    canonical = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
    )
    manifest["manifest_digest"] = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
    return manifest


def validate_candidate_record(
    record: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    if record.get("manifest_digest") != manifest["manifest_digest"]:
        raise ValueError(
            "candidate manifest digest differs from frozen J002 manifest"
        )
    for field in (
        "producer_contract",
        "hit_contract",
        "storage_contract",
    ):
        if record.get(field) != manifest[field]:
            raise ValueError(f"{field} mismatch")

    profile_name = str(record.get("profile"))
    profiles = {
        str(profile["name"]): profile
        for profile in manifest["profiles"]
    }
    if profile_name not in profiles:
        raise ValueError(f"unknown J002 profile: {profile_name}")
    profile = profiles[profile_name]
    if record.get("topology_digest") != profile["topology_digest"]:
        raise ValueError(
            "candidate topology digest differs from frozen profile"
        )

    snapshots = record.get("snapshots")
    if not isinstance(snapshots, list):
        raise TypeError("snapshots must be a list")
    contract.validate_transition_identity(snapshots)
    expected_counts = [
        int(step["primitive_count"])
        for step in profile["steps"]
    ]
    observed_counts = [
        int(step["primitive_count"])
        for step in snapshots
    ]
    if observed_counts != expected_counts:
        raise ValueError(
            "candidate primitive-count sequence differs from frozen profile"
        )

    contract.validate_boundary_record(
        record,
        [
            str(field)
            for field in manifest["required_boundary_fields"]
        ],
    )

    correctness = record.get("correctness")
    if (
        not isinstance(correctness, dict)
        or correctness.get("passed") is not True
    ):
        raise ValueError(
            "candidate correctness must PASS before timing evidence is usable"
        )
    for field in manifest["required_correctness_zero_fields"]:
        if int(correctness.get(str(field), -1)) != 0:
            raise ValueError(
                f"correctness field is nonzero: {field}"
            )

    events = record.get("mutation_events")
    if not isinstance(events, list):
        raise TypeError("mutation_events must be a list")
    contract.validate_object_local_mutations(
        [
            contract.MutationEvent(
                str(event["owner_id"]),
                str(event["operation"]),
            )
            for event in events
        ],
        changed_object_id=str(manifest["changed_object_id"]),
        immutable_owner_ids=[
            str(value)
            for value in manifest["immutable_owner_ids"]
        ],
    )

    raw_allocations = record.get("allocations")
    if not isinstance(raw_allocations, list):
        raise TypeError("allocations must be a list")
    allocations = [
        contract.AllocationLifetime(
            str(item["name"]),
            str(item["owner_id"]),
            int(item["bytes"]),
            int(item["birth_phase"]),
            int(item["death_phase"]),
            str(item.get("allocation_class", "persistent")),
        )
        for item in raw_allocations
    ]
    peak = contract.true_peak_resident_bytes(allocations)
    if peak != int(record["true_peak_resident_bytes"]):
        raise ValueError(
            "true_peak_resident_bytes differs from allocation lifetime census"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare and validate the frozen J002 contract"
    )
    parser.add_argument(
        "--producer-stream",
        type=Path,
        help="Accepted A001 stream-v1.bin",
    )
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="development-only; never use for retained evidence",
    )
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(
            f"J002 preparation must run on {EXPECTED_BRANCH}"
        )
    if not args.allow_dirty and git("status", "--porcelain"):
        raise RuntimeError(
            "J002 retained preparation requires a clean worktree"
        )

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    stream = (
        args.producer_stream.read_bytes()
        if args.producer_stream
        else None
    )
    manifest = build_manifest(cfg, stream)

    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    root = args.artifact_dir or (
        Path(env_root)
        if env_root
        else None
    )
    if root is None:
        root = (
            ROOT
            / "out/research/lane-j-topology-backend-alternatives"
            / "002-deterministic-topology-contract/prepare"
        )
    root.mkdir(
        parents=True,
        exist_ok=bool(env_root),
    )
    output = root / "j002-workload-manifest.json"
    output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"J002 manifest digest: {manifest['manifest_digest']}"
    )
    print(
        "A001 producer stream ready: "
        f"{manifest['producer_stream_ready']}"
    )
    for profile in manifest["profiles"]:
        print(
            f"{profile['name']}: "
            f"{profile['topology_digest']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
