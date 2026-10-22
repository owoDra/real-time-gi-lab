"""CPU safety contracts for one-step reference operation, never native/GPU sampling."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import reference_step as R


class ReferenceStepGuards(unittest.TestCase):
    def test_unregistered_cell_and_depth(self):
        for cell, depth in [('C1', 2), ('H01', 4)]:
            with self.assertRaises(ValueError):
                R.target(cell, depth)

    def test_admitted_h01_b2_cannot_be_sampled(self):
        with patch.object(R, 'preflight') as preflight:
            with self.assertRaisesRegex(ValueError, 'already admitted'):
                R.acquire('H01', 2, 8192)
            preflight.assert_not_called()

    def test_cannot_skip_or_repeat_frozen_level(self):
        with patch.object(R, 'preflight', return_value=({}, {}, {})), \
             patch.object(R, 'prior_levels', return_value=([(8192, Path('/unused'))],
                                                          [{'screen': {'status': 'incomplete'}}])), \
             patch.object(R.subprocess, 'run') as native:
            for spp in (8192, 32768):
                with self.assertRaisesRegex(ValueError, 'exactly the next'):
                    R.acquire('H02', 2, spp)
            native.assert_not_called()

    def test_sampling_stops_after_statistical_pass(self):
        with patch.object(R, 'preflight', return_value=({}, {}, {})), \
             patch.object(R, 'prior_levels', return_value=(
                 [(8192, Path('/unused')), (16384, Path('/unused2'))],
                 [{'screen': {'status': 'statistical-screen-pass'}}])), \
             patch.object(R.subprocess, 'run') as native:
            with self.assertRaisesRegex(ValueError, 'sampling must stop'):
                R.acquire('H02', 2, 32768)
            native.assert_not_called()

    def test_no_overwrite_of_partial_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.json'
            R.write_new(path, {'complete': False, 'error': 'retained partial'})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                R.write_new(path, {'complete': True})
            self.assertEqual(path.read_bytes(), original)

    def test_incomplete_level_cannot_be_imported(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            R.write_new(work / 'result.json', {'complete': False, 'returncode': -6})
            with self.assertRaisesRegex(ValueError, 'incomplete/wrong'):
                R.audit_level(work, 'H02', 2, 8192)


if __name__ == '__main__':
    unittest.main()
