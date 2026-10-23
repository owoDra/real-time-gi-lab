"""012 CPU input isolation and actual011 H01 contract reuse; never launch GPU."""
import unittest
from unittest.mock import patch

import ddgi_corrected_quality_cases as F


class CorrectedInputs(unittest.TestCase):
    def test_exact_cohort_and_budgets(self):
        self.assertEqual(F.TARGETS, tuple((c, b) for c in ('H01', 'H02', 'H03') for b in (2, 8)))
        self.assertEqual(F.BUDGETS, ((8, 128), (16, 256), (24, 512)))
        for args in [('H04', 2, 0), ('H01', 3, 0), ('H01', 2, True), ('H01', 2, -1), ('H01', 2, 3)]:
            with self.assertRaises(ValueError):
                F.Case(*args)

    def test_h01_commands_match_existing_corrected_contracts_exactly(self):
        for rung in range(3):
            for depth in (2, 8):
                c = F.Case('H01', depth, rung)
                old = F.B.get_case(f'integrity-h01-q{rung}-b{depth}')
                self.assertEqual(F.command(c, cpu=True), F.B.command(old, c.work / 'capture', cpu=True))
                self.assertNotEqual(c.work, old.work)
                self.assertNotEqual(c.plan, old.plan)
                self.assertNotEqual(c.archive, old.archive)

    def test_reuses_six_actual_h01_receipts_without_native_execution_or_mutation(self):
        receipts = [F.B.CPU / f'integrity-h01-q{r}-b{d}' / 'result.json' for r in range(3) for d in (2, 8)]
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in receipts]
        with patch.object(F.subprocess, 'run', side_effect=AssertionError('No native rerun permitted')):
            for rung in range(3):
                for depth in (2, 8):
                    report = F.cpu_contract(F.Case('H01', depth, rung))
                    self.assertTrue(report['reused_011'])
                    self.assertFalse(report['gpu_executed'])
        self.assertEqual(before, [(p.read_bytes(), p.stat().st_mtime_ns) for p in receipts])

    def test_different_scenes_keep_static_entry_and_corrected_binary(self):
        for cell in ('H02', 'H03'):
            for depth in (2, 8):
                for rung in range(3):
                    case = F.Case(cell, depth, rung)
                    cmd = F.command(case)
                    self.assertEqual(cmd[2], str(F.B.BUILD / 'm001-ddgi-border-transition'))
                    self.assertEqual(cmd[cmd.index('--state') + 1], str(case.state))
                    self.assertNotIn('--target-state', cmd)
                    self.assertNotIn('--cpu-check', cmd)
                    self.assertEqual(F.command(case, cpu=True), cmd + ['--cpu-check'])
                    self.assertIn('m001-ddgi-border-quality-', str(case.plan))

    def test_native_shapes_cover_all_ray_work(self):
        for rung, (side, rays) in enumerate(F.BUDGETS):
            for depth in (2, 8):
                d = F.expected_contract(F.Case('H03', depth, rung))
                self.assertEqual(d['stage_count'], depth - 1)
                self.assertEqual(d['tile_count_per_stage'] * 4096, side**3 * rays)
                self.assertFalse(d['gpu_initialized'])


if __name__ == '__main__':
    unittest.main()
