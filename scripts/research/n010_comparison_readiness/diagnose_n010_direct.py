#!/usr/bin/env python3
"""Post-hoc CPU hypotheses for residual N010 direct pixels; no repaired GPU PASS."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from qualify_references import ROOT, scene_for_state, L
sys.path.insert(0,str(ROOT/'scripts/research/n008_hdr_oracle'))
from phase_c_gpu_diagnostic import gpu_hits
from generate_rqmc_oracle import once

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

HELPER=r'''
o::V3 ulp4(o::V3 point,o::V3 normal) {
    float p[3]={float(point.x),float(point.y),float(point.z)};
    float n[3]={float(normal.x),float(normal.y),float(normal.z)};
    for(int a=0;a<3;++a) {
        int32_t delta=int32_t(4.0f*n[a]);
        if(p[a]<0)delta=-delta;
        float shifted=std::bit_cast<float>(std::bit_cast<uint32_t>(p[a])+uint32_t(delta));
        p[a]=std::abs(p[a])<1.0f/32.0f ? p[a]+n[a]*1.0e-7f : shifted;
    }
    return v3(p);
}
'''

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing diagnostic acquisition')
    args.work.mkdir(parents=True)
    base=ROOT/'src/research/n010_comparison_readiness/direct_diagnostic.cpp'
    source=base.read_text()
    source=once(source,'#include <cstring>','#include <cstring>\n#include <bit>')
    source=once(source,'int main(int argc,char** argv){try{',HELPER+'\nint main(int argc,char** argv){try{')
    source=once(source,'if(argc!=3)', 'if(argc!=4)')
    source=once(source,'fs::path cap=argv[1];',
                'std::ifstream canonical_input(argv[3]);if(!canonical_input)throw std::runtime_error("canonical scene open");\n'
                ' const auto canonical=o::parse_scene(canonical_input);\n'
                ' fs::path cap=argv[1];')
    source=once(source,'float target[3];for(int a=0;a<3;++a)target[a]=p.cam[a]+p.fwd[a];\n  auto fwd=o::normalize(v3(target)-cam)',
                'auto fwd=o::normalize(canonical.camera.forward)')
    source=source.replace('N008 float32 target addition then float64 forward subtraction',
                          'N010 canonical scene camera basis')
    source=source.replace('n010-direct-ray-diagnostic/2','n010-direct-ray-diagnostic/3')
    source=once(source,'for(int source=0;source<2;++source){auto pos0=source?oracle_pos:gpu_pos,n=source?oracle_n:gpu_n;',
                'auto plane_n=o::normalize(o::cross(tris[self].v1-tris[self].v0,tris[self].v2-tris[self].v0));\n'
                '  auto projected=gpu_pos-plane_n*o::dot(gpu_pos-tris[self].v0,plane_n);\n'
                '  for(int source=0;source<3;++source){auto pos0=source==1?oracle_pos:(source==2?projected:gpu_pos),n=source==1?oracle_n:gpu_n;')
    source=once(source,'for(int mode=0;mode<4;++mode)', 'for(int mode=0;mode<5;++mode)')
    source=once(source,'auto blocker=bvh.closest({org,wi},mode==0?1e-4:0.0,tmax,mode==3?invalid:self);',
                'if(mode==4) {org=ulp4(pos0,n);dist=o::length(light-org);wi=(light-org)*(1.0/dist);tmax=dist*(1.0-2.0e-7);}\n'
                '    if(mode==1) {dist=o::length(light-org);wi=(light-org)*(1.0/dist);tmax=dist*(1.0-1e-12)-eps;}\n'
                '    auto blocker=bvh.closest({org,wi},mode==0?1e-4:0.0,tmax,mode==3?invalid:(source==1?oi:self));')
    source=source.replace('(source?"oracle":"gpu_float_reconstructed")',
                          '(source==1?"oracle_double":source==2?"projected_point_counterfactual":"gpu_float_reconstructed")')
    source=source.replace('mode==2?"zero_offset_ignore_self":"zero_offset_include_self"',
                          'mode==2?"zero_offset_ignore_self":mode==3?"zero_offset_include_self":"ulp4_recomputed_shadow"')
    source=once(source,'  std::cout<<"]}";first=false;',r'''
  std::cout<<"],\"gpu_captured_normal\":";vec(v3(hit.n));
  std::cout<<",\"oracle_normal\":";vec(oracle_n);
  std::cout<<",\"gpu_source_cosine\":"<<o::dot(gpu_n,o::normalize(light-gpu_pos))
           <<",\"oracle_source_cosine\":"<<o::dot(oracle_n,o::normalize(light-oracle_pos))
           <<",\"captured_gpu_t\":"<<hit.t<<",\"canonical_reference_t\":"<<ot
           <<",\"pairwise_primary_hypothesis\":[";
  for(int camera=0;camera<2;++camera) {
   o::WatertightRay ray({cam,camera?od:v3(d)});
   double selected=ray.intersect(tris[self]),nearest=ray.intersect(tris[oi]);
   bool both=std::isfinite(selected)&&std::isfinite(nearest);
   double delta=selected-nearest;
   double selected_tol=both?std::max(2e-4,std::abs(selected)*2e-5):0;
   double nearest_tol=both?std::max(2e-4,std::abs(nearest)*2e-5):0;
   bool preferred=both&&delta>=0&&std::abs(delta)<=selected_tol&&std::abs(delta)<=nearest_tol&&hit.prim<at<uint32_t>(g,44+52*size_t(oi));
   std::cout<<(camera?",":"")<<"{\"ray\":\""<<(camera?"canonical_double":"gpu_float_reconstructed")
    <<"\",\"both_triangles_intersect\":"<<(both?"true":"false")<<",\"selected_triangle_t\":";
   if(std::isfinite(selected))std::cout<<selected;else std::cout<<"null";
   std::cout<<",\"reference_triangle_t\":";
   if(std::isfinite(nearest))std::cout<<nearest;else std::cout<<"null";
   std::cout<<",\"distance_difference\":";
   if(both)std::cout<<delta;else std::cout<<"null";
   std::cout<<",\"selected_tolerance\":"<<selected_tol<<",\"reference_tolerance\":"<<nearest_tol
    <<",\"legacy_pair_rule_prefers_farther_gpu_primitive_in_both_orders\":"<<(preferred?"true":"false")<<'}';
  }
  std::cout<<"]}";first=false;''')
    generated=args.work/'direct_n010.cpp'
    generated.write_text(source)
    binary=args.work/'direct_n010'
    command=['c++','-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-I',str(ROOT/'src/research/n008_hdr_oracle'),str(generated),'-o',str(binary)]
    build=subprocess.run(command,capture_output=True,text=True)
    result={'schema':'n010-residual-direct-cpu-diagnostic/1','classification':'POST_HOC_CPU_DIAGNOSIS',
            'complete':False,'gpu_run':False,'historical_outcomes_revised':False,
            'remaining_max_relative_error_1_pixels':'UNRESOLVED',
            'limitations':'GPU float hit positions/rays are reconstructed, not exported. Double BVH hypotheses and point projection do not emulate GPU intersection or prove a repair.',
            'build_command':command,'build_returncode':build.returncode,'build_stderr':build.stderr,
            'base_source_sha256':sha(base),'generated_source_sha256':sha(generated),'script_sha256':sha(Path(__file__)),'rows':[]}
    if build.returncode:
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        raise SystemExit('diagnostic build failure retained')
    result['binary_sha256']=sha(binary)
    evidence=ROOT/'research/lanes/n010-comparison-readiness/results/011-rc-correctness-pilot.json'
    result['capture_evidence_sha256']=sha(evidence)
    result['primary_shader_source_sha256']={name:sha(ROOT/'shaders/research/lane_n_end_to_end_renderer'/name)
        for name in ('n001_primary.comp.glsl','n003_primary_software.comp.glsl')}
    corpus=json.loads(evidence.read_text())
    for row in corpus['rows']:
        if row['cell']!='C1' or row['backend'] not in ('hwrt','software'):
            continue
        capture=Path(row['command'][row['command'].index('--out')+1])
        for name,digest in row['payload_sha256'].items():
            if sha(capture/name)!=digest:
                raise ValueError('original capture payload changed: '+name)
        reference=ROOT/'out/research/n010-comparison-readiness/references-v1/C1_T_B2'
        qualification=reference/'qualification.json'
        q=json.loads(qualification.read_text())
        for name,digest in q['levels'][-1]['all_payload_sha256'].items():
            if sha(reference/name)!=digest:
                raise ValueError('reference payload changed: '+name)
        state=L.read_state(capture)
        scene=scene_for_state(state,2)
        if hashlib.sha256(scene.text().encode()).hexdigest()!=q['scene_sha256']:
            raise ValueError('capture/reference physical scene mismatch')
        spp=q['levels'][-1]['spp']
        means=np.mean([L.read_sidecar(reference/f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)],axis=0)
        r=means[...,1,0].ravel()
        g=L.read_pfm(capture/'gpu/direct.pfm')[...,0].ravel()
        ids=np.flatnonzero((r>0)&(g<=0))
        oracle_hits=np.frombuffer((reference/f'o.n{spp}.hits').read_bytes(),
                                 dtype=[('t','<f8'),('tri','<u4'),('front','<u4')],offset=16)
        hits=gpu_hits(capture/'gpu/hits.bin',len(r))
        path=args.work/(row['backend']+'.pixels.tsv')
        path.write_text(''.join(f'{i} {oracle_hits["t"][i]:.17g} {oracle_hits["tri"][i]} {g[i]:.17g} {r[i]:.17g}\n' for i in ids))
        process=subprocess.run([str(binary),str(capture),str(path),str(reference/'scene.n008')],capture_output=True,text=True)
        (args.work/(row['backend']+'.stdout.json')).write_text(process.stdout)
        (args.work/(row['backend']+'.stderr.log')).write_text(process.stderr)
        value={'backend':row['backend'],'returncode':process.returncode,
               'qualification_sha256':sha(qualification),'direct_image_sha256':sha(capture/'gpu/direct.pfm'),
               'gpu_hit_sha256':sha(capture/'gpu/hits.bin'),
               'reference_scene_sha256':sha(reference/'scene.n008'),
               'reference_f64_sha256':{f'o.n{spp}.s{i}.f64':sha(reference/f'o.n{spp}.s{i}.f64') for i in range(4)},
               'reference_primary_hit_sha256':sha(reference/f'o.n{spp}.hits'),
               'pixels':[{'id':int(i),'x':int(i%state['width']),'y':int(i//state['width']),
                          'primary_primitive_matches':bool(hits['prim'][i]==state['meta'][oracle_hits['tri'][i],0])} for i in ids]}
        if process.returncode==0:
            value['diagnostic']=json.loads(process.stdout)
        result['rows'].append(value)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        if process.returncode:
            raise SystemExit('diagnostic failure retained')
    result.update(complete=True,payload_sha256={str(path.relative_to(args.work)):sha(path)
        for path in sorted(args.work.rglob('*')) if path.is_file()})
    args.output.write_text(json.dumps(result,indent=2)+'\n')
