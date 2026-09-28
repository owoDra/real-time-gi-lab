#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess


ACCEPTED_A001_COMMIT = "8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f"
CASES = ("static", "camera-motion", "light-motion")
EXPECTED_BRANCH = "research-lane-b-traversal"


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise SystemExit(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def validate_checkout() -> str:
    branch = git_output("branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise SystemExit(
            f"B003 formal run requires branch {EXPECTED_BRANCH!r}, got {branch!r}"
        )
    dirty = git_output("status", "--porcelain")
    if dirty:
        raise SystemExit(
            "B003 formal run requires a clean Git tree; commit/stash local changes first"
        )
    return git_output("rev-parse", "HEAD")


def validate_lane_a_artifact(root: Path) -> None:
    for case in CASES:
        case_root = root / case
        stream = case_root / "stream-v1.bin"
        manifest = case_root / "stream-v1.json"
        if not stream.exists():
            raise SystemExit(f"Accepted A001 replay stream not found: {stream}")
        if not manifest.exists():
            raise SystemExit(f"Accepted A001 replay manifest not found: {manifest}")

        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("schema_version") != 1:
            raise SystemExit(f"{manifest}: expected schema_version=1")
        if payload.get("case") != case:
            raise SystemExit(
                f"{manifest}: case mismatch, expected {case!r}"
            )
        if payload.get("git_commit") != ACCEPTED_A001_COMMIT:
            raise SystemExit(
                f"{manifest}: expected accepted A001 commit "
                f"{ACCEPTED_A001_COMMIT}, got {payload.get('git_commit')!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run B003 Stage A wide software traversal comparison."
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

    commit = validate_checkout()
    print(f"b003_git_commit={commit}", flush=True)

    semantic_smoke = Path(args.build_dir) / "phos-lane-b-b002-smoke"
    structural_smoke = Path(args.build_dir) / "phos-lane-b-b003-smoke"
    executable = Path(args.build_dir) / "phos-lane-b-b003"
    for required in (semantic_smoke, structural_smoke, executable):
        if not required.exists():
            raise SystemExit(
                f"B003 executable not found: {required}; run 'mise run build'"
            )

    scene = Path(args.scene)
    if not scene.exists():
        raise SystemExit(
            f"B003 scene not found: {scene}; run 'mise run assets'"
        )

    lane_a_root = Path(args.lane_a_artifact)
    validate_lane_a_artifact(lane_a_root)

    for smoke in (semantic_smoke, structural_smoke):
        smoke_command = [str(smoke)]
        print("+", " ".join(smoke_command), flush=True)
        smoke_result = subprocess.run(
            smoke_command,
            env=os.environ.copy(),
            check=False,
        )
        if smoke_result.returncode:
            return smoke_result.returncode

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

    print("+", " ".join(command), flush=True)
    return subprocess.run(
        command,
        env=os.environ.copy(),
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
