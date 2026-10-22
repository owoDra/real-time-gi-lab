#!/usr/bin/env python3
"""Exactly one preregistered H03 GPU state capture, after full local H01/H02 CPU audits.

Never acquire reference/quality/timing, execute H01/H02 again, run H03 twice, or queue
more GPU work. Automatically write a compact state-only TAR into repository out/.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from audit_h01_evidence import audit as audit_h01
from audit_h02_evidence import audit as audit_h02
from generate_heldout_geometry import ROOT, FACTORY, verify, digest
from m001_first_capture import BINARY, CONTRACT, RUNNER, MIN_FREE, busy, git

WORK = ROOT / "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1"
H03 = WORK / "capture/M001-H03-hwrt"
RESULT = WORK / "result-h03.json"
STDOUT = WORK / "native-h03.stdout.txt"
STDERR = WORK / "native-h03.stderr.txt"
ARCHIVE = ROOT / "out/m001-h03-state.tar"
H02_RESULT_SHA = "5562656fad898b07ac91903affd7d0f00423b1813f2a59dc67941fc22e23f765"
MANIFEST_SHA = "55e656caa352352fba160c1e02151f17237c116f37de2f2f0c2517893f25a707"
GLTF_SHA = "23b1a96560c405dfc645f8de51afef4fb4cbdca4e06d75ee32097bde034c9424"
BIN_SHA = "bab24715916c2a62a02f55aab4a9d0c1f43ca860600cb0529ca70e8b41d643f4"
REQUIRED = ("geometry-state.bin", "frame-state.bin", "capture.json", "allocation-ledger.json",
            "gpu/direct.pfm", "gpu/indirect.pfm", "gpu/total.pfm")
ARCHIVE_FILES = (
    "result.json", "result-h02.json", "result-h03.json", "assets/manifest.json",
    "assets/M001-H03.gltf", "assets/M001-H03.bin",
    "capture/M001-H03-hwrt/geometry-state.bin",
    "capture/M001-H03-hwrt/frame-state.bin",
    "capture/M001-H03-hwrt/capture.json",
    "capture/M001-H03-hwrt/allocation-ledger.json",
)


def require(ok, label):
    if not ok:
        raise ValueError(label)


def preflight():
    require(git("branch", "--show-current") == "research-lane-m-gi-competitiveness",
            "wrong branch")
    require(WORK.is_dir(), "missing preserved H01/H02 experiment")
    require(not any(p.exists() for p in (H03, RESULT, STDOUT, STDERR, ARCHIVE)),
            "refuse existing H03 output, result, logs or archive: never overwrite or retry")
    require(shutil.disk_usage(ROOT).free >= MIN_FREE, "less than 8GiB free disk")
    require(not busy(), "another research worker active")
    for path in (FACTORY, BINARY, CONTRACT, RUNNER):
        require(path.is_file(), "missing pinned research input: " + str(path))
    require(digest(WORK / "result-h02.json") == H02_RESULT_SHA,
            "H02 owner receipt changed since independent CPU audit")
    h01 = audit_h01(WORK, metadata_only=False)
    h02 = audit_h02(WORK, metadata_only=False)
    require(not h01["capture_payload_hashes_unverified"]
            and not h02["capture_payloads_not_provided"],
            "H01/H02 full retained local payload SHA-256 replay failed")
    require(h01["reference_eligible"] is False and h02["reference_eligible"] is False,
            "prior raw state improperly accepted as reference")
    assets = WORK / "assets"
    manifest_path = assets / "manifest.json"
    require(digest(manifest_path) == MANIFEST_SHA, "M001 original preregistration drift")
    verify(manifest_path)
    row = json.loads(manifest_path.read_text(encoding="utf-8"))["scenes"][2]
    require((row["name"], row["kind"], row["wall_thickness_world"], row["triangle_count"])
            == ("M001-H03", "enclosed", 0.127, 1248), "nonpreregistered H03 scene")
    require(row["eligible_reference"] is False and row["gpu_state_frozen"] is False,
            "H03 geometry manifest prematurely admitted")
    gltf, binary = assets / "M001-H03.gltf", assets / "M001-H03.bin"
    require(digest(gltf) == GLTF_SHA == row["gltf_sha256"], "H03 glTF SHA changed")
    require(digest(binary) == BIN_SHA == row["bin_sha256"], "H03 BIN SHA changed")
    return {"scene": row, "h01_state_input_audit": h01["classification"],
            "h02_state_input_audit": h02["classification"],
            "h01_payload_count_rechecked": h01["capture_payload_hashes_checked"],
            "h02_payload_count_rechecked": len(h02["capture_payloads_hash_verified"])}


def create_archive():
    """Only after a completed native capture; exclusive file create in repo/out/."""
    missing = [rel for rel in ARCHIVE_FILES if not (WORK / rel).is_file()]
    require(not missing, "cannot pack compact H03 state: " + str(missing))
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w") as tar:
            for rel in ARCHIVE_FILES:
                tar.add(WORK / rel, arcname=rel, recursive=False)
    return str(ARCHIVE.relative_to(ROOT))


def execute():
    ready = preflight()
    scene = WORK / "assets/M001-H03.gltf"
    command = ["bash", "scripts/run_with_vulkan.sh", str(BINARY),
               "--scene", str(scene), "--scenario", "static",
               "--backend", "hwrt", "--direct-profile", "ulp4", "--out", str(H03)]
    inputs = {str(p.relative_to(ROOT)): digest(p) for p in
              (FACTORY, BINARY, CONTRACT, RUNNER, scene, WORK / "assets/M001-H03.bin")}
    evidence = {"schema": "lane-m-m001-h03-first-capture/1", "complete": False,
                "classification": "H03_PREPARED_NOT_EXECUTED",
                "source_commit": git("rev-parse", "HEAD"),
                "scene": ready["scene"], "command": command,
                "preflight": ready, "source_input_sha256": inputs,
                "manifest_sha256": MANIFEST_SHA,
                "h02_receipt_sha256": H02_RESULT_SHA,
                "reference_eligible": False, "accepted_timing": False,
                "state_locked": False, "quality_scored": False}
    RESULT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    env = os.environ.copy()
    env["PHOS_N009_CONTRACT"] = str(CONTRACT)
    env["PHOS_N010_MEMORY_LEDGER"] = str(H03 / "allocation-ledger.json")
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    STDOUT.write_text(proc.stdout, encoding="utf-8")
    STDERR.write_text(proc.stderr, encoding="utf-8")
    evidence["returncode"] = proc.returncode
    evidence["payload_sha256"] = {
        str(p.relative_to(H03)): digest(p)
        for p in sorted(H03.rglob("*")) if p.is_file()
    } if H03.exists() else {}
    evidence["missing_required"] = [p for p in REQUIRED if not (H03 / p).is_file()]
    evidence["inputs_unchanged"] = all(digest(ROOT / name) == value for name, value in inputs.items())
    evidence["complete"] = (proc.returncode == 0 and not evidence["missing_required"]
                            and evidence["inputs_unchanged"])
    evidence["classification"] = ("H03_RAW_STATE_CAPTURE_RETAINED_UNQUALIFIED"
                                  if evidence["complete"] else "H03_CAPTURE_FAILED_RETAIN_PARTIAL")
    RESULT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    archive = create_archive() if evidence["complete"] else None
    print(json.dumps({
        "classification": evidence["classification"],
        "returncode": proc.returncode, "payload_count": len(evidence["payload_sha256"]),
        "receipt": str(RESULT.relative_to(ROOT)), "state_archive": archive,
        "next": "STOP: do not run any more GPU operations, acquire references or claim speed"
    }, indent=2))


if __name__ == "__main__":
    execute()
