#!/usr/bin/env python3
"""Build separate prefix-capable host; no runtime or reference-admission claim."""
import argparse
import json
from pathlib import Path
from diagnose_gpu_deep_sampling import BASE, LANE, ROOT, invoke, replace_once, sha

RESTORE = r'''
static void restore_prefix(const N::Scene& scene,uint64_t seed,uint32_t spp,const fs::path& f64,const fs::path& raw,std::vector<GStats>& values){
    size_t pixels=size_t(scene.width)*scene.height;
    std::ifstream file(f64,std::ios::binary|std::ios::ate),stats(raw,std::ios::binary|std::ios::ate);
    if(!file||!stats||file.tellg()!=std::streamoff(28+pixels*192)||stats.tellg()!=std::streamoff(pixels*sizeof(GStats)))throw std::runtime_error("prefix file/length mismatch");
    file.seekg(0);stats.seekg(0);char magic[8];uint32_t shape[3];uint64_t oldseed;
    file.read(magic,8);file.read(reinterpret_cast<char*>(shape),12);file.read(reinterpret_cast<char*>(&oldseed),8);
    if(std::memcmp(magic,"N008F64\0",8)||shape[0]!=scene.width||shape[1]!=scene.height||shape[2]!=spp||oldseed!=seed)throw std::runtime_error("prefix frame/seed/SPP mismatch");
    std::vector<GStats> saved(pixels);stats.read(reinterpret_cast<char*>(saved.data()),pixels*sizeof(GStats));
    for(size_t p=0;p<pixels;++p){double samples[24];file.read(reinterpret_cast<char*>(samples),sizeof samples);
        for(int k=0;k<4;++k)for(int c=0;c<3;++c){double a=samples[k*3+c]*spp,b=samples[12+k*3+c]*spp;
            if(!std::isfinite(a)||!std::isfinite(b)||std::bit_cast<uint64_t>(a)!=std::bit_cast<uint64_t>(saved[p].sum[k].v[c])||std::bit_cast<uint64_t>(b)!=std::bit_cast<uint64_t>(saved[p].sum2[k].v[c]))throw std::runtime_error("prefix moment/sum is not exact");
            values[p].sum[k].v[c]=a;values[p].sum2[k].v[c]=b;}
        for(int k=0;k<4;++k)values[p].counters[k]=saved[p].counters[k];
    }
    if(!file||!stats)throw std::runtime_error("prefix read failure");
}
'''


def run(args):
    if args.work.exists()or args.output.exists():raise ValueError('refuse existing prefix build')
    args.work.mkdir(parents=True)
    prior=BASE/'hybrid-oracle-build-v1'
    proof=LANE/'results/095-hybrid-oracle-build.json';d=json.loads(proof.read_text())
    if not d.get('all_pass')or any(sha(prior/n)!=h for n,h in d['generated_sha256'].items()):raise ValueError('base candidate build differs')
    original=prior/'hybrid.cpp';plan=LANE/'experiments/028-hybrid-state-and-prefix-validation.md'
    report=dict(schema='n010-hybrid-prefix-build/1',complete=False,all_pass=False,gpu_run=False,eligible_for_references=False,
                input_sha256={str(p.relative_to(ROOT)):sha(p)for p in (original,proof,plan,Path(__file__))},steps=[])
    try:
        host=original.read_text()
        host='#include <bit>\n'+host
        host=replace_once(host,'static void execute(',RESTORE+'\nstatic void execute(')
        host=replace_once(host,'uint32_t threads,const fs::path& out)', 'uint32_t threads,const fs::path& out,const fs::path& resume_f64,uint32_t resume_spp,const fs::path& resume_stats)')
        host=replace_once(host,'    std::vector<GStats> corrected(pixels);','    std::vector<GStats> corrected(pixels);\n    if(resume_spp)restore_prefix(scene,seed,resume_spp,resume_f64,resume_stats,corrected);')
        host=replace_once(host,'for(uint32_t begin=0;begin<spp;begin+=batch)', 'for(uint32_t begin=resume_spp;begin<spp;begin+=batch)')
        host=replace_once(host,'if(argc!=9)', 'if(argc!=9 && argc!=12)')
        host=replace_once(host,'CPU_THREADS NEW_OUTPUT\\n', 'CPU_THREADS NEW_OUTPUT [RESUME_F64 RESUME_SPP RESUME_STATS]\\n')
        host=replace_once(host,'uint32_t threads=uint32_t(std::stoul(argv[7]));', 'uint32_t threads=uint32_t(std::stoul(argv[7]));uint32_t resume_spp=argc==12?uint32_t(std::stoul(argv[10])):0;fs::path resume_f64=argc==12?argv[9]:"",resume_stats=argc==12?argv[11]:"";if(argc==12 && (!resume_spp || (resume_spp&(resume_spp-1)) || spp!=2*resume_spp))throw std::runtime_error("prefix must be a complete dyadic previous level");')
        host=replace_once(host,'seed,spp,batch,threads,out);', 'seed,spp,batch,threads,out,resume_f64,resume_spp,resume_stats);')
        source=args.work/'hybrid-prefix.cpp';source.write_text(host);binary=args.work/'phos-n010-hybrid-prefix'
        build=json.loads((prior/'host-build.json').read_text())['command']
        old_binary=prior/'phos-n010-hybrid-reference'
        build=[str(source)if x in (str(original),str(original.relative_to(ROOT)))else str(binary)if x in (str(old_binary),str(old_binary.relative_to(ROOT)))else x for x in build]
        if str(source)not in build or build[-1]!=str(binary)or binary.exists():raise ValueError('requires new source/output')
        report['steps'].append(invoke(build,args.work,'host-build'))
        report['generated_sha256']={source.name:sha(source),binary.name:sha(binary)}
        report['shared_shader_sha256']=sha(prior/'hybrid.spv')
        report['all_pass']=True
        report['scope']='Separate host build only: exact dyadic mean/moment sum-bit restoration plus per-pixel counters. Kernel/base CPU transport unchanged; no runtime prefix proof, physical admission or reference transition.'
    except Exception as error:report['failure']=str(error)
    report['complete']=True;args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k)for k in ('complete','failure','all_pass')}))
    return 0 if report['all_pass']else 2


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
