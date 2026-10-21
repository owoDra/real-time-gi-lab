#!/usr/bin/env python3
"""M001 H01: offline CPU state-evidence audit. Does not read HDR pixel values."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

CAPTURE_SOURCE = "948d38c339190340b9e3f91f8ec0347b3b4a0109"
CAPTURE = Path("capture/M001-H01-hwrt")
NEEDED = ("geometry-state.bin", "frame-state.bin", "capture.json",
          "gpu/direct.pfm", "gpu/indirect.pfm", "gpu/total.pfm",
          "allocation-ledger.json")
SCENES = (
    ("M001-H01", "medium", 0.137, 1224),
    ("M001-H02", "grazing", 0.163, 1224),
    ("M001-H03", "enclosed", 0.127, 1248),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(truth, reason: str) -> None:
    if not truth:
        raise ValueError(reason)


def geometry(path: Path) -> dict:
    raw = path.read_bytes()
    check(len(raw) >= 8, "short geometry")
    version, count = struct.unpack_from("<2I", raw)
    check(version == 1 and count == 1224 and len(raw) == 8 + 52 * count,
          "geometry version, triangle count or byte count differs")
    primitive_ids = set()
    for index in range(count):
        offset = 8 + 52 * index
        vertices = struct.unpack_from("<9f", raw, offset)
        meta = struct.unpack_from("<4I", raw, offset + 36)
        check(all(map(math.isfinite, vertices)), "nonfinite vertex")
        check(meta[3] == 1, "not BF-P two-sided geometry")
        primitive_ids.add(meta[0])
    return {"triangles": count, "two_sided": True,
            "unique_primitive_ids": len(primitive_ids), "geometry_sha256": digest(path)}


def frame(path: Path) -> dict:
    raw = path.read_bytes()
    check(len(raw) == 148 and raw[:12] == b"N007-STATE1\0", "frame header/size differs")
    w, h = struct.unpack_from("<2I", raw, 12)
    check((w, h) == (320, 180), "frame resolution differs")
    p = struct.unpack_from("<32f", raw, 20)
    check(all(map(math.isfinite, p)), "nonfinite frame uniform")
    names = ("camera_pos_near", "camera_right_tan_x", "camera_up_tan_y",
             "camera_forward_far", "scene_origin_spacing", "light_pos_interval")
    return {"frame_sha256": digest(path), "resolution": [w, h],
            "ubo": {name: list(p[i*4:i*4+4]) for i, name in enumerate(names)}}


def memory(ledger: dict) -> dict:
    live, peak = {}, 0
    check(type(ledger.get("events")) is list, "memory events missing")
    for event in ledger["events"]:
        key = (event.get("device_context"), event.get("allocation_id"))
        amount = event.get("bytes")
        check(type(amount) is int and amount >= 0, "invalid allocation size")
        if event.get("action") == "allocate":
            check(key not in live, "duplicate allocation")
            live[key] = amount
        elif event.get("action") == "free":
            check(key in live and live[key] == amount, "unmatched free")
            del live[key]
        else:
            raise ValueError("unexpected memory event")
        active = sum(live.values())
        check(active == event.get("live_bytes"), "inconsistent memory sum")
        peak = max(peak, active)
    check(not live and ledger.get("teardown_zero") is True, "teardown is nonzero")
    check(ledger.get("true_peak_owned_bytes") == peak and peak <= 8 * 1024**3,
          "owned peak differs or exceeds limit")
    return {"events": len(ledger["events"]), "true_peak_owned_bytes": peak,
            "teardown_zero": True}


def audit(work: Path) -> dict:
    work = work.resolve()
    receipt = json.loads((work / "result.json").read_text())
    check(receipt.get("schema") == "lane-m-m001-first-capture/1", "unexpected receipt")
    check(receipt.get("preflight", {}).get("source_commit") == CAPTURE_SOURCE,
          "unexpected native capture source version")
    check(receipt.get("fixed_first_scene") == "M001-H01" and receipt.get("returncode") == 0
          and receipt.get("complete") is True
          and receipt.get("classification") == "RAW_H01_GPU_CAPTURE_RETAINED_UNQUALIFIED",
          "H01 native is not complete")
    check(receipt.get("reference_eligible") is False and receipt.get("state_locked") is False
          and receipt.get("accepted_timing") is False, "raw capture falsely admitted")
    check(receipt.get("missing_capture_files") == []
          and receipt.get("required_capture_files") == list(NEEDED),
          "H01 native required-file checks differ")
    command = receipt.get("command", [])
    check(type(command) is list and all(type(x) is str for x in command),
          "invalid native command")
    for arg, expected in (("--scenario", "static"), ("--backend", "hwrt"),
                          ("--direct-profile", "ulp4")):
        check(command.count(arg) == 1 and command[command.index(arg) + 1] == expected,
              "changed native option: " + arg)
    for arg, name in (("--scene", "M001-H01.gltf"), ("--out", "M001-H01-hwrt")):
        check(command.count(arg) == 1 and
              Path(command[command.index(arg) + 1]).name == name, "changed " + arg)
    manifest = json.loads((work / "assets/manifest.json").read_text())
    check(manifest.get("schema") == "lane-m-m001-heldout-geometry/1"
          and manifest.get("complete") is True, "invalid geometry manifest")
    check(digest(work / "assets/manifest.json") == receipt.get("geometry_manifest_sha256"),
          "geometry manifest has changed")
    check(manifest.get("factory_sha256") == receipt["preflight"].get("n004_source_sha256"),
          "frozen scene-generator SHA mismatch")
    check(len(manifest.get("scenes", [])) == 3, "missing preregistered scenes")
    for row, (name, kind, thickness, triangles) in zip(manifest["scenes"], SCENES):
        check((row.get("name"), row.get("kind"), row.get("wall_thickness_world"),
               row.get("triangle_count")) == (name, kind, thickness, triangles),
              "changed preregistered scene recipe")
        check(row.get("eligible_reference") is False and
              row.get("gpu_state_frozen") is False, "geometry self-admitted")
        for ext in ("gltf", "bin"):
            filename = name + "." + ext
            check(row.get(ext) == filename and
                  digest(work / "assets" / filename) == row.get(ext + "_sha256"),
                  "scene asset drift: " + filename)
    payloads = receipt.get("payload_sha256")
    check(type(payloads) is dict and len(payloads) == 13, "unexpected payload inventory")
    for rel, expected in payloads.items():
        check(type(rel) is str and rel.startswith(CAPTURE.as_posix() + "/")
              and type(expected) is str and len(expected) == 64,
              "invalid payload entry")
        source = (work / rel).resolve()
        check(source.is_relative_to(work) and source.is_file(), "missing/unsafe payload")
        check(digest(source) == expected, "changed captured payload: " + rel)
    for file in NEEDED:
        check((CAPTURE / file).as_posix() in payloads, "missing pinned file " + file)
    meta = json.loads((work / CAPTURE / "capture.json").read_text())
    check(meta.get("schema_version") == 1 and meta.get("scenario") == "static"
          and meta.get("backend") == "hwrt" and meta.get("target_state") is False
          and meta.get("frame_id") == 1 and meta.get("work_overflow") == 0
          and meta.get("triangles") == 1224, "unexpected GPU capture contract")
    g, f = geometry(work / CAPTURE / "geometry-state.bin"), frame(work / CAPTURE / "frame-state.bin")
    check([meta.get("width"), meta.get("height")] == f["resolution"], "capture/frame mismatch")
    m = memory(json.loads((work / CAPTURE / "allocation-ledger.json").read_text()))
    return {"schema": "lane-m-m001-h01-state-audit/1", "complete": True,
            "classification": "STATE_EVIDENCE_CONSISTENT_REFERENCE_NOT_YET_ELIGIBLE",
            "capture_source_commit": CAPTURE_SOURCE, "geometry": g, "frame": f,
            "allocation": m, "input_sha256": {
                "result": digest(work / "result.json"),
                "geometry_manifest": digest(work / "assets/manifest.json"),
                "capture_json": digest(work / CAPTURE / "capture.json")},
            "capture_payload_hashes_checked": len(payloads),
            "reference_eligible": False, "accepted_timing": False, "gpu_run": False,
            "scope": "Full payload SHA checks including HDR byte hashes. No HDR pixels read, reference scored, or GPU work."}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    check(not args.output.exists(), "refuse overwriting result")
    result = audit(args.work)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"classification": result["classification"],
                      "geometry_sha256": result["geometry"]["geometry_sha256"],
                      "frame_sha256": result["frame"]["frame_sha256"],
                      "true_peak_owned_bytes": result["allocation"]["true_peak_owned_bytes"],
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
