#!/usr/bin/env python3
"""H01/T_B2 reference admission from original full 8192+16384 CPU evidence, no sampling.

Rehash all retained original oracle outputs, replay the original N007 screen
over raw full-image PFMs, materialize an immutable canonical original-full-prefix
N010 reference view, then invoke the *unchanged* N010 reference_provenance
physical_proof + verify_reference. Stop on any mismatch, never reuse R1.

No GPU, no oracle sampling, no HDR candidate scoring, no timing. A successful
attestation only qualifies this one H01/T_B2 reference, not other scenes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from audit_h01_evidence import audit as audit_h01
from run_h01_b2_reference_stage2 import (
    ROOT, PRIOR, WORK as SECOND, SOURCES, SCENE, SEEDS, SCHEDULE,
    BINARY, NET, VALIDATION, BINARY_SHA, NET_SHA, VALIDATION_SHA,
    FIRST_SHA, FIRST_SCREEN_SHA, SOURCE_MANIFEST_SHA, GEOMETRY_SHA,
    FRAME_SHA, frozen_first, quiet, sha, require,
)
from prepare_m001_n010_physical_inputs import CORRECTED_SHA

sys.path[:0] = [
    str(ROOT / "scripts/research/n010_comparison_readiness"),
    str(ROOT / "scripts/research/n008_hdr_oracle"),
    str(ROOT / "scripts/research/n007_reference_validity"),
]
import qualify_references as Q
import reference_provenance as P
import check_convergence as N007

LANE = ROOT / "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1"
DEST = ROOT / "out/research/lane-m-gi-competitiveness/m001-h01-b2-original-admitted-reference-v1"
ARCHIVE = ROOT / "out/m001-h01-b2-reference-admission.tar"
SECOND_SHA = "4c520b32278b87d8b89b0aecac2d42fc8e34e92f3b357d00f15a82e1b965ee00"
TWO_SCREEN_SHA = "7d49e60664fa9f9a3ab976d28d0d3567ffac865e82cb07587a925c99e301b48f"
TWO_INPUT_SHA = "857e21fcc14df1f24bf34313c8fc74278e735823e020e5ec2b3546d8863d0fac"
SOURCE_SHA = CORRECTED_SHA["H01"][2]
SUFFIXES = ("f64", "emission.pfm", "direct.pfm", "indirect.pfm", "total.pfm")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def replay_inputs() -> tuple[dict, dict, dict]:
    require(subprocess.check_output(["git", "branch", "--show-current"],
                                    cwd=ROOT, text=True).strip()
            == "research-lane-m-gi-competitiveness", "wrong research branch")
    require(not DEST.exists() and not ARCHIVE.exists(),
            "refuse existing admitted reference or archive: no overwrite/retry")
    quiet()
    h01 = audit_h01(LANE, metadata_only=False)
    require(h01["capture_payload_hashes_checked"] == 13 and
            not h01["capture_payload_hashes_unverified"],
            "H01 GPU source-state raw hash proof incomplete")
    first = frozen_first()  # all 23 8192 spp native files independently rehashed
    require(sha(SECOND / "result.json") == SECOND_SHA and
            sha(SECOND / "two-level-screen.json") == TWO_SCREEN_SHA and
            sha(SECOND / "two-level-input-manifest.json") == TWO_INPUT_SHA,
            "H01 B2 second-level original receipt/screen/manifest drift")
    result = read(SECOND / "result.json")
    screen = read(SECOND / "two-level-screen.json")
    manifest = read(SECOND / "two-level-input-manifest.json")
    require(result.get("classification") ==
            "TWO_LEVEL_STATISTICAL_SCREEN_PASS_REFERENCE_ADMISSION_PENDING"
            and result.get("complete") is True and result.get("returncode") == 0
            and result.get("reference_eligible") is False and
            result.get("quality_scored") is False and
            result.get("accepted_timing") is False
            and result.get("original_8192_result_sha256") == FIRST_SHA
            and result.get("original_8192_screen_sha256") == FIRST_SCREEN_SHA
            and result.get("first_level_payload_hashes_verified") == 23
            and result.get("physical_source_sha256") == SOURCE_SHA
            and result.get("physical_manifest_sha256") == SOURCE_MANIFEST_SHA
            and result.get("validation_sha256") == VALIDATION_SHA
            and result.get("binary_sha256") == BINARY_SHA
            and result.get("net_sha256") == NET_SHA
            and result.get("scene") == "H01" and result.get("transport") == "T_B2"
            and result.get("spp") == 16384 and
            result.get("seeds") == list(map(str, SEEDS)),
            "original 16384 RQMC contract changed")
    require([x["spp"] for x in manifest.get("levels", [])] == [8192, 16384] and
            len(screen.get("rows", [])) == 2 and
            screen.get("status") == "statistical-screen-pass" and
            screen.get("eligible_at_spp") == 16384 and
            screen.get("physical_correctness_proven") is False and
            all(x["eligible"] and not x["problems"] for x in screen["rows"]) and
            screen["rows"][1]["signal_support_stable_vs_previous"] is True,
            "original N007 two-consecutive eligible screen is not PASS")
    require(screen["manifest_sha256"] == sha(SECOND / "two-level-input-manifest.json")
            and screen["scene_sha256"] == SOURCE_SHA and
            screen["frame_state_sha256"] == FRAME_SHA and
            manifest["scene_sha256"] == SOURCE_SHA and
            manifest["frame_state_sha256"] == FRAME_SHA,
            "original two-level frozen source or screen mismatch")
    require(sha(SCENE) == SOURCE_SHA and
            sha(SOURCES / "manifest.json") == SOURCE_MANIFEST_SHA and
            sha(BINARY) == BINARY_SHA and sha(NET) == NET_SHA and
            sha(VALIDATION) == VALIDATION_SHA,
            "original sampler/oracle/physical source bytes changed")
    hashes = result.get("payload_sha256", {})
    require(type(hashes) is dict and len(hashes) == 23,
            "second-level 23 native raw entries missing")
    for name, expected in hashes.items():
        path = (SECOND / name).resolve()
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and
                path.is_relative_to(SECOND) and path.is_file() and sha(path) == expected,
                "16384 native file altered: " + name)
    # Ensure the stage2 checker really operated on byte-identical original level1 PFMs.
    for i, seed in enumerate(SEEDS):
        old = PRIOR / f"oracle.s{i}.total.pfm"
        copied = SECOND / f"first-level-s{i}.total.pfm"
        require(sha(copied) == sha(old) ==
                first["payload_sha256"][old.name] ==
                manifest["levels"][0]["references"][i]["sha256"],
                "8192 copied PFM original identity mismatch")
        fresh = SECOND / f"oracle.s{i}.total.pfm"
        require(sha(fresh) == hashes[fresh.name] ==
                manifest["levels"][1]["references"][i]["sha256"],
                "16384 PFM original identity mismatch")
        require(all(manifest["levels"][j]["references"][i]["seed"] == seed
                    for j in range(2)), "original replicate seed drift")
    for spp, work in ((8192, PRIOR), (16384, SECOND)):
        native = read(work / "oracle.stdout.txt")
        require(native["oracle"] == "n010-rqmc-digital-shift"
                and native["scene_sha256"] == SOURCE_SHA
                and native["geometry_sha256"] == GEOMETRY_SHA
                and native["triangles"] == 1224
                and native["width"] == 320 and native["height"] == 180
                and native["spp"] == spp and native["seeds"] == list(SEEDS)
                and [r["seed"] for r in native["runs"]] == list(SEEDS)
                and all(r["backface_absorbed"] == 0 for r in native["runs"]),
                "actual original oracle stdout physical/provenance mismatch")
    return first, result, screen


def materialize(first: dict, second: dict, previous_screen: dict) -> dict:
    # Companion N010 physical sampler proof is separate from N007's deliberately
    # false 'physical_correctness_proven' field (statistical-only screen).
    physical_inputs = {}
    proof = P.physical_proof(physical_inputs)
    require(proof["complete"] is True and proof["all_pass"] is True
            and proof["binary_sha256"] == BINARY_SHA
            and proof["sobol_table_sha256"] == NET_SHA,
            "original N010 009 physical/sampler proof is not PASS")
    state_dir = LANE / "capture/M001-H01-hwrt"
    state = Q.L.read_state(state_dir)
    require(state["sha256"] == {
        "geometry": "f8b25b1c20ad84b6b9b030a2edd12c4a812af7199e21002897be9cf974ad75ca",
        "frame": FRAME_SHA
    }, "H01 source-state bytes differ from original GPU lock")
    scene = Q.scene_for_state(state, 2)
    require(scene.text().encode("utf-8") == SCENE.read_bytes()
            and scene.geometry_sha256() == GEOMETRY_SHA,
            "full canonical N010 held-out physical scene not equal to captured state")
    require(Q.LEVELS == SCHEDULE and tuple(Q.L.N007_SEEDS) == tuple(SEEDS),
            "reference schedule/seeds changed from original N010")

    DEST.mkdir(parents=True)
    (DEST / "scene.n008").write_bytes(SCENE.read_bytes())
    levels = []
    manifests = []
    for spp, work, receipt in ((8192, PRIOR, first), (16384, SECOND, second)):
        names = {}
        for name in ["oracle.hits"] + [
            f"oracle.s{i}.{suffix}" for i in range(4) for suffix in SUFFIXES
        ]:
            suffix = name[len("oracle."):]
            destname = f"o.n{spp}.{suffix}"
            src = work / name
            dest = DEST / destname
            require(sha(src) == receipt["payload_sha256"][name],
                    f"original {spp} raw file hash changed: {name}")
            shutil.copyfile(src, dest)
            require(sha(dest) == receipt["payload_sha256"][name],
                    f"view copied file hash mismatch: {destname}")
            names[destname] = sha(dest)
        native = read(work / "oracle.stdout.txt")
        meta = dict(native)
        meta.update({
            "binary_sha256": BINARY_SHA, "net_sha256": NET_SHA,
            "scene_sha256": SOURCE_SHA, "geometry_sha256": GEOMETRY_SHA,
            "source_commit": receipt["source_commit"],
            "original_raw_receipt_sha256": sha(work / "result.json"),
            "import_note": "Byte-exact immutable copy, not a new oracle acquisition",
        })
        (DEST / f"n{spp}.meta.json").write_text(
            json.dumps(meta, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        manifests.append({
            "spp": spp,
            "references": [{
                "seed": seed, "path": f"o.n{spp}.s{i}.total.pfm",
                "sha256": names[f"o.n{spp}.s{i}.total.pfm"]
            } for i, seed in enumerate(SEEDS)]
        })
        input_manifest = {
            "schema_version": 1,
            "source_commit": second["source_commit"],
            "scene_sha256": SOURCE_SHA,
            "frame_state_sha256": FRAME_SHA,
            "levels": list(manifests)
        }
        screen_file = DEST / f"screen-n{spp}.json"
        screen_file.write_text(json.dumps(input_manifest, indent=2) + "\n")
        N007.SPP = SCHEDULE
        assessed = N007.assess(screen_file)
        require(assessed["scene_sha256"] == SOURCE_SHA
                and assessed["frame_state_sha256"] == FRAME_SHA
                and assessed["physical_correctness_proven"] is False,
                "original N007 full-frame manifest physical identity differs")
        expected_old = read(work / ("level1-screen.json" if spp == 8192
                                    else "two-level-screen.json"))
        require(assessed["rows"] == expected_old["rows"] and
                assessed["status"] == expected_old["status"] and
                assessed["eligible_at_spp"] == expected_old["eligible_at_spp"],
                "original N007 raw-PFM recomputation differs from frozen screen")
        # Independent read of all F64 headers; never infer from just receipt.
        for i, seed in enumerate(SEEDS):
            data = Q.L.read_sidecar(DEST / f"o.n{spp}.s{i}.f64")
            require((data["seed"], data["spp"], data["width"], data["height"]) ==
                    (seed, spp, state["width"], state["height"]),
                    "retained original full-precision F64 header mismatch")
        levels.append({
            "spp": spp,
            "screen": assessed,
            "geometry_hash_match": native["geometry_sha256"] == scene.geometry_sha256(),
            "all_payload_sha256": names,
        })

    require(levels[0]["screen"]["status"] == "incomplete" and
            levels[1]["screen"]["status"] == "statistical-screen-pass" and
            levels[1]["screen"]["eligible_at_spp"] == 16384 and
            all(x["geometry_hash_match"] for x in levels),
            "two original reference levels not qualifying")
    q = {
        "cell": "H01", "transport": "T_B2", "state_sha256": state["sha256"],
        "scene_sha256": SOURCE_SHA, "levels": levels,
        "classification": "STATISTICALLY_ELIGIBLE",
        "computational_variant": "original-full-prefix",
        "H01_M001_scope": "Static held-out geometry only; no R1 or N010 C1-C12 reuse",
        "original_first_result_sha256": FIRST_SHA,
        "original_second_result_sha256": SECOND_SHA,
        "original_n010_physical_validation_sha256": VALIDATION_SHA,
        "original_N007_physical_correctness_proven": False,
    }
    (DEST / "qualification.json").write_text(
        json.dumps(q, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    spec = {
        "state_directory": str(state_dir.relative_to(ROOT)),
        "state_sha256": state["sha256"]
    }
    verification = P.verify_reference(DEST, "H01", 2, spec, physical_inputs)
    require(verification["pass"] is True and
            verification["computational_variant"] == "original-full-prefix" and
            verification["levels"] == [8192, 16384],
            "canonical original N010 reference_provenance verification failed")
    report = {
        "schema": "lane-m-m001-h01-b2-original-reference-admission/1",
        "classification": "H01_B2_ORIGINAL_N010_REFERENCE_STATISTICALLY_ELIGIBLE_PROVENANCE_PASS",
        "complete": True,
        "reference_eligible": True,
        "full_original_raw_payloads_rehashed": 46,
        "full_original_N007_screen_replayed": True,
        "original_n010_sampler_physical_validation_009": "PASS",
        "original_N007_statistical_only_physical_correctness_proven": False,
        "quality_scored": False, "gpu_executed": False,
        "accepted_timing": False,
        "physical_scene_sha256": SOURCE_SHA, "frame_sha256": FRAME_SHA,
        "scene_geometry_sha256": GEOMETRY_SHA,
        "first_level_result_sha256": FIRST_SHA,
        "second_level_result_sha256": SECOND_SHA,
        "proof_009_sha256": VALIDATION_SHA,
        "reference_qualification_sha256": sha(DEST / "qualification.json"),
        "verification": verification,
        "retained_raw_view": str(DEST.relative_to(ROOT)),
        "scope_limitations": [
            "Admission is for H01/T_B2 only, not H01/B8/H02/H03 or dynamic scenes.",
            "Original N007's physical_correctness_proven=false is not changed; original N010 sampler/physical 009 companion proof was separately validated.",
            "No GPU PT/RC quality score or quality-matched calibrated timing is implied."
        ]
    }
    (DEST / "admission.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify-only", action="store_true",
                    help="refuse previously created reference; does not acquire samples")
    args = ap.parse_args()
    if args.verify_only:
        print(json.dumps({
            "classification": "NO_ADMISSION_CREATED_VERIFY_ONLY",
            "reference_eligible": False,
            "required_files": ["H01 original 13 raw", "8192 23 raw", "16384 23 raw"],
            "destination_exists": DEST.exists(),
            "archive_exists": ARCHIVE.exists()}, indent=2))
        return
    first, second, screen = replay_inputs()
    report = materialize(first, second, screen)
    # Transfer only the small immutable proof and manifest, never upload raw HDR.
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE.open("xb") as output:
        with tarfile.open(fileobj=output, mode="w") as t:
            for filename in ("admission.json", "qualification.json",
                             "screen-n8192.json", "screen-n16384.json",
                             "n8192.meta.json", "n16384.meta.json"):
                t.add(DEST / filename, arcname=filename, recursive=False)
            for file, name in (
                (PRIOR / "result.json", "original-8192-result.json"),
                (SECOND / "result.json", "original-16384-result.json")
            ):
                t.add(file, arcname=name, recursive=False)
    print(json.dumps({
        "classification": report["classification"],
        "reference_eligible": True,
        "accepted_spp": 16384, "local_raw_view": report["retained_raw_view"],
        "compact_archive": str(ARCHIVE.relative_to(ROOT)),
        "next": "STOP; send compact archive. No other reference cell, GPU/score/timing."
    }, indent=2))


if __name__ == "__main__":
    main()
