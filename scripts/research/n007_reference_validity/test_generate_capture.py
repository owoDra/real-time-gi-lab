#!/usr/bin/env python3
"""N007 source overlay contracts; synthetic CPU-only unit tests."""
import unittest
from generate_capture import composite, runtime

class OverlayTest(unittest.TestCase):
    def test_component_channels_preserved(self):
        src='image.pixels[id] = vec4(radiance, radiance, radiance, 1.0);'
        result=composite(src)
        self.assertIn('vec4(direct, indirect, radiance, 1.0)',result)
        self.assertNotIn('vec4(radiance, radiance, radiance, 1.0)',result)
    def test_missing_anchor_fails_closed(self):
        with self.assertRaises(ValueError):composite('void main() {}')
    def test_multiple_anchors_fail_closed(self):
        src='image.pixels[id] = vec4(radiance, radiance, radiance, 1.0);'
        with self.assertRaises(ValueError):composite(src+src)
    def test_runtime_isolation(self):
        src='#include <filesystem>\n#include "../../vk_init.hpp"\n#include "../n006_interval_aware_allocation/n006_primary_axis_proxy.hpp"\n"n001_composite.spv"\n"n003_composite_software.spv"\n'+'''    impl_->context.download_device_buffer(
        impl_->image,
        out.image_rgba.data(),
        out.image_rgba.size() * sizeof(float));'''+'''
        const auto dynamic_update = update_dynamic_geometry(target_state);
        update_params(target_state);'''+'''
        const auto translated =
            options.scenario == I001Scenario::MovingRigid
                ? translated_geometry(
                    b_scene.triangles, moving.primitives, moving.delta_x)
                : b_scene.triangles;
        n006_primary_cpu->rebuild(translated);'''
        result=runtime(src)
        self.assertIn('n007_hwrt_composite.spv',result)
        self.assertIn('n007_software_composite.spv',result)
        self.assertIn('PHOS_N007_GPU_HITS',result)
        self.assertIn('PHOS_N007_GPU_PRIMARY_GEOMETRY',result)
        self.assertIn('PHOS_N007_PROBE_DIR',result)
        self.assertIn('impl_->work,',result)
        self.assertIn('impl_->hits,',result)
        self.assertIn('impl_->contributions,',result)
        self.assertIn('impl_->n006_primary_triangles, gpu_geos.data()',result)
        self.assertIn('sizeof(GpuTriangle) == 64',result)
        self.assertIn('(void)n006_refresh_software_primary();',result)
        self.assertLess(result.index('n006_refresh_software_primary();'),
                        result.index('update_params(target_state);'))
        self.assertEqual(result.count('n006_refresh_software_primary();'),1)
        self.assertIn('const auto& translated = b_scene.triangles;',result)
        self.assertNotIn('translated_geometry(\n                    b_scene.triangles, moving.primitives, moving.delta_x)',result)
        self.assertEqual(result.count('n006_primary_cpu->rebuild(translated);'),1)
        self.assertIn('#include "vk_init.hpp"',result)
        self.assertIn('#include "research/n006_interval_aware_allocation/n006_primary_axis_proxy.hpp"',result)
        self.assertNotIn('#include "../../vk_init.hpp"',result)
        self.assertIn('static_assert(sizeof(GpuHit) == 32)',result)
if __name__=='__main__':
    unittest.main()
