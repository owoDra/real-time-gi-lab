from __future__ import annotations
import unittest
import audit_p1l_c0_division_rounding as c0

class TestDivisionRisk(unittest.TestCase):
    def test_known_f32_slab_boundary_changes_decision(self):
        data = c0.audit(seed=6006, samples=2000)
        self.assertGreater(data["different_float32_enters"], 0)
        counterexample = data["first_constructed_decision_flip"]
        self.assertNotEqual(counterexample["direct_accepts"],
                            counterexample["reciprocal_accepts"])
        self.assertGreater(counterexample["x_exit_division"], counterexample["tmax"])
        self.assertGreater(counterexample["x_exit_reciprocal"], counterexample["tmax"])

    def test_f32_is_rounded(self):
        self.assertNotEqual(c0.f32(1.0/3.0), 1.0/3.0)

if __name__ == "__main__":
    unittest.main()
