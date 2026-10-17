#!/usr/bin/env python3
"""Plan 065: resolve generated compute's pinned imported Vulkan header."""
import json
import build_contiguous_c7_capture as B


def main():
    original_generated = B.generated_sources
    old_work = B.WORK.parent / 'contiguous-c7-build-v2'
    B.PLAN = B.RESULTS.parent / 'experiments/065-contiguous-import-header-repair.md'
    B.WORK = B.WORK.parent / 'contiguous-c7-build-v3'
    B.OUTPUT = B.RESULTS / '206-contiguous-c7-import-repair-build.json'
    if B.WORK.exists() or B.OUTPUT.exists():
        raise ValueError('refuse existing corrected build')
    prior = json.loads(B.read(B.RESULTS / '205-contiguous-c7-decoder-repair-build.json'))
    if not prior['complete'] or prior['all_pass'] or [s['returncode'] for s in prior['steps']] != [0, 0, 1]:
        raise ValueError('exact terminal compute compiler failure required')
    if 'redefinition' not in prior['steps'][-1]['stderr']:
        raise ValueError('different original build failure')
    for path, digest in prior['input_sha256'].items():
        B.read(path, digest)
    for path in old_work.iterdir():
        if path.is_file():
            B.read(path)
    B.read(__file__)

    def repaired(originals):
        generated, pairs = original_generated(originals)
        changes = [
            ('return n010_decode_frame({});', 'return n010_decode_frame(false,{});'),
            ('return n010_decode_frame(dynamic_update);', 'return n010_decode_frame(target_state,dynamic_update);'),
            ('I001FrameResult n010_decode_frame(const DynamicUpdateStats& dynamic_update)',
             'I001FrameResult n010_decode_frame(bool target_state,const DynamicUpdateStats& dynamic_update)')]
        generated['runtime'] = B.overlay(generated['runtime'], changes)
        pairs['runtime'].extend(changes)
        includes = [('#include "../lane_b_traversal/b002_vulkan.hpp"',
                     '#include "imported/lane_b_traversal/b002_vulkan.hpp"')]
        generated['compute'] = B.overlay(generated['compute'], includes)
        pairs['compute'].extend(includes)
        return generated, pairs

    B.generated_sources = repaired
    B.main()


if __name__ == '__main__':
    main()
