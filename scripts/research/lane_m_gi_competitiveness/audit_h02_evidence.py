#!/usr/bin/env python3
"""Offline H02 state/binary/owned-memory audit. Never reads HDR pixels or admits references."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from audit_h01_evidence import digest, check, geometry, frame, memory

H01_RECEIPT_SHA = "27e612439447bd1afd73f9346a679682c46eb0babe053883f17e9a53455a6cc0"
MANIFEST_SHA = "55e656caa352352fba160c1e02151f17237c116f37de2f2f0c2517893f25a707"
H01_GEOMETRY_SHA = "f8b25b1c20ad84b6b9b030a2edd12c4a812af7199e21002897be9cf974ad75ca"
H01_FRAME_SHA = "70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4"
H02_GLTF_SHA = "25a6ba40cb1f6065284b5da5bc979e33562cf65f913bf6808e35b38782eb6747"
H02_BIN_SHA = "fd2c7e09c7da2ff0f6760dc09c09c524586e2126328a26666dd98d35640ef94b"
H02 = Path("capture/M001-H02-hwrt")
REQUIRED = ("geometry-state.bin", "frame-state.bin", "capture.json", "allocation-ledger.json",
            "gpu/direct.pfm", "gpu/indirect.pfm", "gpu/total.pfm")


def expand_gltf(path: Path, binary_path: Path) -> list[bytes]:
    """Decode the unchanged N004 POSITION/index meshes in scene order, byte-exact float32."""
    gltf = json.loads(path.read_text(encoding="utf-8"))
    data = binary_path.read_bytes()
    check(len(gltf["buffers"]) == 1 and gltf["buffers"][0]["uri"] == binary_path.name
          and gltf["buffers"][0]["byteLength"] == len(data), "unexpected glTF buffer")
    check(len(gltf["scenes"]) == 1 and gltf["scene"] == 0, "unexpected glTF scene")
    views, accessors = gltf["bufferViews"], gltf["accessors"]

    def accessor(index: int, kind: str) -> list[tuple]:
        row = accessors[index]
        component, type_, fmt, size = ((5126, "VEC3", "<3f", 12)
                                       if kind == "position" else (5125, "SCALAR", "<I", 4))
        check(row["componentType"] == component and row["type"] == type_
              and "sparse" not in row, "unexpected accessor type")
        view = views[row["bufferView"]]
        start = view.get("byteOffset", 0) + row.get("byteOffset", 0)
        stride = view.get("byteStride", size)
        count = row["count"]
        check(view["buffer"] == 0 and stride >= size and stride % 4 == 0
              and type(count) is int and count > 0
              and start >= 0 and start + (count - 1) * stride + size <= len(data),
              "invalid glTF buffer bounds")
        return [struct.unpack_from(fmt, data, start + k * stride) for k in range(count)]

    triangles = []
    for nid in gltf["scenes"][0]["nodes"]:
        node = gltf["nodes"][nid]
        check(set(node) == {"mesh"}, "unregistered glTF transform or instancing")
        for prim in gltf["meshes"][node["mesh"]]["primitives"]:
            check(prim.get("mode", 4) == 4 and set(prim["attributes"]) == {"POSITION"},
                  "unexpected glTF primitive")
            pos = accessor(prim["attributes"]["POSITION"], "position")
            ids = [v[0] for v in accessor(prim["indices"], "index")]
            check(len(ids) % 3 == 0 and max(ids) < len(pos), "out-of-range triangle index")
            for k in range(0, len(ids), 3):
                triangles.append(b"".join(struct.pack("<3f", *pos[j]) for j in ids[k:k+3]))
    return triangles


def audit(work: Path, *, metadata_only: bool = False) -> dict:
    work = work.resolve()
    result = json.loads((work / "result-h02.json").read_text(encoding="utf-8"))
    check(result.get("schema") == "lane-m-m001-h02-first-capture/1"
          and result.get("classification") == "H02_RAW_STATE_CAPTURE_RETAINED_UNQUALIFIED"
          and result.get("returncode") == 0 and result.get("complete") is True
          and result.get("inputs_unchanged") is True and result.get("missing_required") == []
          and result.get("reference_eligible") is False and result.get("accepted_timing") is False,
          "H02 not a complete yet-unqualified GPU state capture")
    check(result.get("h01_receipt_sha256") == H01_RECEIPT_SHA
          and digest(work / "result.json") == H01_RECEIPT_SHA
          and result.get("h01_geometry_sha256") == H01_GEOMETRY_SHA
          and result.get("h01_frame_sha256") == H01_FRAME_SHA,
          "H02 not bound to original H01 provenance")
    check(digest(work / "assets/manifest.json") == MANIFEST_SHA, "changed preregistration")
    manifest = json.loads((work / "assets/manifest.json").read_text(encoding="utf-8"))
    check(manifest.get("complete") is True and len(manifest.get("scenes", [])) == 3,
          "wrong locked scene manifest")
    scene = manifest["scenes"][1]
    check(result.get("scene") == scene
          and (scene.get("name"), scene.get("kind"), scene.get("wall_thickness_world"),
               scene.get("triangle_count")) == ("M001-H02", "grazing", 0.163, 1224)
          and scene.get("eligible_reference") is False and scene.get("gpu_state_frozen") is False,
          "H02 scene differs from preregistration")
    gltf, binary = work / "assets/M001-H02.gltf", work / "assets/M001-H02.bin"
    check(digest(gltf) == H02_GLTF_SHA == scene["gltf_sha256"]
          and digest(binary) == H02_BIN_SHA == scene["bin_sha256"],
          "H02 glTF or BIN drift")
    command = result.get("command", [])
    check(type(command) is list and all(type(x) is str for x in command), "bad native command")
    for opt, expected in (("--scenario", "static"), ("--backend", "hwrt"),
                          ("--direct-profile", "ulp4")):
        check(command.count(opt) == 1 and command[command.index(opt)+1] == expected,
              "changed native option " + opt)
    for opt, expected in (("--scene", "M001-H02.gltf"), ("--out", "M001-H02-hwrt")):
        check(command.count(opt) == 1 and Path(command[command.index(opt)+1]).name == expected,
              "changed output/scene " + opt)
    payloads = result.get("payload_sha256")
    check(type(payloads) is dict and len(payloads) == 13 and set(REQUIRED).issubset(payloads),
          "missing H02 capture payload inventory")
    checked, missing = [], []
    for rel, expected in payloads.items():
        check(type(rel) is str and type(expected) is str and len(expected) == 64
              and not Path(rel).is_absolute() and ".." not in Path(rel).parts,
              "unsafe capture payload")
        target = (work / H02 / rel).resolve()
        check(target.is_relative_to(work / H02), "payload path escaped work root")
        if target.is_file():
            check(digest(target) == expected, "raw capture payload SHA drift: " + rel)
            checked.append(rel)
        else:
            check(metadata_only and rel not in {"geometry-state.bin", "frame-state.bin",
                                                "capture.json", "allocation-ledger.json"},
                  "required/raw capture file missing: " + rel)
            missing.append(rel)
    meta = json.loads((work / H02 / "capture.json").read_text(encoding="utf-8"))
    check(meta.get("schema_version") == 1 and meta.get("scenario") == "static"
          and meta.get("backend") == "hwrt" and meta.get("target_state") is False
          and meta.get("frame_id") == 1 and meta.get("spp") == 512
          and meta.get("triangles") == 1224 and meta.get("work_overflow") == 0
          and type(meta.get("work_items")) is int and meta["work_items"] > 0,
          "incorrect H02 Vulkan native metadata")
    geom_path = work / H02 / "geometry-state.bin"
    geom = geometry(geom_path)
    data = geom_path.read_bytes()
    captured = [data[8+52*i:8+52*i+36] for i in range(1224)]
    gltf_expanded = expand_gltf(gltf, binary)
    check(captured == gltf_expanded, "H02 glTF ordered triangles differ from captured GPU state")
    frm = frame(work / H02 / "frame-state.bin")
    check([meta["width"], meta["height"]] == frm["resolution"], "frame size mismatch")
    owned = memory(json.loads((work / H02 / "allocation-ledger.json").read_text(encoding="utf-8")))
    return {
        "schema": "lane-m-m001-h02-state-input-audit/1",
        "classification": ("STATE_INPUTS_CONSISTENT_FULL_PAYLOAD_NOT_VERIFIED" if missing
                           else "STATE_EVIDENCE_CONSISTENT_REFERENCE_NOT_YET_ELIGIBLE"),
        "capture_source_commit": result.get("source_commit"),
        "complete_metadata_audit": True,
        "h01_receipt_sha256": H01_RECEIPT_SHA,
        "h02_receipt_sha256": digest(work / "result-h02.json"),
        "frozen_manifest_sha256": MANIFEST_SHA,
        "h02_geometry": geom, "h02_frame": frm, "h02_owned_memory": owned,
        "glTF_ordered_triangles_matched": len(captured),
        "capture_payloads_hash_verified": sorted(checked),
        "capture_payloads_not_provided": sorted(missing),
        "reference_eligible": False, "quality_scored": False,
        "accepted_timing": False, "gpu_executed_by_auditor": False
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--metadata-only", action="store_true")
    args = ap.parse_args()
    check(not args.output.exists(), "refuse to overwrite previous audit")
    info = audit(args.work, metadata_only=args.metadata_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "classification": info["classification"],
        "geometry_sha256": info["h02_geometry"]["geometry_sha256"],
        "frame_sha256": info["h02_frame"]["frame_sha256"],
        "owned_peak_bytes": info["h02_owned_memory"]["true_peak_owned_bytes"],
        "hashes_checked": len(info["capture_payloads_hash_verified"]),
        "hashes_unverified": len(info["capture_payloads_not_provided"]),
        "reference_eligible": False}, indent=2))


if __name__ == "__main__":
    main()
