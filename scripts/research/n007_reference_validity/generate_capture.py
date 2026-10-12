#!/usr/bin/env python3
"""Fail-closed N007-only build overlays: preserve every original N001 source.

N007 packed composite: RGB = direct, probe-indirect, total. The generated
runtime alone reads back the existing primary-hit SSBO. Never substitute these
diagnostic shaders for a production image-producing renderer.
"""
from __future__ import annotations
import argparse
from pathlib import Path

SHADERS = {
    'n001_composite.comp.glsl': 'n007_hwrt_composite.comp.glsl',
    'n003_composite_software.comp.glsl': 'n007_software_composite.comp.glsl',
}

def exactly_one(source: str, old: str, new: str) -> str:
    n = source.count(old)
    if n != 1:
        raise ValueError(f'N007 source contract drift: expected one, found {n}: {old[:85]}')
    return source.replace(old, new)

def composite(source: str) -> str:
    return exactly_one(source,
        'image.pixels[id] = vec4(radiance, radiance, radiance, 1.0);',
        '// N007-only channels: R=direct, G=probe indirect, B=total.\n'
        '    image.pixels[id] = vec4(direct, indirect, radiance, 1.0);')

def runtime(source: str) -> str:
    source = exactly_one(source, '"n001_composite.spv"', '"n007_hwrt_composite.spv"')
    source = exactly_one(source, '"n003_composite_software.spv"', '"n007_software_composite.spv"')
    source = exactly_one(source, '#include <filesystem>',
                         '#include <filesystem>\n#include <cstdlib>\n#include <fstream>')
    # Generated file lives in the build tree: relative includes from the N001
    # original directory must be rebased to the configured project include root.
    source = exactly_one(source, '#include "../../vk_init.hpp"',
                         '#include "vk_init.hpp"')
    source = exactly_one(source,
        '#include "../n006_interval_aware_allocation/n006_primary_axis_proxy.hpp"',
        '#include "research/n006_interval_aware_allocation/n006_primary_axis_proxy.hpp"')
    # The historical N006 integration refreshes the SOFTWARE primary BVH for
    # target-state moving geometry *after* updating b_scene. Plain N001's
    # run_frame omits this step because it is HWRT-only. Without this isolated
    # overlay, the GPU first hits are still on the original scene while the
    # N007 CPU reference traces the translated renderer_readback() triangles.
    source = exactly_one(source,
        '''        const auto dynamic_update = update_dynamic_geometry(target_state);
        update_params(target_state);''',
        '''        const auto dynamic_update = update_dynamic_geometry(target_state);
#ifdef PHOS_GI_N006_SOFTWARE_PRIMARY
        if (target_state && uses_lane_e_final_software(options.variant))
            (void)n006_refresh_software_primary();
#endif
        update_params(target_state);''')

    # n006_refresh_software_primary() was written for an assumed object-space
    # b_scene; however update_dynamic_geometry() actually assigns the WORLD
    # translated triangles to b_scene before returning. Applying delta_x again
    # shifts the GPU BVH twice, while N007 CPU traces b_scene once-translated.
    # Bind directly to that same authoritative post-update vector; this also
    # avoids leaving GpuSoftwareBvhData::triangles_ pointing at a dead local.
    source = exactly_one(source,
        '''        const auto translated =
            options.scenario == I001Scenario::MovingRigid
                ? translated_geometry(
                    b_scene.triangles, moving.primitives, moving.delta_x)
                : b_scene.triangles;
        n006_primary_cpu->rebuild(translated);''',
        '''        const auto& translated = b_scene.triangles;
        n006_primary_cpu->rebuild(translated);''')
    marker = '''    impl_->context.download_device_buffer(
        impl_->image,
        out.image_rgba.data(),
        out.image_rgba.size() * sizeof(float));'''
    replacement = marker + '''
    // Diagnostic SSBO export: existing primary traversal remains unchanged.
    const char* n007_path = std::getenv("PHOS_N007_GPU_HITS");
    if (!n007_path || !*n007_path) {
        fail("N007 primary-hit export path is required");
    }
    static_assert(sizeof(GpuHit) == 32);
    std::vector<std::uint8_t> n007_bytes(
        std::size_t(out.width) * out.height * sizeof(GpuHit));
    impl_->context.download_device_buffer(
        impl_->primary_hits, n007_bytes.data(), n007_bytes.size());
    std::ofstream n007_out(n007_path, std::ios::binary);
    if (!n007_out) fail("N007 primary-hit capture could not open");
    n007_out.write(reinterpret_cast<const char*>(n007_bytes.data()),
                   std::streamsize(n007_bytes.size()));
    if (!n007_out) fail("N007 primary-hit capture write failed");
#ifdef PHOS_GI_N006_SOFTWARE_PRIMARY
    // Independently retrieve the GPU-visible triangles backing the software
    // primary traversal. Do NOT substitute the CPU triangle array here.
    if (uses_lane_e_final_software(impl_->options.variant)) {
        const char* geo_path = std::getenv("PHOS_N007_GPU_PRIMARY_GEOMETRY");
        if (!geo_path || !*geo_path) fail("N007 GPU primary geometry export path missing");
        static_assert(sizeof(GpuTriangle) == 64);
        std::vector<GpuTriangle> gpu_geos(out.triangles.size());
        impl_->context.download_device_buffer(
            impl_->n006_primary_triangles, gpu_geos.data(),
            gpu_geos.size() * sizeof(GpuTriangle));
        std::ofstream geo_out(geo_path, std::ios::binary);
        if (!geo_out) fail("N007 GPU primary geometry export could not open");
        geo_out.write(reinterpret_cast<const char*>(gpu_geos.data()),
                      std::streamsize(gpu_geos.size() * sizeof(GpuTriangle)));
        if (!geo_out) fail("N007 GPU primary geometry export write failed");
    }
#endif''''''
    return exactly_one(source, marker, replacement)

def generate(root: Path, out: Path) -> dict:
    shader_root = root / 'shaders/research/lane_n_end_to_end_renderer'
    runtime_path = root / 'src/research/lane_n_end_to_end_renderer/n001_runtime.cpp'
    values = {
        name: composite((shader_root / orig).read_text(encoding='utf-8'))
        for orig, name in SHADERS.items()
    }
    values['n007_runtime.cpp'] = runtime(runtime_path.read_text(encoding='utf-8'))
    out.mkdir(parents=True, exist_ok=True)
    for name, data in values.items():
        (out / name).write_text(data, encoding='utf-8')
    return {name: len(data) for name, data in values.items()}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    print(generate(args.root, args.out))

if __name__ == '__main__':
    main()
