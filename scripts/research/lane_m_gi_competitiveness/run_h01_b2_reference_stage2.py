#!/usr/bin/env python3
"""Single original N010 H01/B2 16384spp CPU level and unchanged two-level N007 screen.

Fail-closed on all 23 prior raw image/F64 hashes. Never overwrite evidence,
re-run any prior level, execute a GPU job or automatically qualify a reference.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from run_h01_b2_reference_stage1 import (
    ROOT, SOURCES, BINARY, NET, VALIDATION, SEEDS,
    BINARY_SHA, NET_SHA, quiet, sha, require
)
from prepare_m001_n010_physical_inputs import CORRECTED_SHA

PRIOR=ROOT/"out/research/lane-m-gi-competitiveness/m001-h01-b2-rqmc-first-level-v1"
WORK=ROOT/"out/research/lane-m-gi-competitiveness/m001-h01-b2-rqmc-second-level-v1"
ARCHIVE=ROOT/"out/m001-h01-b2-cpu-second-level.tar"
SCENE=SOURCES/"M001-H01-T_B2.n008"
SCHEDULE=(8192,16384,32768,65536,131072,262144)
FIRST_SHA="f8cd89121b149adcba824134fdde08102e88d99320cc378c966093324273cfe8"
FIRST_SCREEN_SHA="aaf7b9458df18097d4fee2dd6b1cbad4bde14f05e0c976f4146bdea75c182546"
FIRST_INPUT_SHA="a2b32c59b8aed4287f1035bdf13c3549b8451ac74a48b1980ac53d47d666938b"
SOURCE_MANIFEST_SHA="faff7cae0afefa0cd66db71d7dd8a11445db7c0fffe3fb3a45111f4099c01abd"
VALIDATION_SHA="dd58ddcdbc9b4975398ca1e0069aad9d1ed40a213f7d578f97fa827bdd3523df"
GEOMETRY_SHA="fd6380ce0848e37d19f06c622f03dbbd76d0c900ff34b9195d2be155b4934966"
FRAME_SHA="70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4"


def frozen_first():
    for path,expected in (
        (PRIOR/"result.json",FIRST_SHA),
        (PRIOR/"level1-screen.json",FIRST_SCREEN_SHA),
        (PRIOR/"level1-input-manifest.json",FIRST_INPUT_SHA),
        (SOURCES/"manifest.json",SOURCE_MANIFEST_SHA),
        (SCENE,CORRECTED_SHA["H01"][2]),
        (BINARY,BINARY_SHA), (NET,NET_SHA),(VALIDATION,VALIDATION_SHA)):
        require(path.is_file() and sha(path)==expected,"frozen CPU input hash changed: "+str(path))
    validation=json.loads(VALIDATION.read_text())
    require(validation.get("complete") is True and validation.get("all_pass") is True
            and validation.get("binary_sha256")==BINARY_SHA
            and validation.get("sobol_table_sha256")==NET_SHA,"N010 physical/sampler proof differs")
    first=json.loads((PRIOR/"result.json").read_text())
    screen=json.loads((PRIOR/"level1-screen.json").read_text())
    manifest=json.loads((PRIOR/"level1-input-manifest.json").read_text())
    require(first.get("classification")=="CPU_H01_B2_FIRST_LEVEL_RETAINED_REFERENCE_INELIGIBLE"
            and first.get("complete") is True and first.get("returncode")==0
            and first.get("reference_eligible") is False
            and first.get("spp")==8192 and first.get("seeds")==list(map(str,SEEDS))
            and first.get("source_sha256")==CORRECTED_SHA["H01"][2]
            and first.get("validation_sha256")==VALIDATION_SHA,"incorrect prior oracle receipt")
    require(screen.get("status")=="incomplete" and screen.get("eligible_at_spp") is None
            and screen.get("physical_correctness_proven") is False
            and len(screen.get("rows",[]))==1
            and screen["rows"][0]["spp"]==8192
            and screen["rows"][0]["eligible"] is True and not screen["rows"][0]["problems"],
            "first-level N007 row is ineligible or different")
    require(manifest.get("scene_sha256")==CORRECTED_SHA["H01"][2]
            and manifest.get("frame_state_sha256")==FRAME_SHA
            and [x["seed"] for x in manifest["levels"][0]["references"]]==list(SEEDS),
            "prior N007 manifest identity changed")
    files=first.get("payload_sha256")
    require(type(files) is dict and len(files)==23,"original stage1 raw inventory incomplete")
    for name,expected in files.items():
        path=(PRIOR/name).resolve()
        require(not Path(name).is_absolute() and ".." not in Path(name).parts
                and path.is_relative_to(PRIOR) and path.is_file()
                and sha(path)==expected,"first-level raw payload changed: "+name)
    for i,seed in enumerate(SEEDS):
        row=manifest["levels"][0]["references"][i]
        require(row["seed"]==seed and
                row["sha256"]==files[f"oracle.s{i}.total.pfm"],
                "first-level reference payload mismatch")
    native=json.loads((PRIOR/"oracle.stdout.txt").read_text())
    require(native.get("oracle")=="n010-rqmc-digital-shift"
            and native.get("scene_sha256")==CORRECTED_SHA["H01"][2]
            and native.get("geometry_sha256")==GEOMETRY_SHA
            and native.get("triangles")==1224 and native.get("spp")==8192
            and native.get("seeds")==list(SEEDS),"first-level actual oracle stdout differs")
    return first


def run():
    require(subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
            =="research-lane-m-gi-competitiveness","wrong branch")
    require(not WORK.exists() and not ARCHIVE.exists(),"refuse existing CPU second-level work or archive")
    require(shutil.disk_usage(ROOT).free>=8*1024**3,"less than 8GiB free disk")
    quiet()
    first=frozen_first()
    WORK.mkdir(parents=True)
    # Original N007 rejects outside-root references. Copy verified PFM bytes into
    # the new root. This does not mutate old first-level corpus.
    for i in range(4):
        name=f"oracle.s{i}.total.pfm"
        shutil.copyfile(PRIOR/name,WORK/f"first-level-s{i}.total.pfm")
        require(sha(WORK/f"first-level-s{i}.total.pfm")==first["payload_sha256"][name],
                "copied first-level reference changed")
    prefix=WORK/"oracle"
    cmd=[str(BINARY),"--net",str(NET),"--scene",str(SCENE),"--out",str(prefix),
         "--seeds",",".join(map(str,SEEDS)),"--spp","16384"]
    result={
      "schema":"lane-m-m001-h01-b2-second-cpu-level/1",
      "complete":False,"classification":"NOT_RUN",
      "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
      "original_8192_result_sha256":FIRST_SHA,
      "original_8192_screen_sha256":FIRST_SCREEN_SHA,
      "first_level_payload_hashes_verified":23,
      "physical_source_sha256":sha(SCENE),"physical_manifest_sha256":sha(SOURCES/"manifest.json"),
      "validation_sha256":sha(VALIDATION),"binary_sha256":sha(BINARY),"net_sha256":sha(NET),
      "command":cmd,"scene":"H01","transport":"T_B2","spp":16384,
      "seeds":[str(x) for x in SEEDS],
      "reference_eligible":False,"accepted_timing":False,"quality_scored":False,"gpu_executed":False
    }
    receipt=WORK/"result.json"
    receipt.write_text(json.dumps(result,indent=2)+"\n")
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    (WORK/"oracle.stdout.txt").write_text(p.stdout)
    (WORK/"oracle.stderr.txt").write_text(p.stderr)
    result["returncode"]=p.returncode
    result["payload_sha256"]={
        path.name:sha(path) for path in sorted(WORK.glob("oracle.*")) if path.is_file()
    }
    req=[f"oracle.s{i}.f64" for i in range(4)]+[
        f"oracle.s{i}.total.pfm" for i in range(4)]
    result["missing_required"]=[x for x in req if not (WORK/x).is_file()]
    result["complete"]=(p.returncode==0 and not result["missing_required"]
                        and sha(SCENE)==CORRECTED_SHA["H01"][2])
    if result["complete"]:
        sys.path[:0]=[str(ROOT/"scripts/research/n008_hdr_oracle"),
                      str(ROOT/"scripts/research/n007_reference_validity")]
        import n008lib as N008
        import check_convergence as N007
        native=json.loads(p.stdout)
        require(native.get("scene_sha256")==CORRECTED_SHA["H01"][2]
                and native.get("geometry_sha256")==GEOMETRY_SHA
                and native.get("spp")==16384 and native.get("seeds")==list(SEEDS)
                and native.get("triangles")==1224
                and native.get("width")==320 and native.get("height")==180,
                "wrong native oracle second-level physical inputs")
        for i,seed in enumerate(SEEDS):
            f=N008.read_sidecar(WORK/f"oracle.s{i}.f64")
            require((f["seed"],f["spp"],f["width"],f["height"])==
                    (seed,16384,320,180),"wrong second-level sidecar metadata")
        input_manifest={
            "schema_version":1,"source_commit":result["source_commit"],
            "scene_sha256":sha(SCENE),"frame_state_sha256":FRAME_SHA,
            "levels":[
                {"spp":8192,"references":[
                    {"seed":seed,"path":f"first-level-s{i}.total.pfm",
                     "sha256":sha(WORK/f"first-level-s{i}.total.pfm")}
                    for i,seed in enumerate(SEEDS)]},
                {"spp":16384,"references":[
                    {"seed":seed,"path":f"oracle.s{i}.total.pfm",
                     "sha256":sha(WORK/f"oracle.s{i}.total.pfm")}
                    for i,seed in enumerate(SEEDS)]}
            ]
        }
        (WORK/"two-level-input-manifest.json").write_text(json.dumps(input_manifest,indent=2)+"\n")
        N007.SPP=SCHEDULE
        screen=N007.assess(WORK/"two-level-input-manifest.json")
        require(screen.get("status") in ("incomplete","statistical-screen-pass")
                and screen.get("physical_correctness_proven") is False
                and len(screen.get("rows",[]))==2
                and screen["rows"][0]["eligible"] is True,
                "unexpected original N007 two-level assessment")
        (WORK/"two-level-screen.json").write_text(json.dumps(screen,indent=2)+"\n")
        result["n007_screen_status"]=screen["status"]
        result["n007_second_eligible"]=screen["rows"][1]["eligible"]
        result["n007_support_stable"]=screen["rows"][1].get("signal_support_stable_vs_previous")
        result["n007_eligible_at_spp"]=screen["eligible_at_spp"]
        result["classification"]=(
            "TWO_LEVEL_STATISTICAL_SCREEN_PASS_REFERENCE_ADMISSION_PENDING"
            if screen["status"]=="statistical-screen-pass" else
            "TWO_LEVEL_SCREEN_INCOMPLETE_RETAIN_FOR_NEXT_FROZEN_LEVEL"
        )
    else:
        result["classification"]="SECOND_CPU_LEVEL_FAILED_RETAIN_PARTIAL"
    receipt.write_text(json.dumps(result,indent=2)+"\n")
    archive=None
    if result["complete"]:
        ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
        with ARCHIVE.open("xb") as stream:
            with tarfile.open(fileobj=stream,mode="w") as t:
                for name in ("result.json","oracle.stdout.txt","oracle.stderr.txt",
                             "two-level-input-manifest.json","two-level-screen.json"):
                    t.add(WORK/name,arcname=name,recursive=False)
                t.add(PRIOR/"level1-screen.json",arcname="original-level1-screen.json",recursive=False)
                t.add(SOURCES/"manifest.json",arcname="corrected-sources-manifest.json",recursive=False)
        archive=str(ARCHIVE.relative_to(ROOT))
    print(json.dumps({
        "classification":result["classification"],"returncode":p.returncode,
        "n007_status":result.get("n007_screen_status"),
        "n007_eligible_at_spp":result.get("n007_eligible_at_spp"),
        "reference_eligible":False,
        "archive":archive,
        "next":"STOP: no third CPU level, other cell, GPU acquisition, scoring or timing"
    },indent=2))


if __name__=="__main__":
    run()
