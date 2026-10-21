#!/usr/bin/env python3
"""One and only one preregistered M001-H02 GPU state capture; no scoring.

H01 state identity and fixed H02 glTF bytes are checked before any GPU work.
H01 inputs/outputs are never edited. No automatic H03 or reference acquisition.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from generate_heldout_geometry import ROOT, FACTORY, verify, digest
from m001_first_capture import busy, git, MIN_FREE, CONTRACT, BINARY, RUNNER

WORK = ROOT / "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1"
H01 = WORK / "capture/M001-H01-hwrt"
H02 = WORK / "capture/M001-H02-hwrt"
RESULT = WORK / "result-h02.json"
STDOUT = WORK / "native-h02.stdout.txt"
STDERR = WORK / "native-h02.stderr.txt"
STATE_SHA = {
    "geometry-state.bin": "f8b25b1c20ad84b6b9b030a2edd12c4a812af7199e21002897be9cf974ad75ca",
    "frame-state.bin": "70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4",
}
H02_GLTF_SHA = "25a6ba40cb1f6065284b5da5bc979e33562cf65f913bf6808e35b38782eb6747"
H02_BIN_SHA = "fd2c7e09c7da2ff0f6760dc09c09c524586e2126328a26666dd98d35640ef94b"


def ensure(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def validate_h01():
    receipt = json.loads((WORK / "result.json").read_text())
    ensure(receipt["preflight"]["source_commit"] ==
           "948d38c339190340b9e3f91f8ec0347b3b4a0109", "H01 original source not pinned")
    ensure(receipt["classification"] == "RAW_H01_GPU_CAPTURE_RETAINED_UNQUALIFIED"
           and receipt["returncode"] == 0 and receipt["complete"] is True
           and receipt["reference_eligible"] is False and
           receipt["accepted_timing"] is False, "H01 not in expected non-admitted state")
    ensure(len(receipt["payload_sha256"]) == 13 and
           not receipt["missing_capture_files"], "H01 inventory incomplete")
    for name, expected in STATE_SHA.items():
        source = H01 / name
        ensure(source.is_file() and digest(source) == expected
               and receipt["payload_sha256"]["capture/M001-H01-hwrt/" + name] == expected,
               "H01 state changed since independent CPU audit")
    for name in ("capture.json", "allocation-ledger.json"):
        source = H01 / name
        ensure(digest(source) == receipt["payload_sha256"]["capture/M001-H01-hwrt/" + name],
               "H01 audit-matched metadata changed")
    return receipt


def run():
    ensure(git("branch", "--show-current") == "research-lane-m-gi-competitiveness",
           "wrong research branch")
    ensure(WORK.is_dir() and H01.is_dir(), "missing complete previous H01 work")
    ensure(not any(p.exists() for p in (H02, RESULT, STDOUT, STDERR)),
           "refuse any H02 existing output/receipt")
    ensure(shutil.disk_usage(ROOT).free >= MIN_FREE, "less than 8GiB free disk")
    ensure(not busy(), "another scientific GPU/research worker is running")
    for path in (FACTORY, BINARY, CONTRACT, RUNNER):
        ensure(path.is_file(), "missing preserved input: " + str(path))
    prior = validate_h01()
    ensure(digest(FACTORY) == prior["preflight"]["n004_source_sha256"],
           "N004 generator changed")
    assets = WORK / "assets"
    manifest = json.loads((assets / "manifest.json").read_text())
    ensure(digest(assets / "manifest.json") == prior["geometry_manifest_sha256"],
           "original preregistration manifest changed")
    verify(assets / "manifest.json")
    row = manifest["scenes"][1]
    ensure((row["name"], row["kind"], row["wall_thickness_world"], row["triangle_count"])
           == ("M001-H02", "grazing", 0.163, 1224), "non-preregistered H02")
    scene, binary = assets / row["gltf"], assets / row["bin"]
    ensure(digest(scene) == H02_GLTF_SHA == row["gltf_sha256"], "H02 geometry changed")
    ensure(digest(binary) == H02_BIN_SHA == row["bin_sha256"], "H02 binary changed")
    command = [
        "bash", "scripts/run_with_vulkan.sh", str(BINARY),
        "--scene", str(scene), "--scenario", "static",
        "--backend", "hwrt", "--direct-profile", "ulp4", "--out", str(H02),
    ]
    before = {str(p.relative_to(ROOT)): digest(p) for p in
              (BINARY, CONTRACT, scene, binary)}
    evidence = {
        "schema": "lane-m-m001-h02-first-capture/1",
        "source_commit": git("rev-parse", "HEAD"),
        "complete": False, "classification": "H02_PREPARED_NOT_EXECUTED",
        "scene": row, "command": command, "source_input_sha256": before,
        "h01_receipt_sha256": digest(WORK / "result.json"),
        "h01_geometry_sha256": STATE_SHA["geometry-state.bin"],
        "h01_frame_sha256": STATE_SHA["frame-state.bin"],
        "reference_eligible": False, "accepted_timing": False, "tests": "NOT_RUN",
    }
    RESULT.write_text(json.dumps(evidence, indent=2)+"\n")
    env = os.environ.copy()
    env["PHOS_N009_CONTRACT"] = str(CONTRACT)
    env["PHOS_N010_MEMORY_LEDGER"] = str(H02 / "allocation-ledger.json")
    proc = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    STDOUT.write_text(proc.stdout)
    STDERR.write_text(proc.stderr)
    evidence["returncode"] = proc.returncode
    evidence["payload_sha256"] = {
        str(p.relative_to(H02)): digest(p) for p in sorted(H02.rglob("*")) if p.is_file()
    } if H02.exists() else {}
    required = ("geometry-state.bin", "frame-state.bin", "capture.json",
                "allocation-ledger.json", "gpu/direct.pfm", "gpu/indirect.pfm",
                "gpu/total.pfm")
    evidence["missing_required"] = [name for name in required if not (H02 / name).is_file()]
    evidence["inputs_unchanged"] = all(digest(ROOT / name) == value for name, value in before.items())
    evidence["complete"] = proc.returncode == 0 and not evidence["missing_required"] and evidence["inputs_unchanged"]
    evidence["classification"] = ("H02_RAW_STATE_CAPTURE_RETAINED_UNQUALIFIED"
                                  if evidence["complete"] else "H02_CAPTURE_FAILED_RETAIN_PARTIAL")
    RESULT.write_text(json.dumps(evidence, indent=2)+"\n")
    print(json.dumps({
        "classification": evidence["classification"], "returncode": proc.returncode,
        "payload_count": len(evidence["payload_sha256"]),
        "result": str(RESULT.relative_to(ROOT)),
        "next": "STOP: no H03, scoring, reference admission or timing claim"
    }, indent=2))


if __name__ == "__main__":
    run()
