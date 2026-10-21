#!/usr/bin/env python3
"""M001 H01: materialize canonical N008 finite-transport scene inputs, CPU only.

This does NOT acquire or qualify reference radiance. It refuses changed state,
generator or physical-scene bytes and never imports GPU image output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n008_hdr_oracle"))
import n008lib as N008  # reuse canonical source rather than another estimator

GEOMETRY_SHA = "f8b25b1c20ad84b6b9b030a2edd12c4a812af7199e21002897be9cf974ad75ca"
FRAME_SHA = "70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4"
GENERATOR_SHA = "cd92c0db431be03b4fe07ed3db4f21aff43d35f44b0d6c821b7d9102297b76f9"
SOURCE_SHA = {
    2: "7153f784ef601167e17aaff7fbbaec1a641f1f194b03f71d248c2965d5847618",
    8: "9cc4fbfeb1aeda2851538e6318a44e0aa2165ae32ebdb5f48859b4448c92438d",
}
CANONICAL_GEOMETRY_SHA = "fd6380ce0848e37d19f06c622f03dbbd76d0c900ff34b9195d2be155b4934966"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def freeze(work: Path, output: Path) -> dict:
    work, output = work.resolve(), output.resolve()
    if output.exists():
        raise ValueError("refuse existing output; never overwrite a reference source")
    capture = work / "capture/M001-H01-hwrt"
    geom, frame = capture / "geometry-state.bin", capture / "frame-state.bin"
    if sha(geom) != GEOMETRY_SHA or sha(frame) != FRAME_SHA:
        raise ValueError("H01 original geometry/frame payload not identical to audited state")
    factory = ROOT / "scripts/research/lane_n_end_to_end_renderer/n004_scene_factory.py"
    if sha(factory) != GENERATOR_SHA:
        raise ValueError("preregistered N004 generator SHA mismatch")
    original = json.loads((work / "assets/manifest.json").read_text())
    receipt = json.loads((work / "result.json").read_text())
    if original.get("factory_sha256") != GENERATOR_SHA or original.get("complete") is not True:
        raise ValueError("frozen N004 manifest differs")
    if receipt.get("geometry_manifest_sha256") != sha(work / "assets/manifest.json"):
        raise ValueError("original pre-capture state manifest differs")
    for filename in ("M001-H01.gltf", "M001-H01.bin"):
        key = "gltf_sha256" if filename.endswith(".gltf") else "bin_sha256"
        if sha(work / "assets" / filename) != original["scenes"][0][key]:
            raise ValueError("original scene asset changed")
    state = N008.read_state(capture)
    if state["sha256"] != {"geometry": GEOMETRY_SHA, "frame": FRAME_SHA}:
        raise ValueError("canonical N008 read_state differs from original state hashes")
    if (state["width"], state["height"], len(state["verts"])) != (320, 180, 1224):
        raise ValueError("wrong H01 geometry/viewport")
    if not (state["meta"][:,3] == 1).all():
        raise ValueError("physically unmatched sidedness")
    result = {"schema": "lane-m-m001-h01-independent-reference-scene-source/1",
              "complete": False, "reference_eligible": False,
              "physical_control_pass": False, "gpu_executed": False,
              "quality_scored": False, "source_state_sha256": state["sha256"],
              "n004_generator_sha256": GENERATOR_SHA,
              "n008_source_sha256": sha(Path(N008.__file__)),
              "transports": []}
    scenes = []
    for bounce in (2, 8):
        scene = N008.state_scene(state, max_bounces=bounce)
        source = scene.text().encode()
        got = hashlib.sha256(source).hexdigest()
        if got != SOURCE_SHA[bounce]:
            raise ValueError(f"T_B{bounce} scene source drift: {got}")
        if scene.geometry_sha256() != CANONICAL_GEOMETRY_SHA:
            raise ValueError("canonical triangle material/float64 identity mismatch")
        scenes.append((bounce, source))
        result["transports"].append({
            "name": f"T_B{bounce}", "max_bounces": bounce,
            "scene_sha256": got, "canonical_geometry_sha256": CANONICAL_GEOMETRY_SHA,
            "width": scene.width, "height": scene.height,
            "eligibility": "NOT_RUN_NOT_QUALIFIED",
            "original_sampling_requirement": "4 seeds; two consecutive levels within the original N010 support/5%/1e-5 criteria; no post-hoc R1 transfer"
        })
    output.mkdir(parents=True)
    for bounce, source in scenes:
        (output / f"M001-H01-T_B{bounce}.n008").write_bytes(source)
    result["complete"] = True
    (output / "manifest.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args = ap.parse_args()
    obj = freeze(args.work,args.output)
    print(json.dumps({"complete":obj["complete"],"reference_eligible":False,
                      "transports":[(r["name"],r["scene_sha256"]) for r in obj["transports"]],
                      "output":str(args.output)},indent=2))


if __name__ == "__main__":
    main()
