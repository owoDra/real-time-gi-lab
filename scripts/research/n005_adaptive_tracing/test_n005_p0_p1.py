from __future__ import annotations

import copy
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import n005_analysis as analysis
import n005_contract as contract


class N005ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config_path = (
            ROOT
            / "research/lanes/n005-adaptive-tracing/experiments/"
              "001-p0-p1-signal-probes-config.json"
        )
        cls.config = json.loads(cls.config_path.read_text(encoding="utf-8"))

    def test_frozen_contract_accepts_repository_config(self) -> None:
        contract.validate_config(copy.deepcopy(self.config))

    def test_extra_rays_are_rejected_in_p0_p1(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["phase_scope"]["extra_rays"] = 1
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)

    def test_signal_combination_is_rejected(self) -> None:
        changed = copy.deepcopy(self.config)
        changed["p1"]["signal_combination"] = "allowed"
        with self.assertRaises(contract.ContractError):
            contract.validate_config(changed)


class N005AnalysisTests(unittest.TestCase):
    def test_aligned_signal_localizes_error(self) -> None:
        signal = [1.0, 1.0, 0.0, 0.0]
        absolute = [4.0, 3.0, 0.1, 0.1]
        relative = [8.0, 6.0, 0.2, 0.2]
        affected = [True, True, False, False]
        result = analysis.localization_metrics(
            signal, absolute, relative, affected, [0.5]
        )
        self.assertEqual(result["support_affected_recall"], 1.0)
        self.assertEqual(result["support_affected_precision"], 1.0)
        self.assertGreater(result["pearson_absolute_error"], 0.9)
        self.assertEqual(
            result["ranked_selection"][0]["affected_recall"], 1.0
        )

    def test_visibility_capture_binary_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "visibility-000.bin"
            header = struct.pack(
                "<8sIIII",
                analysis.VISIBILITY_MAGIC,
                analysis.VISIBILITY_VERSION,
                2,
                1,
                2,
            )
            path.write_bytes(
                header
                + struct.pack("<2f", 1.0, float("inf"))
                + struct.pack("<2I", 7, analysis.INVALID_OWNER)
            )
            capture = analysis.read_visibility_capture(path)
            self.assertEqual((capture.width, capture.height), (2, 1))
            self.assertAlmostEqual(capture.depth[0], 1.0)
            self.assertEqual(capture.owner[0], 7)
            self.assertEqual(capture.owner[1], analysis.INVALID_OWNER)

    def test_visibility_signal_maps_separate_temporal_and_spatial_changes(self) -> None:
        previous = analysis.VisibilityCapture(
            2, 2,
            [1.0, float("inf"), 2.0, 2.0],
            [1, analysis.INVALID_OWNER, 2, 3],
        )
        current = analysis.VisibilityCapture(
            2, 2,
            [1.5, 3.0, 2.0, 2.0],
            [1, 4, 5, 3],
        )
        signals = analysis.signal_maps(previous, current)
        self.assertEqual(signals["newly-visible"][1], 1.0)
        self.assertEqual(signals["ownership-changed"][2], 1.0)
        self.assertGreater(signals["temporal-depth-change"][0], 0.0)
        self.assertGreater(signals["depth-discontinuity"][0], 0.0)

    def test_visibility_discontinuity_does_not_select_unowned_current_tile(self) -> None:
        previous = analysis.VisibilityCapture(
            2, 1,
            [1.0, float("inf")],
            [1, analysis.INVALID_OWNER],
        )
        current = analysis.VisibilityCapture(
            2, 1,
            [1.0, float("inf")],
            [1, analysis.INVALID_OWNER],
        )
        signals = analysis.signal_maps(previous, current)
        self.assertEqual(signals["visibility-discontinuity"][0], 1.0)
        self.assertEqual(signals["visibility-discontinuity"][1], 0.0)

    def test_pixel_errors_keep_absolute_relative_and_affected_separate(self) -> None:
        output = [0.001, 0.001, 0.001, 0.2, 0.2, 0.2]
        reference = [0.0, 0.0, 0.0, 0.1, 0.1, 0.1]
        absolute, relative, affected = analysis.pixel_error_vectors(
            output,
            reference,
            relative_floor=0.0001,
            affected_fraction=0.05,
        )
        self.assertAlmostEqual(absolute[0], 0.001)
        self.assertAlmostEqual(relative[0], 10.0)
        self.assertTrue(affected[0])
        self.assertAlmostEqual(absolute[1], 0.1)
        self.assertAlmostEqual(relative[1], 1.0)
        self.assertTrue(affected[1])


if __name__ == "__main__":
    unittest.main()
