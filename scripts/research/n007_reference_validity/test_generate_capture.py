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
        src='#include <filesystem>\n"n001_composite.spv"\n"n003_composite_software.spv"\n'+'''    impl_->context.download_device_buffer(
        impl_->image,
        out.image_rgba.data(),
        out.image_rgba.size() * sizeof(float));'''
        result=runtime(src)
        self.assertIn('n007_hwrt_composite.spv',result)
        self.assertIn('n007_software_composite.spv',result)
        self.assertIn('PHOS_N007_GPU_HITS',result)
        self.assertIn('static_assert(sizeof(GpuHit) == 32)',result)
if __name__=='__main__':
    unittest.main()
