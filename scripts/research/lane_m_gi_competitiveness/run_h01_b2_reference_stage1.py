#!/usr/bin/env python3
"""Run ONLY the first H01 T_B2 original N010 CPU RQMC level (8192 spp, four seeds).

This script never runs GPU, never runs another slot/level and never accepts a
reference from a single level. All full raw and failed outputs are retained.
It creates a compact owner attachment tar in repository out/ on success.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from prepare_m001_n010_physical_inputs import prepare, ROOT, CORRECTED_SHA

LANE=ROOT/"out/research/lane-m-gi-competitiveness/m001-first-heldout-v1"
SOURCES=ROOT/"out/research/lane-m-gi-competitiveness/m001-physical-inputs-n010-camera-v1"
WORK=ROOT/"out/research/lane-m-gi-competitiveness/m001-h01-b2-rqmc-first-level-v1"
ARCHIVE=ROOT/"out/m001-h01-b2-cpu-first-level.tar"
BINARY=ROOT/"build/n010-cpu/n010_rqmc_oracle"
NET=ROOT/"out/research/n010-comparison-readiness/sobol16x262144.bin"
VALIDATION=ROOT/"research/lanes/n010-comparison-readiness/results/009-iid-precision-confirmation.json"
LEVEL=8192
SEEDS=(305419896,2596069104,81985529216486895,18364758544493064720)
BINARY_SHA="cbe1186c0b8b15ebd2fcd19d081d61898b827fcea59d96ce5ba09c015407d0a5"
NET_SHA="e4020cf0c0e521d16dab5d4e0aa9860943aa6de843e558978ea544842a13a439"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition,label):
    if not condition:
        raise ValueError(label)

def quiet():
    proc=Path("/proc")
    require(proc.is_dir(),"cannot inspect concurrent CPU/GPU workers")
    seen=[]
    for item in proc.iterdir():
        if not item.name.isdigit() or item.name==str(os.getpid()):
            continue
        try:
            comm=(item/"comm").read_text().strip()
            command=(item/"cmdline").read_bytes().decode("utf-8","replace")
        except OSError:
            continue
        if (comm.startswith(("n010_","n008_oracle","phos-n010"))
            or any(n in command for n in ("qualify_references.py","qualify_incremental_references.py",
                                         "run_h01_b2_reference_stage1.py"))):
            seen.append(comm)
    require(not seen,"another reference or GPU producer active: "+str(seen))

def run():
    require(subprocess.check_output(["git","branch","--show-current"],cwd=ROOT,text=True).strip()
            =="research-lane-m-gi-competitiveness","wrong research branch")
    for path in (BINARY,NET,VALIDATION):
        require(path.is_file(),"missing original immutable N010 CPU input: "+str(path))
    require(sha(BINARY)==BINARY_SHA,"N010 original CPU oracle binary SHA differs")
    require(sha(NET)==NET_SHA,"N010 original Sobol net SHA differs")
    validation=json.loads(VALIDATION.read_text(encoding="utf-8"))
    require(validation.get("complete") is True and validation.get("all_pass") is True
            and validation.get("binary_sha256")==BINARY_SHA
            and validation.get("sobol_table_sha256")==NET_SHA,
            "N010 original physical/sampler proof missing or changed")
    require(not any(p.exists() for p in (WORK,SOURCES,ARCHIVE)),
            "refuse previous source/CPU result/archive; never overwrite or retry")
    require(shutil.disk_usage(ROOT).free>=8*1024**3,"need >=8GiB free for retained CPU evidence")
    quiet()
    # Full 13/13 local H01/H02/H03 payload verification before input source creation.
    source=prepare(LANE,SOURCES)
    target=SOURCES/"M001-H01-T_B2.n008"
    require(sha(target)==CORRECTED_SHA["H01"][2],
            "unexpected corrected N010 physical scene")
    WORK.mkdir(parents=True)
    prefix=WORK/"oracle"
    command=[str(BINARY),"--net",str(NET),"--scene",str(target),"--out",str(prefix),
             "--seeds",",".join(str(s) for s in SEEDS),"--spp",str(LEVEL)]
    info={
        "schema":"lane-m-m001-h01-b2-first-cpu-rqmc-level/1",
        "classification":"CPU_ORACLE_NOT_RUN", "complete":False,
        "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "source_sha256":sha(target), "source_manifest_sha256":sha(SOURCES/"manifest.json"),
        "validation_sha256":sha(VALIDATION),"binary_sha256":sha(BINARY),
        "sobol_table_sha256":sha(NET), "command":command,
        "fixed_scene":"H01", "fixed_transport":"T_B2","spp":LEVEL,"seeds":[str(s) for s in SEEDS],
        "reference_eligible":False, "accepted_timing":False, "gpu_executed":False
    }
    result=WORK/"result.json"
    result.write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    proc=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    (WORK/"oracle.stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (WORK/"oracle.stderr.txt").write_text(proc.stderr,encoding="utf-8")
    info["returncode"]=proc.returncode
    evidence={
       str(p.relative_to(WORK)):sha(p)
       for p in sorted(WORK.glob("oracle.*")) if p.is_file()
    }
    info["payload_sha256"]=evidence
    required=[f"oracle.s{i}.f64" for i in range(4)]+[
      f"oracle.s{i}.total.pfm" for i in range(4)]
    info["missing_required"]=[f for f in required if not (WORK/f).is_file()]
    info["complete"]=proc.returncode==0 and not info["missing_required"] and sha(target)==CORRECTED_SHA["H01"][2]
    if info["complete"]:
        sys.path.insert(0,str(ROOT/"scripts/research/n008_hdr_oracle"))
        sys.path.insert(0,str(ROOT/"scripts/research/n007_reference_validity"))
        import n008lib as N008
        import check_convergence as N007
        for i,seed in enumerate(SEEDS):
            row=N008.read_sidecar(WORK/f"oracle.s{i}.f64")
            require(row["seed"]==seed and row["spp"]==LEVEL
                    and row["width"]==320 and row["height"]==180,
                    "wrong original CPU oracle replicate identity")
        N007.SPP=(8192,16384,32768,65536,131072,262144)
        manifest={
          "schema_version":1, "source_commit":info["source_commit"],
          "scene_sha256":sha(target),
          "frame_state_sha256":source["original_state_sha256"]["H01"]["frame"],
          "levels":[{"spp":LEVEL,"references":[
              {"seed":seed,"path":f"oracle.s{i}.total.pfm",
               "sha256":sha(WORK/f"oracle.s{i}.total.pfm")}
              for i,seed in enumerate(SEEDS)]}]
        }
        (WORK/"level1-input-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        screen=N007.assess(WORK/"level1-input-manifest.json")
        require(screen["status"]=="incomplete" and
                screen["eligible_at_spp"] is None and
                screen["physical_correctness_proven"] is False,
                "single reference level cannot qualify")
        (WORK/"level1-screen.json").write_text(json.dumps(screen,indent=2)+"\n")
        info["original_n007_level1_screen_status"]=screen["status"]
    info["classification"]=(
      "CPU_H01_B2_FIRST_LEVEL_RETAINED_REFERENCE_INELIGIBLE"
      if info["complete"] else "CPU_H01_B2_FIRST_LEVEL_FAILED_RETAIN_PARTIAL"
    )
    result.write_text(json.dumps(info,indent=2)+"\n",encoding="utf-8")
    archive=None
    if info["complete"]:
        ARCHIVE.parent.mkdir(parents=True,exist_ok=True)
        with ARCHIVE.open("xb") as stream:
            with tarfile.open(fileobj=stream,mode="w") as tf:
                for name in ("result.json","oracle.stdout.txt","oracle.stderr.txt",
                             "level1-input-manifest.json","level1-screen.json"):
                    tf.add(WORK/name,arcname=name,recursive=False)
                tf.add(SOURCES/"manifest.json",arcname="corrected-sources-manifest.json",recursive=False)
        archive=str(ARCHIVE.relative_to(ROOT))
    print(json.dumps({"classification":info["classification"],"returncode":proc.returncode,
                     "raw_payload_count":len(evidence),"archive":archive,
                     "reference_eligible":False,
                     "next":"STOP: no other CPU level, GPU acquisition, HDR score or timing claim"},indent=2))

if __name__=="__main__":
    run()
