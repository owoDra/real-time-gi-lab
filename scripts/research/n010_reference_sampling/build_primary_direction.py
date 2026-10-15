#!/usr/bin/env python3
"""Build plan-043 offline sampling variants with reversible source overlays."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_point_guided_prefix import overlay
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files

PLAN = RESULTS.parent/'experiments/043-prospective-primary-direction-reference-sampling.md'

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing primary-direction build')
    inputs = {str(p.resolve()): sha(p) for p in (Path(__file__), PLAN,
        Path(__file__).with_name('primary_direction_guide.inc'),
        SCRIPTS/'generate_cached_oracle.py', SCRIPTS/'generate_rqmc_oracle.py',
        SCRIPTS/'generate_point_guided_prefix.py', SCRIPTS/'generate_incremental_oracle.py',
        ROOT/'src/research/n008_hdr_oracle/n008_oracle.hpp',
        ROOT/'src/research/n008_hdr_oracle/n008_oracle_main.cpp')}
    result = {'schema': 'n010-primary-direction-build/1', 'complete': False, 'all_pass': False,
        'gpu_run': False, 'eligible_for_references': False, 'input_sha256': inputs,
        'source_commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        'constants': {'cosine_branch_probability': 0.5, 'bins': 256, 'pilot_rays_per_primary': 1024},
        'steps': [], 'scope': 'CPU sampling-only standalone/prefix build; no physical or reference admission'}
    a.work = a.work.resolve(); a.work.mkdir(parents=True)
    def save():
        a.output.write_text(json.dumps(result, indent=2)+'\n')
    save()
    try:
        standalone = a.work/'standalone'
        command = [sys.executable, str(SCRIPTS/'generate_cached_oracle.py'), '--out', str(standalone)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        path = standalone/'n010_rqmc_oracle.hpp'; original = path.read_text()
        guide = Path(__file__).with_name('primary_direction_guide.inc').read_text()
        pairs = [
            ('private:\n    const Scene& scene_;', 'private:\n'+guide+'\n    const Scene& scene_;'),
            ('                emitter_cdf_.push_back(emitter_area_);\n            }\n        }\n    }',
             '                emitter_cdf_.push_back(emitter_area_);\n            }\n        }\n'
             '        direction_guides_.resize(size_t(scene_.width)*scene_.height);\n    }'),
            ('    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{};',
             '    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{}, proposal_null_samples{};'),
            ('            ray = {origin, cosine_sample(n, n010_u1, n010_u2)};',
             '            if(bounce==0) {\n'
             '                const auto& guide=primary_direction_guide(x,y,origin,n,hit.tri);\n'
             '                const auto draw=primary_direction_sample(guide,n,n010_u1,n010_u2);\n'
             '                for(int channel=0;channel<3;++channel)throughput[channel]*=draw.correction;\n'
             '                ray={origin,draw.direction};\n'
             '            } else ray = {origin, cosine_sample(n, n010_u1, n010_u2)};'),
            ('    double offset() const { return offset_; }',
             '    double offset() const { return offset_; }\n'
             '    uint64_t direction_guide_pilot_rays() const {\n'
             '        uint64_t count=0;for(const auto& guide:direction_guides_)count+=guide.ready?1024:0;return count;\n    }')]
        text = original
        for old, new in pairs:
            text = once(text, old, new)
        restored = text
        for old, new in reversed(pairs):
            restored = once(restored, new, old)
        if restored != original:
            raise ValueError('source changed outside sampling/diagnostic overlays')
        result['geometry_light_transport_source_unchanged'] = True
        result['cached_original_header_sha256'] = sha(path)
        path.write_text(text)
        path = standalone/'n010_rqmc_main.cpp'; text = path.read_text()
        text = once(text, 'n010-rqmc-digital-shift', 'n010-rqmc-primary-direction-mixture')
        text = once(text, '\\"backface_absorbed\\":%llu,\\"cpu_seconds_diagnostic\\":%.3f}',
            '\\"backface_absorbed\\":%llu,\\"proposal_null_samples\\":%llu,\\"cpu_seconds_diagnostic\\":%.3f}')
        text = once(text, 'static_cast<unsigned long long>(counters.backface_absorbed), secs);',
            'static_cast<unsigned long long>(counters.backface_absorbed),\n'
            '                        static_cast<unsigned long long>(counters.proposal_null_samples), secs);')
        text = once(text, '        std::printf("]}\\n");',
            '        std::printf("],\\"direction_guide_pilot_rays\\":%llu}\\n",\n'
            '                    static_cast<unsigned long long>(oracle.direction_guide_pilot_rays()));')
        path.write_text(text)
        prefix = a.work/'prefix'; prefix.mkdir()
        for name in ('n010_rqmc_oracle.hpp','n010_rqmc_main.cpp'):
            shutil.copyfile(standalone/name, prefix/name)
        overlay(prefix)
        result['sampling_physical_source_bytes_equal'] = True
        for directory, name in ((standalone, 'n010_primary_direction_oracle'), (prefix, 'n010_primary_direction_prefix')):
            command = ['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread',
                '-I',str(ROOT/'src/research/n008_hdr_oracle'),str(directory/'n010_rqmc_main.cpp'),'-o',str(directory/name)]
            proc = subprocess.run(command, text=True, capture_output=True)
            result['steps'].append({'command': command, 'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr})
            save()
            if proc.returncode:
                raise ValueError('primary-direction compiler failed; retain outputs')
        result['generated_sha256'] = {p.name:sha(p) for p in standalone.iterdir() if p.is_file()}
        result['prefix_generated_sha256'] = {p.name:sha(p) for p in prefix.iterdir() if p.is_file()}
        check_files(inputs, {})
        result['all_pass'] = True
    except (ValueError, OSError, KeyError, AssertionError, subprocess.CalledProcessError) as error:
        result['failure'] = str(error)
    result['complete'] = True; save()
    print(json.dumps({'all_pass':result['all_pass'],'failure':result.get('failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)
