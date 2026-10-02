#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import n001_contract as contract

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/001-n001-config.json"


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    value = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if value:
        return Path(value).resolve()
    return (ROOT / "out/research/lane-n-end-to-end-renderer/001-renderer-reference-bringup/manual").resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lane N N001 renderer/reference contract and target-artifact validator")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "validate-target"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--target-artifact", type=Path)
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

    if args.target_artifact is None:
        parser.error("--target-artifact is required for --phase validate-target")
    result = contract.validate_target_artifact(args.target_artifact.resolve(), config)
    output = args.target_artifact.resolve() / "n001-validation-summary.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("N001 target artifact validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
