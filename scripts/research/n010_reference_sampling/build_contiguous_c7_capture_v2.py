#!/usr/bin/env python3
"""Plan 064: retain failed 204 and pass target_state to the result decoder."""
import json
import build_contiguous_c7_capture as B


def main():
    old_generated = B.generated_sources
    old_work = B.WORK
    B.PLAN = B.RESULTS.parent / 'experiments/064-contiguous-decoder-build-repair.md'
    B.WORK = old_work.parent / 'contiguous-c7-build-v2'
    B.OUTPUT = B.RESULTS / '205-contiguous-c7-decoder-repair-build.json'
    if B.WORK.exists() or B.OUTPUT.exists():
        raise ValueError('refuse existing corrected build')
    prior = json.loads(B.read(B.RESULTS / '204-contiguous-c7-fixture-build.json'))
    if not prior['complete'] or prior['all_pass'] or len(prior['steps']) != 1 or prior['steps'][0]['returncode'] != 1:
        raise ValueError('exact terminal original compiler failure required')
    if 'target_state' not in prior['steps'][0]['stderr']:
        raise ValueError('different original build failure')
    for path, digest in prior['input_sha256'].items():
        B.read(path, digest)
    for path in old_work.iterdir():
        if path.is_file():
            B.read(path)
    B.read(__file__)

    def repaired(originals):
        generated, pairs = old_generated(originals)
        changes = [
            ('return n010_decode_frame({});', 'return n010_decode_frame(false,{});'),
            ('return n010_decode_frame(dynamic_update);', 'return n010_decode_frame(target_state,dynamic_update);'),
            ('I001FrameResult n010_decode_frame(const DynamicUpdateStats& dynamic_update)',
             'I001FrameResult n010_decode_frame(bool target_state,const DynamicUpdateStats& dynamic_update)')]
        generated['runtime'] = B.overlay(generated['runtime'], changes)
        pairs['runtime'].extend(changes)
        return generated, pairs

    B.generated_sources = repaired
    B.main()


if __name__ == '__main__':
    main()
