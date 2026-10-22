#!/usr/bin/env python3
"""Freeze H01/H02/H03 physical T_B2/T_B8 inputs using N010's corrected camera.

CPU/metadata and source text only: does NOT run the oracle, acquire an image,
establish physical correctness/statistical eligibility, score GI or invoke GPU.
The old H01/H02 N008 camera hashes are retained as historical diagnostics but
MUST NOT serve as eligible Lane M reference input.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

from audit_h01_evidence import audit as audit_h01
from audit_h02_evidence import audit as audit_h02
from audit_h03_evidence import audit as audit_h03

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts/research/n008_hdr_oracle"))
sys.path.insert(0,str(ROOT/"scripts/research/n010_comparison_readiness"))
import n008lib as N008
from qualify_references import scene_for_state as n010_scene_for_state

CAPTURE_SHA={
    "H01":{"geometry":"f8b25b1c20ad84b6b9b030a2edd12c4a812af7199e21002897be9cf974ad75ca",
           "frame":"70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4"},
    "H02":{"geometry":"9d7c434202d2c9d14a7b3c4fb024b13cbd5240fc5251c22d3b533f719f968b5c",
           "frame":"70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4"},
    "H03":{"geometry":"6ef490de5bb43658aac6c83852316146971cbf6f80a7ffad36ef88649cfe98a3",
           "frame":"a2cc0b4a730971e78e857054490d0f53b7fe89e5f0c0e50628f0ebb6ebb0f225"},
}
F64_GEOMETRY_SHA={
    "H01":"fd6380ce0848e37d19f06c622f03dbbd76d0c900ff34b9195d2be155b4934966",
    "H02":"b40574ad76dbcc8f80250a0b1a1be0313176983b7140e96fdee18f4970ecb6e7",
    "H03":"e147373b109f5317ea75744b05705ca1df329a5b12fbdc37e9d1317faddb2b4c",
}
CORRECTED_SHA={
    "H01":{2:"047834e01eec9488bcf6a9c6cd6ed38aa28fad21e15363f353224df27c3eac4e",
           8:"7bd24d7acb70e78d414c87009a676f62eecb2ba0d1a3f92c1bcdc23ff6e12031"},
    "H02":{2:"5c400c4848ab3faff64fd2d241f31400e172d033a8a52b9ff944b71a5268ae0d",
           8:"289c2519dda077e079c0637c69f8690d5aec98c6685aa49bac9375a6bc7805a6"},
    "H03":{2:"b515c290cfeccde0a4b037262484a11ee4caaebe7a303e56df0ca944dd0acf54",
           8:"a9a8c88eac98fba728c189ab90180142a0e06d48e60f7001dd3d7999f8f1f847"},
}
SOURCE_LEN={"H01":142870,"H02":143266,"H03":145587}


def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def prepare(work:Path,output:Path)->dict:
    work,output=work.resolve(),output.resolve()
    if output.exists():
        raise ValueError("refuse existing physical state lock; never regenerate or overwrite")
    # On GPU-owner checkout all 13 original payloads are retained; their hashes
    # are verified before new physical input bytes become eligible for acquisition.
    h01=audit_h01(work,metadata_only=False)
    h02=audit_h02(work,metadata_only=False)
    h03=audit_h03(work,metadata_only=False)
    if h01["capture_payload_hashes_unverified"] or h02["capture_payloads_not_provided"] or h03["unverified_raw_payloads"]:
        raise ValueError("missing full H01/H02/H03 raw hash chain")
    sources=[]
    for name in ("H01","H02","H03"):
        capture=work/f"capture/M001-{name}-hwrt"
        st=N008.read_state(capture)
        if st["sha256"] != CAPTURE_SHA[name]:
            raise ValueError(name+": original frozen GPU state byte hashes differ")
        if (st["width"],st["height"],len(st["verts"])) != (320,180,1248 if name=="H03" else 1224):
            raise ValueError(name+": changed native geometry/viewport")
        if not (st["meta"][:,3]==1).all():
            raise ValueError(name+": not BF-P two-sided")
        for bounce in (2,8):
            scene=n010_scene_for_state(st,bounce)
            raw=scene.text().encode("utf-8")
            if (sha_bytes(raw)!=CORRECTED_SHA[name][bounce]
                    or len(raw)!=SOURCE_LEN[name]
                    or scene.geometry_sha256()!=F64_GEOMETRY_SHA[name]):
                raise ValueError(name+f"/T_B{bounce}: N010 corrected physical scene drift")
            sources.append((name,bounce,raw))
    manifest={
        "schema":"lane-m-m001-n010-camera-corrected-source-lock/1",
        "complete":True,"classification":"PHYSICAL_SOURCE_BYTES_LOCKED_REFERENCE_INELIGIBLE",
        "original_state_sha256":CAPTURE_SHA,
        "canonical_f64_geometry_sha256":F64_GEOMETRY_SHA,
        "n008lib_source_sha256":sha_bytes(Path(N008.__file__).read_bytes()),
        "n010_qualify_references_source_sha256":
            sha_bytes(ROOT.joinpath("scripts/research/n010_comparison_readiness/qualify_references.py").read_bytes()),
        "scene_rule":"N010 qualify_references.scene_for_state; corrected double-precision camera origin+forward",
        "transport_sources":[{
            "cell":name,"transport":f"T_B{bounce}","filename":f"M001-{name}-T_B{bounce}.n008",
            "sha256":CORRECTED_SHA[name][bounce],"bytes":len(raw),
            "max_bounces":bounce,"reference_eligible":False}
            for name,bounce,raw in sources],
        "acquisition_constraints":{
            "original_n010_four_seeds":[305419896,2596069104,81985529216486895,18364758544493064720],
            "original_prospective_levels":[8192,16384,32768,65536,131072,262144],
            "statistical_rule":"unchanged N007 four-seed two consecutive eligible levels and stable support; no R1 reuse without new preregistration",
            "reference_eligible":False,"quality_scored":False,
            "accepted_timing":False,"oracle_executed":False,"gpu_executed":False
        },
        "warning":"Not yet an independent, converged or physically admitted radiance reference. Historical N008 input hashes retained but superseded for new acquisition."
    }
    output.mkdir(parents=True)
    for name,bounce,raw in sources:
        (output/f"M001-{name}-T_B{bounce}.n008").write_bytes(raw)
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",
                                         encoding="utf-8")
    return manifest


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    report=prepare(args.work,args.output)
    print(json.dumps({"classification":report["classification"],
                      "sources":len(report["transport_sources"]),
                      "output":str(args.output),"reference_eligible":False},
                     indent=2))


if __name__=="__main__":
    main()
