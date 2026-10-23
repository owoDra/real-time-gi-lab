from dataclasses import replace
import unittest

import ddgi_border_cases as F


class QualificationInventory(unittest.TestCase):
    def test_exact_twenty_case_inventory_and_order(self):
        c = F.CASES
        self.assertEqual(len(c), 20)
        self.assertEqual(len(set(x.name for x in c)), 20)
        self.assertEqual([sum(x.family == k for x in c) for k in ('static', 'dynamic', 'integrity')], [6, 8, 6])
        self.assertEqual([x.name for x in c[:6]], ['static-direct', 'static-black', 'static-unit', 'static-hdr', 'static-scene-one', 'static-scene-seven'])
        self.assertEqual([(x.side, x.rays, x.depth) for x in c[14:]], [(8, 128, 2), (8, 128, 8), (16, 256, 2), (16, 256, 8), (24, 512, 2), (24, 512, 8)])

    def test_all_native_commands_have_explicit_new_binary_and_shaders(self):
        for c in F.CASES:
            cmd = F.command(c)
            self.assertIn(str(F.BUILD / 'm001-ddgi-border-transition'), cmd)
            self.assertEqual(cmd[cmd.index('--sdk-shaders') + 1], str(F.SHADERS))
            self.assertEqual(cmd[cmd.index('--vertices') + 1], str(c.depth))
            self.assertEqual('--target-state' in cmd, c.transition)
            self.assertEqual('--history-policy' in cmd, c.transition)
            self.assertNotIn('--cpu-check', cmd)
            self.assertEqual(F.command(c, cpu=True), cmd + ['--cpu-check'])

    def test_modified_or_unknown_case_cannot_get_native_command(self):
        with self.assertRaises(ValueError):
            F.get_case('static-unknown')
        for key, value in [('side', 32), ('rays', 1024), ('mode', 'constant8'), ('depth', 8)]:
            with self.assertRaises(ValueError):
                F.command(replace(F.CASES[0], **{key: value}))

    def test_exact_physical_source_target_return_boundaries(self):
        for c in F.CASES:
            self.assertEqual(c.state, F.D.WORK / c.kind if c.kind and not c.transition else F.SOURCE)
        for kind in ('light', 'geometry'):
            for depth in (2, 8):
                s = F.expected_schedule(kind, depth)
                self.assertEqual([x['state_index'] for x in s], [0, 1, 1, 0])
                self.assertEqual([x['moved_primitives'] for x in s], [0, 1224, 0, 1224] if kind == 'geometry' else [0] * 4)
                self.assertTrue(all(x['finite_stages'] == depth - 1 and x['reset_both_atlases'] for x in s))


if __name__ == '__main__':
    unittest.main()
