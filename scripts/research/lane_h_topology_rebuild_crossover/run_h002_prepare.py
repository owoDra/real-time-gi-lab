#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import h002_contract as contract

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_BRANCH = "research-lane-h-topology-rebuild-crossover"
CONFIG = (
    ROOT / "research/lanes/lane-h-topology-rebuild-crossover/experiments"
    / "002-same-boundary-topology-comparator-config.json"
)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip())
    return proc.stdout.strip()


def build_manifest(cfg: dict[str, object]) -> dict[str, object]:
    steps = contract.topology_sequence(
        int(cfg["base_primitive_count"]),
        [float(value) for value in cfg["primitive_count_factors"]],
        int(cfg["topology_seed"]),
        float(cfg["replacement_fraction"]),
    )
    digest = contract.workload_digest(
        steps,
        producer_contract=str(cfg["producer_contract"]),
        hit_contract=str(cfg["hit_contract"]),
        storage_contract=str(cfg["storage_contract"]),
    )
    expected_digest = cfg.get("expected_workload_digest")
    if expected_digest is not None and digest != expected_digest:
        raise ValueError(
            f"H002 workload digest drift: expected {expected_digest}, got {digest}"
        )
    return {
        "schema_version": 1,
        "plan_version": cfg["plan_version"],
        "workload_digest": digest,
        "producer_contract": cfg["producer_contract"],
        "hit_contract": cfg["hit_contract"],
        "storage_contract": cfg["storage_contract"],
        "changed_object_id": cfg["changed_object_id"],
        "immutable_owner_ids": cfg["immutable_owner_ids"],
        "steps": [
            {
                "index": step.index,
                "primitive_count": step.primitive_count,
                "topology_seed": step.topology_seed,
                "replacement_count": step.replacement_count,
            }
            for step in steps
        ],
        "candidate_set": cfg["candidate_set"],
        "required_boundary_fields": cfg["required_boundary_fields"],
    }


def validate_evidence_record(
    record: dict[str, object],
    *,
    manifest: dict[str, object],
) -> None:
    if record.get("workload_digest") != manifest["workload_digest"]:
        raise ValueError("candidate workload digest differs from frozen H002 workload")
    if record.get("producer_contract") != manifest["producer_contract"]:
        raise ValueError("producer contract mismatch")
    if record.get("hit_contract") != manifest["hit_contract"]:
        raise ValueError("Hit contract mismatch")
    if record.get("storage_contract") != manifest["storage_contract"]:
        raise ValueError("storage contract mismatch")

    contract.validate_boundary_record(
        record,
        [str(value) for value in manifest["required_boundary_fields"]],
    )

    quality = record.get("correctness")
    if not isinstance(quality, dict) or quality.get("passed") is not True:
        raise ValueError("candidate correctness must PASS before timing evidence is usable")
    for key in (
        "visibility_mismatches",
        "producer_semantic_errors",
        "hit_mismatches",
        "traversal_runtime_errors",
        "storage_failures",
    ):
        if int(quality.get(key, -1)) != 0:
            raise ValueError(f"correctness field is nonzero: {key}")

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
            str(value) for value in manifest["immutable_owner_ids"]
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
        )
        for item in raw_allocations
    ]
    recomputed_peak = contract.true_peak_resident_bytes(allocations)
    if recomputed_peak != int(record["true_peak_resident_bytes"]):
        raise ValueError(
            "true_peak_resident_bytes does not match allocation lifetime census"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()

    if git("branch", "--show-current") != EXPECTED_BRANCH:
        raise RuntimeError(f"H002 preparation must run on {EXPECTED_BRANCH}")
    if git("status", "--porcelain"):
        raise RuntimeError("H002 preparation requires a clean worktree")

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    manifest = build_manifest(cfg)
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    root = args.artifact_dir or (Path(env_root) if env_root else None)
    if root is None:
        root = (
            ROOT / "out/research/lane-h-topology-rebuild-crossover"
            / "002-same-boundary-topology-comparator" / "prepare"
        )
    root.mkdir(parents=True, exist_ok=bool(env_root))
    (root / "h002-workload-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"H002 workload digest: {manifest['workload_digest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
