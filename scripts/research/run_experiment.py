#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANES = {
    "lane-a-split-rc",
    "lane-b-traversal",
    "lane-c-storage-locality",
    "lane-k-gpu-primary-calibration",
    "lane-n-end-to-end-renderer",
}
EXPERIMENT_RE = re.compile(r"^[0-9]{3}-[a-z0-9][a-z0-9-]*$")
GPU_RE = re.compile(r"^GPU:\s*(.+)$", re.MULTILINE)


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def tee_stream(stream, path: Path, target) -> None:
    with path.open("w", encoding="utf-8") as output:
        for line in iter(stream.readline, ""):
            output.write(line)
            output.flush()
            target.write(line)
            target.flush()
    stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one research-lane experiment and capture reproducibility metadata."
    )
    parser.add_argument("--lane", choices=sorted(LANES), required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--command", required=True)
    args = parser.parse_args()

    if not EXPERIMENT_RE.fullmatch(args.experiment):
        parser.error("--experiment must match NNN-lowercase-kebab-name")

    command = shlex.split(args.command)
    if not command:
        parser.error("--command must not be empty")

    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = (
        ROOT / "out" / "research" / args.lane / args.experiment / stamp
    ).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=False)

    env = os.environ.copy()
    env["PHOS_RESEARCH_ARTIFACT_DIR"] = str(artifact_dir)
    env["PHOS_RESEARCH_LANE"] = args.lane
    env["PHOS_RESEARCH_EXPERIMENT"] = args.experiment

    stdout_path = artifact_dir / "stdout.log"
    stderr_path = artifact_dir / "stderr.log"

    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    out_thread = threading.Thread(
        target=tee_stream, args=(proc.stdout, stdout_path, sys.stdout), daemon=True
    )
    err_thread = threading.Thread(
        target=tee_stream, args=(proc.stderr, stderr_path, sys.stderr), daemon=True
    )
    out_thread.start()
    err_thread.start()
    return_code = proc.wait()
    out_thread.join()
    err_thread.join()

    finished = datetime.now(timezone.utc)
    combined = (
        stdout_path.read_text(encoding="utf-8", errors="replace")
        + "\n"
        + stderr_path.read_text(encoding="utf-8", errors="replace")
    )
    gpu_match = GPU_RE.search(combined)

    metadata = {
        "schema_version": 1,
        "lane": args.lane,
        "experiment": args.experiment,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "duration_seconds": (finished - started).total_seconds(),
        "command": command,
        "return_code": return_code,
        "git": {
            "branch": git("branch", "--show-current"),
            "commit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain")),
        },
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "gpu": gpu_match.group(1).strip() if gpu_match else "unknown",
        },
        "environment": {
            "VK_DRIVER_FILES": env.get("VK_DRIVER_FILES"),
            "AMD_VULKAN_ICD": env.get("AMD_VULKAN_ICD"),
        },
        "artifact_dir": str(artifact_dir),
    }
    (artifact_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Research artifact: {artifact_dir}")
    if return_code != 0:
        print(
            f"Experiment command failed with exit code {return_code}; artifact retained.",
            file=sys.stderr,
        )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
