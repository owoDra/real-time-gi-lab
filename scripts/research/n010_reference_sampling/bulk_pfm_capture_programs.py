"""Plan 048 source overlays and provenance; no GPU or build at import time."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/048-prospective-bulk-pfm-calibration-output.md'
V2_BUILDER = HERE/'build_minimal_calibration_capture_v2.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('bulk PFM source guard differs: '+old[:80])
    return source.replace(old, new, 1)


def pairs():
    return {
        'capture': [('''    for(auto y=h;y-->0;)for(std::uint32_t x=0;x<w;++x) {
        const float v=values[std::size_t(y)*w+x];
        const float pixel[3]{v,v,v};
        out.write(reinterpret_cast<const char*>(pixel),sizeof(pixel));
    }''', '''    std::vector<float> row(std::size_t(w)*3U);
    for(auto y=h;y-->0;) {
        for(std::uint32_t x=0;x<w;++x) {
            const float v=values[std::size_t(y)*w+x];
            row[std::size_t(x)*3U]=v;
            row[std::size_t(x)*3U+1U]=v;
            row[std::size_t(x)*3U+2U]=v;
        }
        out.write(reinterpret_cast<const char*>(row.data()),std::streamsize(row.size()*sizeof(float)));
    }''')],
        'pt': [('''    for(uint32_t y=h;y-->0;) for(uint32_t x=0;x<w;++x) {
        float v=image[4*(size_t(y)*w+x)+component];
        const float rgb[]{v,v,v}; f.write(reinterpret_cast<const char*>(rgb),sizeof(rgb));
    }''', '''    std::vector<float> row(size_t(w)*3U);
    for(uint32_t y=h;y-->0;) {
        for(uint32_t x=0;x<w;++x) {
            const float v=image[4*(size_t(y)*w+x)+component];
            row[size_t(x)*3U]=v;
            row[size_t(x)*3U+1U]=v;
            row[size_t(x)*3U+2U]=v;
        }
        f.write(reinterpret_cast<const char*>(row.data()),std::streamsize(row.size()*sizeof(float)));
    }''')],
    }


def require_no_gpu_worker():
    scripts = {'calibrate_renderer.py', 'calibrate_minimal_capture.py', 'calibrate_bulk_pfm_capture.py',
        'acquire_ddgi_bringup.py', 'acquire_pt_pilot.py', 'acquire_dynamic_pilot.py',
        'acquire_rc_pilot.py', 'acquire_corpus.py'}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            name = (p/'comm').read_text().strip()
            args = (p/'cmdline').read_bytes().split(b'\0')
        except OSError:
            continue
        words = [a.decode(errors='replace') for a in args if a]
        allowed_cpu = (
            bool(words) and words[0] in {
                str(ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1/standalone/n010_primary_direction_oracle'),
                str(ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1/prefix/n010_primary_direction_prefix')}) or any(
            Path(w).name in {'recover_primary_direction_physical.py', 'validate_recovered_primary_direction_prefix.py',
                            'acquire_recovered_primary_direction_feasibility.py', 'qualify_recovered_primary_direction_references.py'}
            for w in words)
        if (name.startswith('phos-') or (name.startswith('n010_') and not allowed_cpu)
            or any(Path(w).name in scripts for w in words)):
            raise ValueError('GPU research/calibration still active: '+p.name+' '+name)


def require_build_paths(work, output):
    if (work.resolve() != ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v3'
        or output.resolve() != RESULTS/'167-bulk-pfm-calibration-fixture-build.json'):
        raise ValueError('bulk PFM fixture requires registered fresh paths')


def validate_v2(generated, inputs):
    from qualify_hybrid_references import check_files
    proof_path = RESULTS/'159-minimal-calibration-directory-fix-build.json'
    proof = json.loads(proof_path.read_text())
    inputs[str(proof_path)] = sha(proof_path)
    if (not proof['complete'] or not proof['all_pass'] or not proof['source_inverse_proof']
        or not proof['active_inputs_byte_unchanged']):
        raise ValueError('v2 source/build proof missing')
    check_files(proof['input_sha256'], inputs)
    baseline = ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v2'
    check_files({str(baseline/name): h for name, h in proof['generated_sha256'].items()}, inputs)
    for key in ('runtime', 'capture', 'pt'):
        restored = generated[key]
        for old, new in reversed(pairs().get(key, [])):
            restored = once(restored, new, old)
        if restored != (baseline/('minimal_'+key+'.cpp')).read_text():
            raise ValueError('changes beyond row writers relative to exact v2 source')


def build_program():
    if sha(V2_BUILDER) != 'f43fe3ae0d924b3d84b5be21d81aaab7786527f35da9a6683b2cb8362d332b8c':
        raise ValueError('frozen v2 builder changed')
    captured = []
    namespace = {'__name__': '__main__', '__file__': str(V2_BUILDER),
        'exec': lambda code, scope: captured.append(scope)}
    exec(compile(V2_BUILDER.read_text(), str(V2_BUILDER)+'#source-only', 'exec'), namespace)
    if len(captured) != 1:
        raise ValueError('v2 source assembly shape differs')
    source = namespace['source']
    source = once(source, 'Plan 044: isolated image/scratch calibration fixture; no GPU dispatch.',
        'Plan 048: isolated row-bulk PFM calibration fixture; no GPU dispatch.')
    source = once(source, '045-minimal-capture-output-directory-repair.md', PLAN.name)
    source = once(source, '    a = ap.parse_args()',
        '    a = ap.parse_args()\n    _require_build_paths(a.work,a.output)\n    _require_no_gpu()')
    source = once(source, 'Path(__file__),Path(_original_builder),',
        'Path(__file__),Path(_original_builder),Path(_v2_builder),Path(_bulk_helper),')
    source = once(source, '    generated = {key:overlay(originals[key],pairs)',
        "    capture_pairs += _bulk_pairs()['capture']\n    pt_pairs += _bulk_pairs()['pt']\n"
        '    generated = {key:overlay(originals[key],pairs)')
    source = once(source, '    # These entire methods/loops must remain byte-identical, not only their shaders.',
        '    _validate_v2(generated,inputs)\n'
        '    # These entire methods/loops must remain byte-identical, not only their shaders.')
    source = once(source, 'n010-minimal-calibration-fixture-build/2', 'n010-minimal-calibration-fixture-build/3')
    scope = dict(captured[0])
    scope.update(_v2_builder=str(V2_BUILDER), _bulk_helper=str(Path(__file__).resolve()),
        _bulk_pairs=pairs, _validate_v2=validate_v2, _require_build_paths=require_build_paths,
        _require_no_gpu=require_no_gpu_worker)
    return source, scope
