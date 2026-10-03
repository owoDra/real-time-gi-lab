#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import n004_contract as contract
import n004_scene_factory as scene_factory
import run_n004_weakness_atlas as runner
import run_n003_preflight_v4 as common

CONFIG = common.ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/004-n004-weakness-atlas-config.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    config = contract.load_config(CONFIG)
    families = config["families"]
    require(
        families["thin-geometry-light-leak"]["scenes"] == contract.EXPECTED_LEAK_SCENES,
        "N004 leak matrix is incomplete",
    )
    require(
        families["camera-disocclusion"]["cases"][0]["motion_fractions"] == contract.ABRUPT_FRACTIONS,
        "N004 abrupt camera path changed",
    )
    require(
        families["camera-disocclusion"]["cases"][1]["motion_fractions"] == contract.GRADUAL_FRACTIONS,
        "N004 gradual camera path changed",
    )
    require(
        families["changing-illumination"]["cases"][0]["motion_fractions"] == contract.ABRUPT_FRACTIONS,
        "N004 step light path changed",
    )
    require(
        families["changing-illumination"]["cases"][1]["motion_fractions"] == contract.GRADUAL_FRACTIONS,
        "N004 gradual light path changed",
    )

    not_observed = {
        "rgb_rms_error": 0.0002,
        "p99_relative_luminance_error": 0.02,
        "scale_aware_affected_pixel_fraction": 0.002,
    }
    require(
        runner.generic_classification(not_observed, config) == "not-observed-under-tested-regime",
        "N004 not-observed classification changed",
    )
    bounded = {
        "rgb_rms_error": 0.002,
        "p99_relative_luminance_error": 0.08,
        "scale_aware_affected_pixel_fraction": 0.02,
    }
    require(
        runner.generic_classification(bounded, config) == "present-but-bounded",
        "N004 bounded classification changed",
    )
    blocker = {
        "rgb_rms_error": 0.02,
        "p99_relative_luminance_error": 0.30,
        "scale_aware_affected_pixel_fraction": 0.02,
    }
    require(
        runner.generic_classification(blocker, config) == "material-blocker",
        "N004 blocker classification changed",
    )

    require(
        runner.correctness_failed({
            "source": {"internal_correctness": False},
            "frames": [{"internal_correctness": True}],
        }),
        "N004 source correctness failure must remain observable",
    )
    require(
        runner.correctness_failed({
            "source": {"internal_correctness": True},
            "frames": [{"internal_correctness": False}],
        }),
        "N004 target correctness failure must remain observable",
    )
    require(
        not runner.correctness_failed({
            "source": {"internal_correctness": True},
            "frames": [{"internal_correctness": True}],
        }),
        "N004 correctness pass was misclassified",
    )
    require(
        families["world-shape"]["correctness_or_capacity_failure_is_blocker"] is True,
        "N004 world correctness failure must remain a blocker",
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        manifest_a = scene_factory.generate_all(root / "a")
        manifest_b = scene_factory.generate_all(root / "b")
        require(manifest_a == manifest_b, "N004 synthetic scene manifest is nondeterministic")
        require(
            set(contract.EXPECTED_LEAK_SCENES).issubset(manifest_a["scenes"]),
            "N004 generated leak cases are incomplete",
        )
        for scene_name, meta in manifest_a["scenes"].items():
            require(meta["idle_dynamic_control_triangles"] == 36, f"control mesh changed: {scene_name}")
            gltf_a = json.loads((root / "a" / meta["path"]).read_text(encoding="utf-8"))
            gltf_b = json.loads((root / "b" / meta["path"]).read_text(encoding="utf-8"))
            require(gltf_a == gltf_b, f"N004 glTF nondeterministic: {scene_name}")
            require(len(gltf_a["meshes"]) >= 2, f"N004 scene lost static/dynamic ownership split: {scene_name}")
            first_index_accessor = gltf_a["meshes"][0]["primitives"][0]["indices"]
            first_triangle_count = gltf_a["accessors"][first_index_accessor]["count"] // 3
            require(first_triangle_count == 36, f"N004 first mesh is not the frozen control object: {scene_name}")
            require((root / "a" / meta["path"]).is_file(), f"missing generated glTF: {scene_name}")
            require((root / "a" / Path(meta["path"]).with_suffix(".bin")).is_file(), f"missing generated buffer: {scene_name}")

    accepted_a001 = (
        common.ROOT / "src/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/a001_runtime.cpp"
    ).read_text(encoding="utf-8")
    wrapper = (
        common.ROOT / "src/research/lane_n_end_to_end_renderer/n004_a001_runtime.cpp"
    ).read_text(encoding="utf-8")
    cmake = (
        common.ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"
    ).read_text(encoding="utf-8")
    require("camera_motion_fraction" not in accepted_a001, "N004 contaminated accepted A001 runtime")
    require("build_a001_params_n004_original" in wrapper, "N004 isolated A001 wrapper missing")
    require("n004_a001_runtime.cpp" in cmake and "N004_SHARED_SUPPORT_SOURCES" in cmake,
            "N004 isolated source wiring missing")

    print("N004 contract/scene-factory/isolation/correctness tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
