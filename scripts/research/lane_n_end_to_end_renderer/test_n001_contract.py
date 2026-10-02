from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import n001_contract as contract


def config() -> dict:
    return {
        "schema_version": 1,
        "experiment": "N001",
        "source_of_truth": {"research_commit": "a75cf7857761cfbc783c9f1f847dc1380359481e"},
        "scene": {"path": "scene.gltf", "sha256": "0" * 64},
        "render_contract": {
            "width": 4,
            "height": 3,
            "hdr_format": "PFM-RGB-f32",
            "color_space": "linear-rec709",
            "origin": "top-left",
            "valid_pixel_mask": "all-finite-pixels",
            "metric_exposure": 1.0,
            "tone_mapping_for_metrics": False,
        },
        "playback": {
            "geometry_subset_seed": 20261002,
            "frames": [
                {"frame": i, "kind": kind, "camera": {"base_direction": [1.0, 0.32, 1.0], "orbit_radians": 0.0, "distance_diagonal": 0.82, "vfov_degrees": 70.0}, "light": {"offset_diagonal": [0.15, 0.35, 0.10], "radiance": [10, 10, 10]}, "geometry": {"rigid_phase": float(i), "deform_phase": 0.0, "topology_epoch": 0}}
                for i, kind in enumerate(("static", "camera-motion", "light-motion", "geometry-motion"))
            ]
        },
        "reference_contract": {"transport": "diffuse-path-traced", "glossy_specular": False, "min_spp": 64, "max_spp": 256, "max_diffuse_bounces": 8, "replicate_p99_abs_luminance_max": 0.001, "replicate_p99_relative_luminance_max": 0.01},
        "image_metrics": {
            "relative_luminance_floor": 1e-4,
            "affected_abs_luminance": 0.01,
            "affected_relative_luminance": 0.05,
            "required": [
                "mean_abs_luminance_error", "mean_relative_luminance_error",
                "rgb_rms_error", "p95_abs_luminance_error",
                "p99_abs_luminance_error", "max_abs_luminance_error",
                "p95_relative_luminance_error", "p99_relative_luminance_error",
                "affected_pixel_fraction",
            ],
        },
        "timing_boundary": {
            "primary_axis": "gpu_timestamp",
            "cpu_wall_role": "diagnostic-health-provenance",
            "required_gi_stages": [
                "renderer_prerequisite_attributable_to_gi", "producer", "geometry_prepare_upload", "acceleration_structure_maintenance", "traversal", "gather", "radiance_storage", "merge_resolve", "synchronization"
            ],
            "required_totals": ["complete_gi_gpu", "complete_renderer_gpu"],
            "formal_performance_threshold": None,
        },
        "memory_boundary": {"required_categories": ["geometry_as_persistent", "radiance_storage_persistent", "producer_stream_persistent", "transient", "scratch", "old_new_overlap", "true_lifetime_peak", "host_mirrors"]},
    }


