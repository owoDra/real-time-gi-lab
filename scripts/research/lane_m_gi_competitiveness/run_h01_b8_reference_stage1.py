#!/usr/bin/env python3
"""M001 original N010 CPU RQMC for H01/T_B8: ONLY level 8192, four fixed seeds.

This is the next prospectively named transport after qualifying H01/T_B2.
No multi-cell queue, third/second level, GPU, candidate score, or timing.
Retain all native payloads and write only small proof metadata into repo/out/.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from run_h01_b2_reference_stage1 import (
    ROOT, LANE, SOURCES, BINARY, NET, VALIDATION, SEEDS,
    BINARY_SHA, NET_SHA, quiet, sha, require
)
from audit_h01_evidence import audit as audit_h01
from prepare_m001_n010_physical_inputs import CORRECTED_SHA

PRIOR_ADMISSION = ROOT / "out/research/lane-m-gi-competitiveness/m001-h01-b2-original-admitted-reference-v1/admission.json"
PRIOR_ADMISSION_SHA = "2bffa1e66206c1b3635351bb07bfc1538f17b05405c8c76f0bc6406eb1e49364"
SOURCES_MANIFEST_SHA = "faff7cae0afefa0cd66db71d7dd8a11445db7c0fffe3fb3a45111f4099c01abd"
VALIDATION_SHA = "dd58ddcdbc9b4975398ca1e0069aad9d1ed40a213f7d578f97fa827bdd3523df"
PHYSICAL_SOURCE = SOURCES / "M001-H01-T_B8.n008"
SOURCE_SHA = CORRECTED_SHA["H01"][8]
GEOMETRY_SHA = "fd6380ce0848e37d19f06c622f03dbbd76d0c900ff34b9195d2be155b4934966"
FRAME_SHA = "70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4"
WORK = ROOT / "out/research/lane-m-gi-competitiveness/m001-h01-b8-rqmc-first-level-v1"
ARCHIVE = ROOT / "out/m001-h01-b8-cpu-first-level.tar"
LEVELS = (8192, 16384, 32768, 65536, 131072, 262144)


def validate():
    require(subprocess.check_output(["git", "branch", "--show-current"],
                                    cwd=ROOT, text=True).strip() ==
            "research-lane-m-gi-competitiveness", "wrong branch")
    require(not WORK.exists() and not ARCHIVE.exists(), "refuse existing output/archive")
    require(shutil.disk_usage(ROOT).free >= 8*1024**3, "less than 8GiB free space")
    quiet()
    for path, expected in (
        (PRIOR_ADMISSION, PRIOR_ADMISSION_SHA),
        (SOURCES / "manifest.json", SOURCES_MANIFEST_SHA),
        (PHYSICAL_SOURCE, SOURCE_SHA), (VALIDATION, VALIDATION_SHA),
        (BINARY, BINARY_SHA), (NET, NET_SHA)):
        require(path.is_file() and sha(path) == expected,
                "frozen reference/physical source/proof SHA changed: " + str(path))
    admit = json.loads(PRIOR_ADMISSION.read_text(encoding="utf-8"))
    require(admit.get("complete") is True and admit.get("reference_eligible") is True
            and admit.get("verification", {}).get("pass") is True
            and admit["verification"]["cell"] == "H01"
            and admit["verification"]["transport"] == "T_B2"
            and admit["verification"]["levels"] == [8192,16384],
            "original H01/B2 reference was not admitted")
    proof = json.loads(VALIDATION.read_text(encoding="utf-8"))
    require(proof.get("complete") is True and proof.get("all_pass") is True
            and proof.get("binary_sha256") == BINARY_SHA
            and proof.get("sobol_table_sha256") == NET_SHA,
            "original N010 sampler physical validation differs")
    state = audit_h01(LANE, metadata_only=False)
    require(state["capture_payload_hashes_checked"] == 13
            and not state["capture_payload_hashes_unverified"]
            and state["reference_eligible"] is False,
            "frozen H01 native GPU source state no longer verifiable")
    scenes = json.loads((SOURCES / "manifest.json").read_text(encoding="utf-8"))
    expected_row = [r for r in scenes.get("transport_sources", [])
                    if r.get("cell") == "H01" and r.get("transport") == "T_B8"]
    require(len(expected_row) == 1
            and expected_row[0]["sha256"] == SOURCE_SHA
            and expected_row[0]["max_bounces"] == 8
            and scenes.get("complete") is True
            and scenes.get("classification") ==
                "PHYSICAL_SOURCE_BYTES_LOCKED_REFERENCE_INELIGIBLE",
            "H01 B8 transport is not the frozen N010-corrected source")


def run():
    validate()
    WORK.mkdir(parents=True)
    prefix = WORK / "oracle"
    command = [str(BINARY), "--net", str(NET), "--scene", str(PHYSICAL_SOURCE),
               "--out", str(prefix), "--seeds", ",".join(map(str,SEEDS)),
               "--spp", "8192"]
    record = {
        "schema": "lane-m-m001-h01-b8-first-cpu-reference-level/1",
        "classification": "CPU_ORACLE_NOT_RUN", "complete": False,
        "source_commit": subprocess.check_output(
            ["git","rev-parse","HEAD"], cwd=ROOT, text=True).strip(),
        "prior_H01_B2_reference_admission_sha256": PRIOR_ADMISSION_SHA,
        "source_sha256": SOURCE_SHA,
        "sources_manifest_sha256": SOURCES_MANIFEST_SHA,
        "n010_validation_sha256": VALIDATION_SHA,
        "binary_sha256": BINARY_SHA, "net_sha256": NET_SHA,
        "geometry_sha256": GEOMETRY_SHA, "frame_sha256": FRAME_SHA,
        "command": command, "scene": "H01", "transport": "T_B8",
        "spp": 8192, "seeds": list(map(str,SEEDS)),
        "reference_eligible": False, "quality_scored": False,
        "accepted_timing": False, "gpu_executed": False
    }
    receipt = WORK / "result.json"
    receipt.write_text(json.dumps(record,indent=2)+"\n", encoding="utf-8")
    p = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    (WORK / "oracle.stdout.txt").write_text(p.stdout, encoding="utf-8")
    (WORK / "oracle.stderr.txt").write_text(p.stderr, encoding="utf-8")
    record["returncode"] = p.returncode
    record["payload_sha256"] = {
        x.name:sha(x) for x in sorted(WORK.glob("oracle.*")) if x.is_file()
    }
    required = [f"oracle.s{i}.f64" for i in range(4)] + [
        f"oracle.s{i}.total.pfm" for i in range(4)]
    record["missing_required"] = [x for x in required if not (WORK/x).is_file()]
    record["complete"] = (p.returncode == 0 and not record["missing_required"]
                          and sha(PHYSICAL_SOURCE) == SOURCE_SHA)
    if record["complete"]:
        sys.path[:0] = [
            str(ROOT/"scripts/research/n008_hdr_oracle"),
            str(ROOT/"scripts/research/n007_reference_validity")
        ]
        import n008lib as N008
        import check_convergence as N007
        native = json.loads(p.stdout)
        require(native.get("oracle") == "n010-rqmc-digital-shift"
                and native.get("scene_sha256") == SOURCE_SHA
                and native.get("geometry_sha256") == GEOMETRY_SHA
                and native.get("spp") == 8192
                and native.get("seeds") == list(SEEDS)
                and native.get("triangles") == 1224
                and native.get("width") == 320 and native.get("height") == 180
                and len(native.get("runs",[])) == 4,
                "H01 B8 native metadata differs")
        for i,seed in enumerate(SEEDS):
            data = N008.read_sidecar(WORK/f"oracle.s{i}.f64")
            require((data["seed"],data["spp"],data["width"],data["height"]) ==
                    (seed,8192,320,180), "wrong H01 B8 F64 replicate")
        manifest = {
            "schema_version": 1, "source_commit": record["source_commit"],
            "scene_sha256": SOURCE_SHA, "frame_state_sha256": FRAME_SHA,
            "levels": [{"spp":8192,"references":[
                {"seed":seed,"path":f"oracle.s{i}.total.pfm",
                 "sha256":sha(WORK/f"oracle.s{i}.total.pfm")}
                for i,seed in enumerate(SEEDS)]}]
        }
        (WORK/"level1-input-manifest.json").write_text(
            json.dumps(manifest,indent=2)+"\n", encoding="utf-8")
        N007.SPP = LEVELS
        screen = N007.assess(WORK/"level1-input-manifest.json")
        require(screen.get("status") == "incomplete"
                and screen.get("eligible_at_spp") is None
                and screen.get("physical_correctness_proven") is False
                and len(screen.get("rows",[])) == 1,
                "single-level N007 assessment cannot be admitted")
        (WORK/"level1-screen.json").write_text(
            json.dumps(screen,indent=2)+"\n", encoding="utf-8")
        record["first_level_statistically_eligible"] = screen["rows"][0]["eligible"]
        record["first_level_statistical_problems"] = screen["rows"][0]["problems"]
        record["original_n007_status"] = screen["status"]
    record["classification"] = (
        "CPU_H01_B8_FIRST_LEVEL_RETAINED_REFERENCE_INELIGIBLE"
        if record["complete"] else "CPU_H01_B8_FIRST_LEVEL_FAILED_RETAIN_PARTIAL"
    )
    receipt.write_text(json.dumps(record,indent=2)+"\n", encoding="utf-8")
    archive = None
    if record["complete"]:
        ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
        with ARCHIVE.open("xb") as handle:
            with tarfile.open(fileobj=handle,mode="w") as tar:
                for filename in ("result.json","oracle.stdout.txt","oracle.stderr.txt",
                                 "level1-input-manifest.json","level1-screen.json"):
                    tar.add(WORK/filename,arcname=filename,recursive=False)
                tar.add(SOURCES/"manifest.json",
                        arcname="corrected-sources-manifest.json",recursive=False)
        archive = str(ARCHIVE.relative_to(ROOT))
    print(json.dumps({
        "classification":record["classification"],
        "returncode":p.returncode, "spp":8192,
        "first_level_eligible":record.get("first_level_statistically_eligible"),
        "reference_eligible":False,
        "archive":archive,
        "next":"STOP: inspect first-level result before any other level/cell or GPU task"
    },indent=2))


if __name__=="__main__":
    run()
