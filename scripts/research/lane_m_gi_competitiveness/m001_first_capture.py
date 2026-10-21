#!/usr/bin/env python3
"""M001 first held-out *state* capture only. No scoring or speed claims."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from generate_heldout_geometry import ROOT, FACTORY, generate, verify, digest

LANE = ROOT / "research/lanes/lane-m-gi-competitiveness"
WORK = ROOT / "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1"
BINARY = ROOT / "build/n009/phos-n010-capture"
CONTRACT = ROOT / "out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract"
RUNNER = ROOT / "scripts/run_with_vulkan.sh"
MIN_FREE = 8 * 1024 ** 3


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def busy() -> list[str]:
    """Conservative check for concurrent known research GPU/CPU acquisitions."""
    seen = []
    proc = Path("/proc")
    if not proc.exists():
        raise ValueError("cannot attest concurrent-worker quiescence without /proc")
    for p in proc.iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            name = (p / "comm").read_text().strip()
            cmd = (p / "cmdline").read_bytes().decode("utf-8", "replace")
        except (OSError, PermissionError):
            continue
        if name.startswith(("phos-n010", "n010_", "n008_oracle")):
            seen.append(name)
        elif any(n in cmd for n in (
            "qualify_incremental_references.py",
            "acquire_corpus.py",
            "acquire_dynamic_pilot.py",
            "acquire_pt_pilot.py",
            "acquire_rc_pilot.py",
        )):
            seen.append(name)
    return seen


def preflight() -> dict:
    branch = git("branch", "--show-current")
    if branch != "research-lane-m-gi-competitiveness":
        raise ValueError("switch to research-lane-m-gi-competitiveness first")
    if not (LANE / "experiments/001-first-cohort-preregistration.md").is_file():
        raise FileNotFoundError("missing committed M001 preregistration")
    for path in (FACTORY, BINARY, CONTRACT, RUNNER):
        if not path.is_file():
            raise FileNotFoundError(f"missing required existing input: {path}")
    if WORK.exists():
        raise ValueError(f"refuse existing experiment root: {WORK}")
    running = busy()
    if running:
        raise ValueError(f"concurrent research worker: {running}")
    free = shutil.disk_usage(ROOT).free
    if free < MIN_FREE:
        raise ValueError("less than 8GiB free: no capture")
    return {
        "classification": "GPU_CAPTURE_PREFLIGHT_ONLY_NOT_RUN",
        "source_commit": git("rev-parse", "HEAD"),
        "branch": branch,
        "n004_source_sha256": digest(FACTORY),
        "capture_binary_sha256": digest(BINARY),
        "contract_sha256": digest(CONTRACT),
        "free_disk_bytes": free,
        "work": str(WORK.relative_to(ROOT)),
        "gpu_executed": False,
    }


def execute() -> dict:
    prior = preflight()
    WORK.mkdir(parents=True)
    assets = WORK / "assets"
    manifest = generate(assets)
    attestation = verify(assets / "manifest.json")
    row = manifest["scenes"][0]  # preregistered H01; do not choose from output
    out = WORK / "capture" / "M001-H01-hwrt"
    out.parent.mkdir(parents=True)
    command = [
        "bash", "scripts/run_with_vulkan.sh", str(BINARY),
        "--scene", str(assets / row["gltf"]), "--scenario", "static",
        "--backend", "hwrt", "--direct-profile", "ulp4", "--out", str(out),
    ]
    frozen = {
        "schema": "lane-m-m001-first-capture/1",
        "complete": False, "classification": "GPU_CAPTURE_NOT_YET_RUN",
        "preflight": prior, "generator_attestation": attestation,
        "geometry_manifest_sha256": digest(assets / "manifest.json"),
        "fixed_first_scene": "M001-H01", "command": command,
        "reference_eligible": False, "accepted_timing": False,
        "state_locked": False, "tests": "NOT_RUN",
    }
    receipt = WORK / "result.json"
    receipt.write_text(json.dumps(frozen, indent=2) + "\n")
    env = os.environ.copy()
    env["PHOS_N009_CONTRACT"] = str(CONTRACT)
    env["PHOS_N010_MEMORY_LEDGER"] = str(out / "allocation-ledger.json")
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    (WORK / "native.stdout.txt").write_text(proc.stdout)
    (WORK / "native.stderr.txt").write_text(proc.stderr)
    frozen["returncode"] = proc.returncode
    frozen["payload_sha256"] = {
        str(p.relative_to(WORK)): digest(p)
        for p in sorted(out.rglob("*")) if p.is_file()
    } if out.exists() else {}
    required = (
        "geometry-state.bin", "frame-state.bin", "capture.json",
        "gpu/direct.pfm", "gpu/indirect.pfm", "gpu/total.pfm",
        "allocation-ledger.json",
    )
    missing = [p for p in required if not (out / p).is_file()]
    frozen["required_capture_files"] = list(required)
    frozen["missing_capture_files"] = missing
    frozen["complete"] = proc.returncode == 0 and not missing
    frozen["classification"] = ("RAW_H01_GPU_CAPTURE_RETAINED_UNQUALIFIED"
                                if frozen["complete"] else "CAPTURE_FAILED_RETAIN_PARTIAL")
    receipt.write_text(json.dumps(frozen, indent=2) + "\n")
    return {"classification": frozen["classification"],
            "returncode": proc.returncode,
            "work": str(WORK.relative_to(ROOT)),
            "receipt": str(receipt.relative_to(ROOT)),
            "payload_count": len(frozen["payload_sha256"]),
            "next": "STOP: no other H02/H03 capture, reference admission or speed claim"}
    

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preflight-only", action="store_true")
    a = ap.parse_args()
    print(json.dumps(preflight() if a.preflight_only else execute(), indent=2))


if __name__ == "__main__":
    main()
