#!/usr/bin/env python3
"""Plan 056: build isolated cached-cosine binaries with nested bit scrambling."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_point_guided_prefix import overlay
from generate_rqmc_oracle import once
from qualify_hybrid_references import check_files
from reference_provenance import ROOT, RESULTS, sha

PLAN = RESULTS.parent/'experiments/056-prospective-nested-scramble-reference-sampling.md'

OLD_UNIFORM = '''        const auto shift = std::uint32_t(mix(seed_ ^ mix(pixel_) ^ mix(dim_ + 0x4e303130ULL)));
        const auto x = net[std::size_t(sample_) * dimensions + dim_++] ^ shift;
        return (double(x) + 0.5) * 0x1p-32;'''

NEW_UNIFORM = '''        // Plan 056: each node is keyed by depth and ORIGINAL input prefix.
        const auto key = mix(seed_ ^ mix(pixel_) ^ mix(dim_ + 0x4e303130ULL));
        const auto x = net[std::size_t(sample_) * dimensions + dim_++];
        std::uint64_t node=1;
        std::uint32_t scrambled=0;
        for(int bit=31;bit>=0;--bit) {
            const auto input_bit=(x>>bit)&1U;
            const auto flip=std::uint32_t(mix(key^node)&1ULL);
            scrambled=(scrambled<<1)|(input_bit^flip);
            node=(node<<1)|input_bit;
        }
        return (double(scrambled) + 0.5) * 0x1p-32;'''


def inverse(text, pairs, original):
    for old, new in reversed(pairs):
        text = once(text, new, old)
    if text != original:
        raise ValueError('whole original source inverse differs')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing nested-scramble build')
    dependencies = [Path(__file__), PLAN,
        HERE/'nested_scramble_programs.py', HERE/'validate_nested_scramble.py',
        HERE/'validate_nested_scramble_prefix.py', HERE/'acquire_nested_scramble_feasibility.py',
        HERE/'run_primary_direction_sequence.py',
        SCRIPTS/'generate_cached_oracle.py', SCRIPTS/'generate_rqmc_oracle.py',
        SCRIPTS/'generate_point_guided_prefix.py', SCRIPTS/'generate_incremental_oracle.py',
        ROOT/'src/research/n008_hdr_oracle/n008_oracle.hpp',
        ROOT/'src/research/n008_hdr_oracle/n008_oracle_main.cpp']
    inputs = {str(p.resolve()):sha(p) for p in dependencies}
    result = {'schema':'n010-nested-scramble-oracle-build/1','complete':False,'all_pass':False,
        'gpu_run':False,'eligible_for_references':False,'input_sha256':inputs,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'constants':{'scramble_bits':32,'original_sobol_dimensions':16,
            'pilot_paths':0,'scored_paths_per_spp':1,'proposal_null_samples':0},
        'steps':[], 'limits':{'address_space_bytes':4*1024**3,'cpu_seconds':21600,
            'elapsed_seconds_per_compilation':3600},
        'scope':'Isolated offline compilation only; no runtime correctness, statistical qualification or Renderer promotion'}
    a.work = a.work.resolve(); a.work.mkdir(parents=True)
    def save(): a.output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        standalone = a.work/'standalone'
        subprocess.run([sys.executable,str(SCRIPTS/'generate_cached_oracle.py'),
            '--out',str(standalone)],check=True,capture_output=True,text=True)
        path = standalone/'n010_rqmc_oracle.hpp'; original = path.read_text()
        pairs = [(OLD_UNIFORM,NEW_UNIFORM),
            ('    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{};',
             '    std::uint64_t primary_hits{}, shadow_tests{}, shadow_blocked{}, backface_absorbed{}, proposal_null_samples{};')]
        text = original
        for old,new in pairs: text = once(text,old,new)
        inverse(text,pairs,original)
        result['cached_original_header_sha256'] = sha(path)
        path.write_text(text)
        result['geometry_light_transport_source_unchanged'] = True
        result['whole_header_inverse_exact'] = True
        path = standalone/'n010_rqmc_main.cpp'; original = path.read_text()
        pairs = [('n010-rqmc-digital-shift','n010-rqmc-nested-prefix-hash'),
            ('\\"backface_absorbed\\":%llu,\\"cpu_seconds_diagnostic\\":%.3f}',
             '\\"backface_absorbed\\":%llu,\\"proposal_null_samples\\":%llu,\\"cpu_seconds_diagnostic\\":%.3f}'),
            ('static_cast<unsigned long long>(counters.backface_absorbed), secs);',
             'static_cast<unsigned long long>(counters.backface_absorbed),\n'
             '                        static_cast<unsigned long long>(counters.proposal_null_samples), secs);')]
        text = original
        for old,new in pairs: text = once(text,old,new)
        inverse(text,pairs,original)
        result['cached_original_main_sha256'] = sha(path)
        path.write_text(text)
        result['whole_main_inverse_exact'] = True
        prefix = a.work/'prefix'; prefix.mkdir()
        for name in ('n010_rqmc_oracle.hpp','n010_rqmc_main.cpp'):
            shutil.copyfile(standalone/name,prefix/name)
        overlay(prefix)
        result['sampling_physical_source_bytes_equal'] = True
        for directory,name in ((standalone,'n010_owen_oracle'),(prefix,'n010_owen_prefix')):
            command = ['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread',
                '-I',str(ROOT/'src/research/n008_hdr_oracle'),
                str(directory/'n010_rqmc_main.cpp'),'-o',str(directory/name)]
            receipt_path = directory/'compiler-resource-limits.json'
            def limits():
                resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                resource.setrlimit(resource.RLIMIT_CPU,(21600,)*2)
                ticks = int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19])
                receipt_path.write_text(json.dumps({'pid':os.getpid(),'start_ticks':ticks,
                    'address_space':list(resource.getrlimit(resource.RLIMIT_AS)),
                    'cpu':list(resource.getrlimit(resource.RLIMIT_CPU)),'command':command})+'\n')
            started = time.monotonic()
            proc = subprocess.run(command,text=True,capture_output=True,timeout=3600,preexec_fn=limits)
            result['steps'].append({'command':command,'returncode':proc.returncode,
                'stdout':proc.stdout,'stderr':proc.stderr,'wall_seconds_diagnostic':time.monotonic()-started,
                'resource_receipt_sha256':sha(receipt_path)})
            save()
            if proc.returncode: raise ValueError('compiler failed; retain without retry')
        result['generated_sha256'] = {p.name:sha(p) for p in standalone.iterdir() if p.is_file()}
        result['prefix_generated_sha256'] = {p.name:sha(p) for p in prefix.iterdir() if p.is_file()}
        check_files(inputs,{})
        result['all_pass'] = True
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result['failure'] = str(error)
    result['complete'] = True; save()
    print(json.dumps({'all_pass':result['all_pass'],'failure':result.get('failure')}))
    return 0 if result['all_pass'] else 2


if __name__=='__main__': raise SystemExit(main())
