#!/usr/bin/env python3
"""H03 state-only offline integrity audit; no HDR read, oracle/physics admission or GPU.

Strict mode can rehash all locally retained native payloads; --metadata-only
validates a compact private attachment and explicitly lists absent raw payloads.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import struct
from audit_h01_evidence import check, digest, frame, memory
from audit_h02_evidence import expand_gltf

H01_RECEIPT_SHA = "27e612439447bd1afd73f9346a679682c46eb0babe053883f17e9a53455a6cc0"
H02_RECEIPT_SHA = "5562656fad898b07ac91903affd7d0f00423b1813f2a59dc67941fc22e23f765"
H03_RECEIPT_SHA = "faad4ca5f966294834d67ee137761b822daee8a8cf9d31a45b4402572dddebff"
MANIFEST_SHA = "55e656caa352352fba160c1e02151f17237c116f37de2f2f0c2517893f25a707"
SOURCE_COMMIT = "eed40f6b80a987c4ff8c87ad1680b12fd69ee4b0"
GEOMETRY_SHA = "6ef490de5bb43658aac6c83852316146971cbf6f80a7ffad36ef88649cfe98a3"
FRAME_SHA = "a2cc0b4a730971e78e857054490d0f53b7fe89e5f0c0e50628f0ebb6ebb0f225"
GLTF_SHA = "23b1a96560c405dfc645f8de51afef4fb4cbdca4e06d75ee32097bde034c9424"
BIN_SHA = "bab24715916c2a62a02f55aab4a9d0c1f43ca860600cb0529ca70e8b41d643f4"
CAPTURE = Path("capture/M001-H03-hwrt")
NEEDED = ("geometry-state.bin", "frame-state.bin", "capture.json", "allocation-ledger.json",
          "gpu/direct.pfm", "gpu/indirect.pfm", "gpu/total.pfm")
SOURCE_INPUTS = {
    "scripts/research/lane_n_end_to_end_renderer/n004_scene_factory.py":
        "cd92c0db431be03b4fe07ed3db4f21aff43d35f44b0d6c821b7d9102297b76f9",
    "build/n009/phos-n010-capture":
        "cc6d7802a45d68d5074a13bbdd5c2cc94310d2f7fa5c303ee890508dae7535ab",
    "out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract":
        "36b1516126b402d72c0bcd02bdce22a1bd5510ca8ea83ddc2437c7fedd58f864",
    "scripts/run_with_vulkan.sh":
        "9b39625714adbbf636888946ab3e4424e67ceae5c49450a6b83f6990c0451b4a",
    "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1/assets/M001-H03.gltf":
        GLTF_SHA,
    "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1/assets/M001-H03.bin":
        BIN_SHA,
}


def audit(work: Path, *, metadata_only: bool = False) -> dict:
    work = work.resolve()
    check(digest(work / "result.json") == H01_RECEIPT_SHA, "H01 original receipt changed")
    check(digest(work / "result-h02.json") == H02_RECEIPT_SHA, "H02 original receipt changed")
    check(digest(work / "result-h03.json") == H03_RECEIPT_SHA, "H03 original receipt changed")
    receipt = json.loads((work / "result-h03.json").read_text(encoding="utf-8"))
    check(receipt.get("schema") == "lane-m-m001-h03-first-capture/1"
          and receipt.get("classification") == "H03_RAW_STATE_CAPTURE_RETAINED_UNQUALIFIED"
          and receipt.get("source_commit") == SOURCE_COMMIT
          and receipt.get("complete") is True and receipt.get("returncode") == 0
          and receipt.get("inputs_unchanged") is True
          and receipt.get("missing_required") == []
          and receipt.get("h02_receipt_sha256") == H02_RECEIPT_SHA
          and receipt.get("manifest_sha256") == MANIFEST_SHA,
          "wrong H03 source, lineage or incomplete receipt")
    check(receipt.get("reference_eligible") is False
          and receipt.get("accepted_timing") is False
          and receipt.get("state_locked") is False
          and receipt.get("quality_scored") is False, "raw capture prematurely admitted")
    pre = receipt.get("preflight", {})
    check(pre.get("h01_payload_count_rechecked") == 13
          and pre.get("h02_payload_count_rechecked") == 13
          and pre.get("h01_state_input_audit") ==
          "STATE_EVIDENCE_CONSISTENT_REFERENCE_NOT_YET_ELIGIBLE"
          and pre.get("h02_state_input_audit") ==
          "STATE_EVIDENCE_CONSISTENT_REFERENCE_NOT_YET_ELIGIBLE",
          "host preflight did not fully verify preceding two captures")
    check(receipt.get("source_input_sha256") == SOURCE_INPUTS, "changed captured native input chain")
    check(digest(work / "assets/manifest.json") == MANIFEST_SHA,
          "H01-H03 pre-registered manifest changed")
    manifest = json.loads((work / "assets/manifest.json").read_text(encoding="utf-8"))
    check(manifest.get("schema") == "lane-m-m001-heldout-geometry/1"
          and manifest.get("complete") is True and len(manifest.get("scenes", [])) == 3,
          "invalid original three-scene manifest")
    row = manifest["scenes"][2]
    check(row == receipt.get("scene") and
          (row.get("name"), row.get("kind"), row.get("wall_thickness_world"),
           row.get("triangle_count")) == ("M001-H03", "enclosed", 0.127, 1248)
          and row.get("eligible_reference") is False and row.get("gpu_state_frozen") is False,
          "unregistered or prematurely admitted H03 scene")
    gltf = work / "assets/M001-H03.gltf"
    binary = work / "assets/M001-H03.bin"
    check(digest(gltf) == GLTF_SHA == row["gltf_sha256"]
          and digest(binary) == BIN_SHA == row["bin_sha256"], "H03 geometry input bytes changed")
    command = receipt.get("command", [])
    check(type(command) is list and all(type(x) is str for x in command),
          "invalid native capture command")
    for arg, expected in (("--scenario", "static"), ("--backend", "hwrt"),
                          ("--direct-profile", "ulp4")):
        check(command.count(arg) == 1 and command[command.index(arg)+1] == expected,
              "changed command option " + arg)
    for arg, expected in (("--scene", "M001-H03.gltf"), ("--out", "M001-H03-hwrt")):
        check(command.count(arg) == 1 and
              Path(command[command.index(arg)+1]).name == expected, "unexpected " + arg)
    entries = receipt.get("payload_sha256")
    check(type(entries) is dict and len(entries) == 13 and set(NEEDED).issubset(entries),
          "expected 13 native payload hash entries")
    verified, deferred = [], []
    for name, expected in entries.items():
        check(type(name) is str and name and not Path(name).is_absolute()
              and ".." not in Path(name).parts and type(expected) is str and
              len(expected) == 64 and all(ch in "0123456789abcdef" for ch in expected),
              "unsafe or invalid payload entry")
        path = (work / CAPTURE / name).resolve()
        check(path.is_relative_to(work / CAPTURE), "payload escaped native root")
        if path.is_file():
            check(digest(path) == expected, "native payload SHA differs: " + name)
            verified.append(name)
        else:
            check(metadata_only and name not in
                  ("geometry-state.bin", "frame-state.bin", "capture.json",
                   "allocation-ledger.json"),
                  "required native payload missing: " + name)
            deferred.append(name)
    cap = json.loads((work / CAPTURE / "capture.json").read_text(encoding="utf-8"))
    check(cap == {"schema_version":1, "scenario":"static", "backend":"hwrt",
                  "target_state":False, "frame_id":1, "spp":512, "width":320,
                  "height":180, "triangles":1248, "work_items":37664,
                  "work_overflow":0}, "unexpected static Vulkan capture metadata")
    gpath = work / CAPTURE / "geometry-state.bin"
    raw = gpath.read_bytes()
    check(digest(gpath) == GEOMETRY_SHA
          and len(raw) == 8+52*1248 and struct.unpack_from("<2I",raw) == (1,1248),
          "H03 captured geometry binary contract differs")
    vertices = []
    ids = []
    materials, instances, sides = set(), set(), set()
    for k in range(1248):
        off = 8 + k*52
        v = struct.unpack_from("<9f",raw,off)
        primitive, material, instance, two_sided = struct.unpack_from("<4I",raw,off+36)
        check(all(map(math.isfinite,v)), "non-finite primitive vertices")
        av=[v[i]-v[i+3] for i in range(3)]
        bv=[v[i]-v[i+6] for i in range(3)]
        cross=(av[1]*bv[2]-av[2]*bv[1],av[2]*bv[0]-av[0]*bv[2],av[0]*bv[1]-av[1]*bv[0])
        check(sum(c*c for c in cross)>1e-16,"degenerate primitive")
        vertices.append(raw[off:off+36]);ids.append(primitive)
        materials.add(material);instances.add(instance);sides.add(two_sided)
    check(len(set(ids)) == 1248 and materials == {0xffffffff} and sides == {1},
          "unexpected primitive/sidedness/material ABI")
    expected = expand_gltf(gltf,binary)
    check(len(expected) == 1248 and expected == vertices, "glTF and GPU differ in triangle order")
    fpath = work / CAPTURE / "frame-state.bin"
    check(digest(fpath) == FRAME_SHA, "H03 frame state bytes changed")
    frm = frame(fpath)
    check(frm["resolution"] == [320,180], "wrong H03 frame resolution")
    ledger_path = work / CAPTURE / "allocation-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    allocation = memory(ledger)
    check(ledger.get("live_bytes_at_teardown") == 0
          and allocation["true_peak_owned_bytes"] == 266947072
          and allocation["events"] == 74, "owned memory lifecycle changed")
    return {
        "schema":"lane-m-m001-h03-state-evidence/1",
        "complete":True,
        "classification":("H03_STATE_INPUTS_INTEGRITY_PASS_RAW_GPU_PAYLOADS_UNVERIFIED"
                          if deferred else "H03_STATE_AND_ALL_RAW_PAYLOAD_HASHES_PASS_REFERENCE_UNQUALIFIED"),
        "captured_state_sha256":{"geometry":GEOMETRY_SHA,"frame":FRAME_SHA},
        "triangle_count":1248,"gltf_ordered_triangle_match":1248,
        "all_two_sided":True, "owned_memory":allocation,
        "verified_raw_payloads":sorted(verified),
        "unverified_raw_payloads":sorted(deferred),
        "reference_eligible":False, "hdr_quality_scored":False,
        "accepted_timing":False, "gpu_executed":False,
        "physical_reference_eligibility":"NOT_RUN"
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--metadata-only",action="store_true")
    opts=parser.parse_args()
    check(not opts.output.exists(),"refuse existing audit output")
    report=audit(opts.work,metadata_only=opts.metadata_only)
    opts.output.parent.mkdir(parents=True,exist_ok=True)
    opts.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"classification":report["classification"],
                      "verified":len(report["verified_raw_payloads"]),
                      "unverified":len(report["unverified_raw_payloads"]),
                      "reference_eligible":False},indent=2))


if __name__ == "__main__":
    main()
