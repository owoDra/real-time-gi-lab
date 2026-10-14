#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANES = {
    "lane-a-split-rc": {
        "src": "src/research/lane_a_split_rc/CMakeLists.txt",
        "shader": "shaders/research/lane_a_split_rc/README.md",
        "script": "scripts/research/lane_a_split_rc/README.md",
    },
    "lane-b-traversal": {
        "src": "src/research/lane_b_traversal/CMakeLists.txt",
        "shader": "shaders/research/lane_b_traversal/README.md",
        "script": "scripts/research/lane_b_traversal/README.md",
    },
    "lane-c-storage-locality": {
        "src": "src/research/lane_c_storage_locality/CMakeLists.txt",
        "shader": "shaders/research/lane_c_storage_locality/README.md",
        "script": "scripts/research/lane_c_storage_locality/README.md",
    },
    "lane-k-gpu-primary-calibration": {
        "src": "src/research/lane_k_gpu_primary_calibration/CMakeLists.txt",
        "shader": "shaders/research/lane_k_gpu_primary_calibration/README.md",
        "script": "scripts/research/lane_k_gpu_primary_calibration/README.md",
    },
    "lane-n-end-to-end-renderer": {
        "src": "src/research/lane_n_end_to_end_renderer/CMakeLists.txt",
        "shader": "shaders/research/lane_n_end_to_end_renderer/README.md",
        "script": "scripts/research/lane_n_end_to_end_renderer/README.md",
    },
    "n008-hdr-oracle": {
        "src": "src/research/n008_hdr_oracle/CMakeLists.txt",
        "shader": "shaders/research/n008_hdr_oracle/README.md",
        "script": "scripts/research/n008_hdr_oracle/README.md",
    },
    "n009-scene-contract": {
        "src": "src/research/n009_scene_contract/CMakeLists.txt",
        "shader": "shaders/research/n009_scene_contract/README.md",
        "script": "scripts/research/n009_scene_contract/README.md",
    },
    "n010-comparison-readiness": {
        "src": "src/research/n010_comparison_readiness/CMakeLists.txt",
        "shader": "shaders/research/n010_comparison_readiness/README.md",
        "script": "scripts/research/n010_comparison_readiness/README.md",
    },
}


def require(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing research harness path: {path.relative_to(ROOT)}")


def verify_index(index_path: Path, lane: str) -> int:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise SystemExit(f"{index_path}: unsupported schema_version")
    if payload.get("lane") != lane:
        raise SystemExit(f"{index_path}: lane does not match directory")
    experiments = payload.get("experiments")
    if not isinstance(experiments, list):
        raise SystemExit(f"{index_path}: experiments must be a list")
    seen = set()
    for row in experiments:
        if not isinstance(row, dict):
            raise SystemExit(f"{index_path}: experiment must be an object")
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise SystemExit(f"{index_path}: missing or duplicate experiment id {identifier!r}")
        seen.add(identifier)
        if not isinstance(row.get("status"), str) or not row["status"]:
            raise SystemExit(f"{index_path}: {identifier}: missing status")
        result = row.get("result")
        if not isinstance(result, str) or not result:
            raise SystemExit(f"{index_path}: {identifier}: missing result path")
        # Historical indexes use both results-relative and repository-relative
        # paths. Preserve their bytes and verify each declared local file.
        relative = Path(result.split("#", 1)[0])
        candidates = [(index_path.parent / relative).resolve(), (ROOT / relative).resolve()]
        existing = [p for p in candidates if p.is_relative_to(ROOT) and p.is_file()]
        if not existing:
            raise SystemExit(f"{index_path}: {identifier}: missing result file {result!r}")
        if existing[0].suffix == ".json":
            json.loads(existing[0].read_text(encoding="utf-8"))
    return len(experiments)


def main() -> int:
    require(ROOT / "AGENTS.md")
    require(ROOT / "research" / "README.md")
    require(ROOT / "research" / "protocol.md")
    require(ROOT / "scripts" / "research" / "run_experiment.py")

    records = 0
    for lane, owned in LANES.items():
        lane_root = ROOT / "research" / "lanes" / lane
        require(lane_root / "README.md")
        require(lane_root / "experiments" / "README.md")
        index_path = lane_root / "results" / "index.json"
        require(index_path)
        for path in owned.values():
            require(ROOT / path)

        records += verify_index(index_path, lane)

    print(f"research harness: OK ({len(LANES)} configured lane indexes, {records} declared result links; not runtime validation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
