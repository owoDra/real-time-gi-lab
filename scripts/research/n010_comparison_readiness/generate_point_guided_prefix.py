#!/usr/bin/env python3
"""Separate prefix overlay on the exact, retained point-guided build 112."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from generate_incremental_oracle import LOADER
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files


def overlay(directory):
    path = directory/'n010_rqmc_oracle.hpp'
    old = path.read_text()
    text = once(old, '                                   std::vector<std::vector<PixelStats>>* snapshots = nullptr) const {',
        '                                   std::vector<std::vector<PixelStats>>* snapshots = nullptr,\n'
        '                                   uint32_t start_spp=0, const std::vector<PixelStats>* initial=nullptr) const {')
    text = once(text, '        std::vector<PixelStats> stats(std::size_t(scene_.width) * scene_.height);',
        '        std::vector<PixelStats> stats = initial ? *initial : std::vector<PixelStats>(std::size_t(scene_.width) * scene_.height);\n'
        '        if(start_spp>=spp || stats.size()!=std::size_t(scene_.width)*scene_.height)\n'
        '            throw std::runtime_error("invalid incremental prefix");')
    text = once(text, '                        for (std::uint32_t s = 0; s < spp; ++s) {',
        '                        for (std::uint32_t s = start_spp; s < spp; ++s) {')
    text = once(text, 'primary && s == 0 ? &(*primary)[pixel] : nullptr, &cache);',
        'primary && s == start_spp ? &(*primary)[pixel] : nullptr, &cache);')
    # All physical/sampling methods surrounding render must remain byte equal.
    if (old.split('    std::vector<PixelStats> render(')[0] != text.split('    std::vector<PixelStats> render(')[0]
        or old[old.index('    const Bvh& bvh()'):] != text[text.index('    const Bvh& bvh()'):]):
        raise ValueError('sampling/physical implementation changed outside render continuation')
    path.write_text(text)
    loader = once(LOADER, 'uint64_t values[4]{};', 'uint64_t values[5]{};')
    loader = once(loader, 'for(int k=0;k<4;++k)', 'for(int k=0;k<5;++k)')
    loader = once(loader, 'count.shadow_blocked=values[2];count.backface_absorbed=values[3];result.push_back(count);',
        'count.shadow_blocked=values[2];count.backface_absorbed=values[3];\n'
        '        count.proposal_null_samples=values[4];result.push_back(count);')
    path = directory/'n010_rqmc_main.cpp'
    text = path.read_text()
    text = once(text, 'int main(int argc, char** argv) {', loader+'\nint main(int argc, char** argv) {')
    text = once(text, '        std::vector<std::uint32_t> checkpoints;',
        '        std::string prefix_path,prefix_counter_text;uint32_t prefix_spp{};\n'
        '        std::vector<std::uint32_t> checkpoints;')
    text = once(text, '            else if (a == "--checkpoints") {',
        '            else if(a=="--resume-prefix")prefix_path=value();\n'
        '            else if(a=="--resume-spp")prefix_spp=uint32_t(std::stoul(value()));\n'
        '            else if(a=="--resume-counters")prefix_counter_text=value();\n'
        '            else if (a == "--checkpoints") {')
    text = once(text, '        for (std::size_t i = 0; i < checkpoints.size(); ++i)',
        '        std::vector<RenderCounters> prefix_counters;\n'
        '        if(!prefix_path.empty()) {\n'
        '            if(prefix_spp==0 || prefix_spp>=spp || !checkpoints.empty())\n'
        '                throw std::runtime_error("invalid prefix/checkpoint combination");\n'
        '            prefix_counters=parse_prefix_counters(prefix_counter_text);\n'
        '            if(prefix_counters.size()!=seeds.size())throw std::runtime_error("prefix seed counter count");\n'
        '        } else if(prefix_spp || !prefix_counter_text.empty())throw std::runtime_error("missing prefix path");\n'
        '        for (std::size_t i = 0; i < checkpoints.size(); ++i)')
    text = once(text, '            RenderCounters counters;',
        '            RenderCounters counters = prefix_path.empty() ? RenderCounters{} : prefix_counters[si];\n'
        '            std::vector<PixelStats> initial;\n'
        '            if(!prefix_path.empty())initial=read_prefix(prefix_path+".s"+std::to_string(si)+".f64",scene,seeds[si],prefix_spp);')
    text = once(text, '                                             checkpoints, &snapshots);',
        '                                             checkpoints, &snapshots, prefix_path.empty()?0:prefix_spp, prefix_path.empty()?nullptr:&initial);')
    path.write_text(text)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing prefix build attempt')
    inputs = {}
    base = read(RESULTS/'112-point-guided-oracle-build.json', inputs)
    if not base['complete'] or not base['all_pass']:
        raise ValueError('point-guided base build incomplete/failed')
    check_files(base['input_sha256'], inputs)
    source = ROOT/'out/research/n010-comparison-readiness/point-guided-oracle-build-v1'
    check_files({str(source/name): h for name, h in base['generated_sha256'].items()}, inputs)
    for path in (Path(__file__), Path(__file__).with_name('generate_incremental_oracle.py'),
                 RESULTS.parent/'experiments/031-point-guided-state-and-prefix-validation.md'):
        inputs[str(path.resolve())] = sha(path)
    result = {'schema': 'n010-point-guided-prefix-build/1', 'complete': False, 'all_pass': False,
        'gpu_run': False, 'eligible_for_references': False, 'input_sha256': inputs,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'steps': [], 'scope': 'Standalone prefix build, no runtime prefix or physical proof'}
    try:
        a.work.mkdir(parents=True)
        for name in ('n010_rqmc_oracle.hpp', 'n010_rqmc_main.cpp'):
            shutil.copyfile(source/name, a.work/name)
        overlay(a.work)
        result['sampling_physical_source_bytes_equal'] = True
        command = ['c++', '-std=c++20', '-O3', '-fno-fast-math', '-ffp-contract=off', '-pthread',
            '-I', str(ROOT/'src/research/n008_hdr_oracle'), str(a.work/'n010_rqmc_main.cpp'),
            '-o', str(a.work/'n010_point_guided_prefix')]
        proc = subprocess.run(command, text=True, capture_output=True)
        result['steps'].append({'command': command, 'returncode': proc.returncode,
            'stdout': proc.stdout, 'stderr': proc.stderr})
        result['all_pass'] = proc.returncode == 0
        result['generated_sha256'] = {p.name: sha(p) for p in a.work.iterdir() if p.is_file()}
        check_files(inputs, {})
    except (ValueError, OSError) as error:
        result['failure'] = str(error)
        result['all_pass'] = False
    result['complete'] = True
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    raise SystemExit(0 if result['all_pass'] else 2)
