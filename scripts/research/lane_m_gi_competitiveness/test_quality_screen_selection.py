"""Scientific first-pass/prefix-stop classifier tests; no native execution."""
import unittest
from summarize_quality_screen import validate_ladder

def row(spp, classification, valid=True):
    return {'spp': spp, 'audit': {'classification': classification, 'quality_evidence_valid': valid}}

class SelectionTests(unittest.TestCase):
    def test_first_pass(self):
        self.assertEqual(validate_ladder([row(1, 'QUALITY_FAIL'), row(4, 'PASS')]), 4)
    def test_terminal_loss(self):
        self.assertIsNone(validate_ladder([row(n, 'QUALITY_FAIL') for n in (1,4,16,64,256,1024)]))
    def test_skipped_level(self):
        with self.assertRaises(ValueError): validate_ladder([row(1, 'QUALITY_FAIL'), row(16, 'PASS')])
    def test_after_pass(self):
        with self.assertRaises(ValueError): validate_ladder([row(1, 'PASS'), row(4, 'PASS')])
    def test_incomplete_and_invalid(self):
        for rows in ([], [row(1, 'QUALITY_FAIL')], [row(1, 'PASS', False)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): validate_ladder(rows)

if __name__ == '__main__': unittest.main()