class ContractTests(unittest.TestCase):
    def test_config_and_playback_are_deterministic(self) -> None:
        cfg = config()
        contract.validate_config(cfg)
        first = contract.build_playback_manifest(cfg)
        second = contract.build_playback_manifest(json.loads(json.dumps(cfg)))
        self.assertEqual(first, second)

    def test_pfm_round_trip_preserves_top_left_pixels(self) -> None:
        image = contract.PFMImage(2, 2, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test.pfm"
            contract.write_pfm(path, image)
            self.assertEqual(contract.read_pfm(path), image)

    def test_metric_zero_for_identical_images(self) -> None:
        cfg = config()
        image = contract.PFMImage(1, 1, (1.0, 2.0, 3.0))
        metrics = contract.compare_hdr(image, image, cfg)
        self.assertEqual(metrics["rgb_rms_error"], 0.0)
        self.assertEqual(metrics["affected_pixel_fraction"], 0.0)

    def test_metric_detects_difference(self) -> None:
        cfg = config()
        ref = contract.PFMImage(1, 1, (1.0, 1.0, 1.0))
        out = contract.PFMImage(1, 1, (2.0, 1.0, 1.0))
        metrics = contract.compare_hdr(out, ref, cfg)
        self.assertGreater(metrics["rgb_rms_error"], 0.0)
        self.assertGreater(metrics["max_abs_luminance_error"], 0.0)

    def test_contract_smoke(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as tmp:
            summary = contract.make_contract_smoke(Path(tmp), cfg)
            self.assertEqual(summary["status"], "pass")

    def test_target_artifact_validation(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            playback = contract.build_playback_manifest(cfg)
            image = contract.PFMImage(cfg["render_contract"]["width"], cfg["render_contract"]["height"], tuple([1.0, 1.0, 1.0] * (cfg["render_contract"]["width"] * cfg["render_contract"]["height"])))
            frames = []
            stages = cfg["timing_boundary"]["required_gi_stages"]
            categories = cfg["memory_boundary"]["required_categories"]
            for state in playback["frames"]:
                out = Path("frames") / f"output-{state['frame']:03d}.pfm"
                ref = Path("frames") / f"reference-{state['frame']:03d}.pfm"
                contract.write_pfm(root / out, image)
                contract.write_pfm(root / ref, image)
                memory = {name: 1 for name in categories}
                memory["true_lifetime_peak"] = 2
                frames.append({
                    "frame": state["frame"],
                    "scene_state_sha256": state["state_sha256"],
                    "output_hdr": str(out),
                    "reference_hdr": str(ref),
                    "reference": {"spp": 64, "converged": True, "replicate_p99_abs_luminance": 0.0, "replicate_p99_relative_luminance": 0.0},
                    "correctness": {"traversal_runtime_errors": 0, "oob_errors": 0, "storage_failures": 0, "lifetime_errors": 0, "alignment_valid": True},
                    "timing_us": {"complete_gi_gpu": 9.0, "complete_renderer_gpu": 10.0, "stages": {name: 1.0 for name in stages}},
                    "memory_bytes": memory,
                })
            provenance = {
                "schema_version": 1,
                "git": {"branch": "research-lane-n-end-to-end-renderer", "commit": "1" * 40, "dirty": False},
                "device": {"name": "gpu", "driver_name": "driver", "driver_info": "info", "api_version": 1, "timestamp_period_ns": 1.0},
                "scene_sha256": cfg["scene"]["sha256"],
                "playback_sha256": playback["playback_sha256"],
                "frames": frames,
            }
            (root / "n001-provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
            summary = contract.validate_target_artifact(root, cfg)
            self.assertEqual(summary["status"], "pass")

    def test_target_artifact_rejects_path_escape(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(contract.ContractError):
                contract._artifact_relative_path(root, "../escape.pfm", "image")

    def test_target_artifact_rejects_non_integer_memory(self) -> None:
        cfg = config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            playback = contract.build_playback_manifest(cfg)
            image = contract.PFMImage(cfg["render_contract"]["width"], cfg["render_contract"]["height"], tuple([1.0, 1.0, 1.0] * (cfg["render_contract"]["width"] * cfg["render_contract"]["height"])))
            frames = []
            for state in playback["frames"]:
                out = Path("frames") / f"output-{state['frame']:03d}.pfm"
                ref = Path("frames") / f"reference-{state['frame']:03d}.pfm"
                contract.write_pfm(root / out, image)
                contract.write_pfm(root / ref, image)
                memory = {name: 1 for name in cfg["memory_boundary"]["required_categories"]}
                memory["true_lifetime_peak"] = 2.0
                frames.append({
                    "frame": state["frame"], "scene_state_sha256": state["state_sha256"],
                    "output_hdr": str(out), "reference_hdr": str(ref),
                    "reference": {"spp": 64, "converged": True, "replicate_p99_abs_luminance": 0.0, "replicate_p99_relative_luminance": 0.0},
                    "correctness": {"traversal_runtime_errors": 0, "oob_errors": 0, "storage_failures": 0, "lifetime_errors": 0, "alignment_valid": True},
                    "timing_us": {"complete_gi_gpu": 9.0, "complete_renderer_gpu": 10.0, "stages": {name: 1.0 for name in cfg["timing_boundary"]["required_gi_stages"]}},
                    "memory_bytes": memory,
                })
            provenance = {
                "schema_version": 1,
                "git": {"branch": "research-lane-n-end-to-end-renderer", "commit": "1" * 40, "dirty": False},
                "device": {"name": "gpu", "driver_name": "driver", "driver_info": "info", "api_version": 1, "timestamp_period_ns": 1.0},
                "scene_sha256": cfg["scene"]["sha256"], "playback_sha256": playback["playback_sha256"], "frames": frames,
            }
            (root / "n001-provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
            with self.assertRaises(contract.ContractError):
                contract.validate_target_artifact(root, cfg)


if __name__ == "__main__":
    unittest.main()
