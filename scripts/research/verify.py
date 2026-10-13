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
}


def require(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"missing research harness path: {path.relative_to(ROOT)}")


def main() -> int:
    require(ROOT / "AGENTS.md")
    require(ROOT / "research" / "README.md")
    require(ROOT / "research" / "protocol.md")
    require(ROOT / "scripts" / "research" / "run_experiment.py")

    for lane, owned in LANES.items():
        lane_root = ROOT / "research" / "lanes" / lane
        require(lane_root / "README.md")
        require(lane_root / "experiments" / "README.md")
        index_path = lane_root / "results" / "index.json"
        require(index_path)
        for path in owned.values():
            require(ROOT / path)

        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise SystemExit(f"{index_path}: unsupported schema_version")
        if payload.get("lane") != lane:
            raise SystemExit(f"{index_path}: lane does not match directory")
        if not isinstance(payload.get("experiments"), list):
            raise SystemExit(f"{index_path}: experiments must be a list")

    print("research harness: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
