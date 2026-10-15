#!/usr/bin/env python3
"""Build a separately identified CPU-only light-surface proposal and own prefix loader."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_point_guided_oracle import GUIDE as OLD_GUIDE
from generate_point_guided_prefix import overlay
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

PLAN = RESULTS.parent/'experiments/040-prospective-light-surface-reference-sampling.md'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing light-surface build')
    inputs = {}
    base = read(RESULTS/'112-point-guided-oracle-build.json', inputs)
    if not base['complete'] or not base['all_pass']:
        raise ValueError('pinned original proposal build incomplete')
    check_files(base['input_sha256'], inputs)
    old_root = ROOT/'out/research/n010-comparison-readiness/point-guided-oracle-build-v1'
    check_files({str(old_root/name): digest for name,digest in base['generated_sha256'].items()}, inputs)
    for path in (Path(__file__), Path(__file__).with_name('light_surface_guide.inc'), PLAN,
                 SCRIPTS/'generate_point_guided_oracle.py', SCRIPTS/'generate_point_guided_prefix.py',
                 SCRIPTS/'generate_incremental_oracle.py', SCRIPTS/'generate_rqmc_oracle.py'):
        inputs[str(path.resolve())] = sha(path)
    result = {'schema': 'n010-light-surface-build/1', 'complete': False, 'all_pass': False,
        'gpu_run': False, 'eligible_for_references': False, 'input_sha256': inputs,
        'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'constants': {'cosine_branch_probability': 0.75}, 'steps': [],
        'scope': 'Standalone CPU sampling prototype/prefix build only; no physical validation or reference admission'}
    args.work = args.work.resolve()
    args.work.mkdir(parents=True)
    def save():
        args.output.write_text(json.dumps(result, indent=2)+'\n')
    save()
    try:
        standalone = args.work/'standalone'; standalone.mkdir()
        for name in ('n010_rqmc_oracle.hpp','n010_rqmc_main.cpp'):
            shutil.copyfile(old_root/name, standalone/name)
        path = standalone/'n010_rqmc_oracle.hpp'
        original = path.read_text()
        guide = '\n'+Path(__file__).with_name('light_surface_guide.inc').read_text()
        old_pdf = '                const double pg=cy>0 && guide_area_[hit.tri]>0 ? guide_probability(hit.tri)*hit.t*hit.t/(guide_area_[hit.tri]*cy):0;'
        new_pdf = ('                const V3 proposal_point=ray.origin+ray.dir*hit.t;\n'
                   '                const double pg=cy>0 ? guide_area_density(hit.tri,proposal_point,ng)*hit.t*hit.t/cy:0;')
        text = once(original, OLD_GUIDE, guide)
        text = once(text, old_pdf, new_pdf)
        if once(once(text, guide, OLD_GUIDE), new_pdf, old_pdf) != original:
            raise ValueError('source changed outside the proposal/density overlay')
        result['geometry_light_transport_source_unchanged'] = True
        path.write_text(text)
        path = standalone/'n010_rqmc_main.cpp'
        path.write_text(once(path.read_text(), 'n010-rqmc-point-guided-mixture', 'n010-rqmc-light-surface-mixture'))
        prefix = args.work/'prefix'; prefix.mkdir()
        for name in ('n010_rqmc_oracle.hpp','n010_rqmc_main.cpp'):
            shutil.copyfile(standalone/name, prefix/name)
        overlay(prefix)
        result['sampling_physical_source_bytes_equal'] = True
        for directory, name in ((standalone,'n010_light_surface_oracle'), (prefix,'n010_light_surface_prefix')):
            command = ['c++','-std=c++20','-O3','-fno-fast-math','-ffp-contract=off','-pthread',
                '-I',str(ROOT/'src/research/n008_hdr_oracle'),str(directory/'n010_rqmc_main.cpp'),'-o',str(directory/name)]
            proc = subprocess.run(command, text=True, capture_output=True)
            result['steps'].append({'command': command,'returncode': proc.returncode,'stdout': proc.stdout,'stderr': proc.stderr})
            save()
            if proc.returncode:
                raise ValueError('light-surface compiler failed; retain sources/output')
        result['generated_sha256'] = {p.name:sha(p) for p in standalone.iterdir() if p.is_file()}
        result['prefix_generated_sha256'] = {p.name:sha(p) for p in prefix.iterdir() if p.is_file()}
        result['standalone_work'] = str(standalone)
        result['prefix_work'] = str(prefix)
        check_files(inputs, {})
        result['all_pass'] = True
    except (ValueError, OSError, KeyError, AssertionError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    save()
    print(json.dumps({'all_pass':result['all_pass'],'failure':result.get('failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)
