import tempfile
import unittest
from pathlib import Path
from audit_transport import lambert_light, shadow_triangle_hit, source_audit, SOURCE, SHADERS

class TestAuditTransport(unittest.TestCase):
    def test_lit_unoccluded_equal(self):
        d,unshadowed,blocked=lambert_light((0,0,0),(0,1,0),(0,2,0),0.5)
        self.assertGreater(d,0)
        self.assertEqual(d,unshadowed)
        self.assertFalse(blocked)

    def test_occluded_cpu_zero_unshadowed_positive(self):
        tri=((-1,1,-1),(1,1,-1),(0,1,1))
        d,unshadowed,blocked=lambert_light((0,0,0),(0,1,0),(0,2,0),0.5,(tri,))
        self.assertTrue(blocked)
        self.assertEqual(d,0)
        self.assertGreater(unshadowed,0)

    def test_backface_unlit_even_without_occlusion(self):
        d,u,_=lambert_light((0,0,0),(0,-1,0),(0,2,0),0.5)
        self.assertEqual((d,u),(0,0))

    def test_blocker_beyond_light_is_not_shadowing(self):
        tri=((-1,3,-1),(1,3,-1),(0,3,1))
        d,u,blocked=lambert_light((0,0,0),(0,1,0),(0,2,0),0.5,(tri,))
        self.assertEqual(d,u)
        self.assertFalse(blocked)

    def test_shadow_triangle_off_ray(self):
        tri=((10,1,10),(11,1,10),(10,1,11))
        self.assertFalse(shadow_triangle_hit((0,0,0),(0,1,0),1.8,tri))

    def test_shadow_triangle_two_sided(self):
        a=((-1,1,-1),(1,1,-1),(0,1,1))
        self.assertTrue(shadow_triangle_hit((0,0,0),(0,1,0),1.8,a))
        self.assertTrue(shadow_triangle_hit((0,0,0),(0,1,0),1.8,tuple(reversed(a))))

    def test_source_contract_known_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            files={
               SOURCE/'CMakeLists.txt': 'add_compute_shader(\n i001_radiance\n shaders/research/lane_n_end_to_end_renderer/n001_physical_radiance.comp.glsl)',
               SOURCE/'n001_runtime.cpp':'"i001_radiance.spv" "i001_radiance.spv"',
               SOURCE/'n001_reference.cpp': 'const auto blocker = bvh.trace(\n float(x) + 0.5F; float(y) + 0.5F; result.converged = delta.p99_abs <= threshold',
               SHADERS/'n001_physical_radiance.comp.glsl':'float point_light_lambert() {}',
               SHADERS/'n003_composite_software.comp.glsl':'visible_to_light(position, normal, light_direction, distance_to_light); indirect += lookup_probe(',
               SHADERS/'n001_composite.comp.glsl':'visible_to_light(position, normal, light_direction, distance_to_light)',
               SHADERS/'imported/integration/i001_radiance.comp.glsl':'deterministic_radiance',
            }
            for p,s in files.items():
                f=root/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
            a=source_audit(root)
            self.assertEqual(sum(a['checks'].values()),10)
            self.assertTrue(a['analytical_occluder_example']['demonstrates_possible_model_mismatch'])
            self.assertFalse(a['historic_m3b_root_cause_proven'])

    def test_source_contract_fails_closed_on_shader_regression(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            files={SOURCE/'CMakeLists.txt':'add_compute_shader(i001_radiance somewhere_else.glsl)',
                SOURCE/'n001_runtime.cpp':'"i001_radiance.spv"',SOURCE/'n001_reference.cpp':'',
                SHADERS/'n001_physical_radiance.comp.glsl':'void visible_to_light() {}',
                SHADERS/'n003_composite_software.comp.glsl':'',
                SHADERS/'n001_composite.comp.glsl':'',
                SHADERS/'imported/integration/i001_radiance.comp.glsl':''}
            for p,s in files.items():
                f=root/p;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
            a=source_audit(root)
            self.assertFalse(a['all_source_checks_pass'])
            self.assertFalse(a['checks']['gpu_probe_lacks_shadow_query'])

if __name__=='__main__':unittest.main()
