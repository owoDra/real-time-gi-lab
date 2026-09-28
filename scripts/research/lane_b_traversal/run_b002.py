#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run B002 exact Lane A stream traversal comparison."
    )
    parser.add_argument("--build-dir", default="build/release")
    parser.add_argument(
        "--scene",
        default="assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf",
    )
    parser.add_argument(
        "--lane-a-artifact",
        default=(
            "out/research/lane-a-split-rc/001-representative-producer/"
            "20260928T143212Z"
        ),
    )
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--build-repeats", type=int, default=3)
    parser.add_argument("--validation", action="store_true")
    args = parser.parse_args()

    executable = Path(args.build_dir) / "phos-lane-b-b002"
    maintenance = Path(args.build_dir) / "phos-lane-b-b002-maintenance"
    for required in (executable, maintenance):
        if not required.exists():
            raise SystemExit(
                f"B002 executable not found: {required}; run 'mise run build'"
            )
    scene = Path(args.scene)
    if not scene.exists():
        raise SystemExit(
            f"B002 scene not found: {scene}; run 'mise run assets'"
        )

    lane_a_root = Path(args.lane_a_artifact)
    for case in ("static", "camera-motion", "light-motion"):
        stream = lane_a_root / case / "stream-v1.bin"
        if not stream.exists():
            raise SystemExit(
                f"Accepted A001 replay stream not found: {stream}"
            )

    command = [
        "bash",
        "scripts/run_with_vulkan.sh",
        str(executable),
        "--scene",
        str(scene),
        "--lane-a-artifact",
        str(lane_a_root),
        "--iterations",
        str(args.iterations),
        "--build-repeats",
        str(args.build_repeats),
    ]
    if args.validation:
        command.append("--validation")

    env = os.environ.copy()
    print("+", " ".join(command), flush=True)
    completed = subprocess.run(command, env=env, check=False)
    if completed.returncode:
        return completed.returncode

    maintenance_command = [
        "bash",
        "scripts/run_with_vulkan.sh",
        str(maintenance),
        "--scene",
        str(scene),
        "--lane-a-artifact",
        str(lane_a_root),
        "--iterations",
        str(max(10, args.iterations // 2)),
    ]
    if args.validation:
        maintenance_command.append("--validation")
    print("+", " ".join(maintenance_command), flush=True)
    return subprocess.run(
        maintenance_command,
        env=env,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
