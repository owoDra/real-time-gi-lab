#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

CASES = ("static", "camera-motion", "light-motion")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", default="build/release")
    parser.add_argument(
        "--scene",
        default="assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf",
    )
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--validation", action="store_true")
    args = parser.parse_args()

    executable = (
        Path(args.build_dir)
        / "src/research/lane_a_split_rc/phos-lane-a-split-rc"
    )
    if not executable.exists():
        raise SystemExit(f"A001 executable not found: {executable}")
    if not Path(args.scene).exists():
        raise SystemExit(
            f"A001 scene not found: {args.scene}; run 'mise run assets' first"
        )

    artifact_root = Path(
        os.environ.get(
            "PHOS_RESEARCH_ARTIFACT_DIR",
            "out/research/lane-a-split-rc/001-representative-producer/manual",
        )
    )
    artifact_root.mkdir(parents=True, exist_ok=True)

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    summary = {}
    for case in CASES:
        output_dir = artifact_root / case
        output_dir.mkdir(parents=True, exist_ok=True)

        command = [
            "bash",
            "scripts/run_with_vulkan.sh",
            str(executable),
            "--scene",
            args.scene,
            "--case",
            case,
            "--iterations",
            str(args.iterations),
            "--output-dir",
            str(output_dir),
        ]
        if args.validation:
            command.append("--validation")

        env = os.environ.copy()
        env["PHOS_RESEARCH_GIT_COMMIT"] = commit
        print("+", " ".join(command), flush=True)
        completed = subprocess.run(command, env=env)
        if completed.returncode:
            return completed.returncode

        metrics = json.loads(
            (output_dir / "metrics.json").read_text(encoding="utf-8")
        )
        summary[case] = metrics
        correctness = metrics["correctness"]
        if not (
            correctness["visibility"]
            and correctness["producer"]
            and correctness["resolve"]
        ):
            return 2
        if not (output_dir / "stream-v1.bin").exists():
            raise SystemExit(
                f"{case}: correctness passed but replay stream was not exported"
            )

    (artifact_root / "summary.json").write_text(
        json.dumps(
            {
                "experiment": "001-representative-producer",
                "git_commit": commit,
                "iterations": args.iterations,
                "validation": args.validation,
                "artifact_root": str(artifact_root.resolve()),
                "scene": args.scene,
                "cases": summary,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"A001 correctness passed for {', '.join(CASES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
