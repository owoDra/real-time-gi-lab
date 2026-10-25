"""033 analytic tests: distinct from actual host API and compiled SDK HLSL."""
import math
import unittest
import restir_gi_bridge_math as M


class AnalyticBridge(unittest.TestCase):
    def test_cosine_pdf_no_resampling_recovers_path(self):
        for x in (0., .2, 1., 3.):
            p=(x,0.,1.);pdf=1/math.sqrt(x*x+1)/math.pi
            self.assertAlmostEqual(M.no_resampling((0,0,0),(0,0,1),p,2.5,pdf),2.5)

    def test_radiance_has_no_spurious_distance_attenuation(self):
        self.assertEqual(M.target((0,0,0),(0,0,1),(0,0,1),3),M.target((0,0,0),(0,0,1),(0,0,8),3))

    def test_inverse_pdf_and_black_miss(self):
        self.assertEqual(M.raw_weight(.25),4);self.assertEqual(M.raw_weight(0),0)

    def test_two_candidate_exact_ris(self):
        self.assertAlmostEqual(M.ris_exact_expectation([2,7],[.25,.5],[1,6]),11)

    def test_ris_preserves_zero_candidate_count(self):
        self.assertAlmostEqual(M.ris_exact_expectation([0,7],[.25,.5],[0,6]),7)

    def test_all_black_ris(self):
        self.assertEqual(M.ris_exact_expectation([0,0],[0,0],[0,0]),0)

    def test_nonuniform_targets_do_not_change_exact_expectation(self):
        for t in ([1,1],[.01,10],[3,7]): self.assertAlmostEqual(M.ris_exact_expectation([2,7],[.25,.5],t),11)

    def test_invalid_physical_inputs_reject(self):
        for x in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):M.raw_weight(x)
            with self.assertRaises(ValueError):M.target((0,0,0),(0,0,1),(0,0,1),x)

    def test_jacobian_identity_and_reciprocal(self):
        a=(0,0,0);b=(1,0,0);p=(0,0,2);n=(0,0,-1)
        self.assertEqual(M.jacobian(a,a,p,n),1)
        self.assertAlmostEqual(M.jacobian(a,b,p,n)*M.jacobian(b,a,p,n),1)

    def test_jacobian_distance_ratio(self):
        self.assertEqual(M.jacobian((0,0,1),(0,0,0),(0,0,2),(0,0,-1)),4)

    def test_jacobian_grazing_and_wrong_side(self):
        self.assertEqual(M.jacobian((0,0,0),(1,0,0),(0,0,1),(1,0,0)),0)
        self.assertEqual(M.jacobian((0,0,2),(0,0,0),(0,0,1),(0,0,1)),0)
        self.assertEqual(M.jacobian((0,0,1),(0,0,0),(0,0,1),(0,0,-1)),0)

    def test_official_validation_policy_boundaries(self):
        self.assertEqual(M.validate_jacobian(.1),(True,1/3));self.assertEqual(M.validate_jacobian(10),(True,3))
        for x in (.099,10.001,float('nan'),float('inf')):self.assertFalse(M.validate_jacobian(x)[0])

    def test_plane_visibility_blocks_actual_segment(self):
        self.assertFalse(M.visible_plane((0,0,0),(0,0,1)));self.assertTrue(M.visible_plane((1,0,0),(1,0,1)))

    def test_plane_endpoint_and_outside_segment(self):
        for a,b in [((0,0,.5),(0,0,1)),((0,0,0),(0,0,.5)),((0,0,0),(0,0,.2)),((0,0,0),(1,0,0))]:self.assertTrue(M.visible_plane(a,b))

    def test_oriented_two_sided_domains_are_distinct(self):
        self.assertTrue(M.oriented_support((0,0,1),(0,0,0),(0,0,1)))
        self.assertFalse(M.oriented_support((0,0,-1),(0,0,0),(0,0,1)))
        self.assertTrue(M.oriented_support((0,0,-1),(0,0,0),(0,0,-1)))

    def test_finite_b2_b8_suffixes(self):
        self.assertEqual(M.remaining_vertices(2),(1,));self.assertEqual(M.remaining_vertices(8),(1,2,3,4,5,6,7))
        with self.assertRaises(ValueError):M.remaining_vertices(9)

    def test_surface_depth_material_normal_validity(self):
        a=dict(valid=True,material=0xffffffff,normal=(0,0,1),depth=1.)
        self.assertTrue(M.similar(a,dict(a)))
        for b in [dict(a,valid=False),dict(a,material=0),dict(a,normal=(0,0,-1)),dict(a,depth=2)]:self.assertFalse(M.similar(a,b))

    def test_previous_frame_visibility_uses_previous_receiver(self):
        current=(0,0,0);previous=(1,0,0);end=(0,0,1)
        self.assertFalse(M.visible_plane(current,end));self.assertTrue(M.visible_plane(previous,end))


if __name__=='__main__': unittest.main()
