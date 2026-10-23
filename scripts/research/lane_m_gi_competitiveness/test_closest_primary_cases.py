"""013 registered case identities and historical CLI preservation; CPU only."""
import json
from pathlib import Path
import unittest

import closest_primary_cases as K


class CaseContracts(unittest.TestCase):
    def test_exact_eight_registered_cases(self):
        self.assertEqual([K.Case(*x).name for x in K.TARGETS],
                         ['c1-hwrt', 'c1-software', 'h01-hwrt', 'h01-software',
                          'h02-hwrt', 'h02-software', 'h03-hwrt', 'h03-software'])

    def test_unregistered_case_is_rejected(self):
        for case in [('C2', 'hwrt'), ('H01', 'vanilla'), ('H04', 'software')]:
            with self.assertRaisesRegex(ValueError, 'Unregistered'):
                K.Case(*case)

    def test_c1_preserves_original_two_frame_command(self):
        record = json.loads((K.ROOT / 'research/lanes/n010-comparison-readiness/results/011-rc-correctness-pilot.json').read_text())
        for backend in ('hwrt', 'software'):
            old = next(r['command'] for r in record['rows'] if (r['cell'], r['backend']) == ('C1', backend))
            command = K.command(K.Case('C1', backend), Path('/private/binary'), Path('/private/capture'))
            restored = list(command)
            restored[2] = old[2]
            restored[restored.index('--out') + 1] = old[old.index('--out') + 1]
            self.assertEqual(restored, old)
            self.assertIn('--target-state', command)

    def test_m001_matches_original_control_inputs(self):
        for cell in ('H01', 'H02', 'H03'):
            old = json.loads((K.ROOT / f'out/m001-{cell.lower()}-fixed-software-plan.json').read_text())['command']
            for backend in ('hwrt', 'software'):
                command = K.command(K.Case(cell, backend), Path('/private/binary'), Path('/private/capture'))
                for flag in ('--scene', '--scenario', '--direct-profile', '--spp'):
                    self.assertEqual(command[command.index(flag) + 1], old[old.index(flag) + 1])
                self.assertNotIn('--target-state', command)
                self.assertTrue(Path(command[command.index('--scene') + 1]).is_file())


if __name__ == '__main__':
    unittest.main()
