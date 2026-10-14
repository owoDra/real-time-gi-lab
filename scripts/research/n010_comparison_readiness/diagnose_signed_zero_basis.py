#!/usr/bin/env python3
"""CPU-only counterfactual on retained paths; post-hoc, never admission."""
import argparse
import json
from pathlib import Path
from diagnose_gpu_deep_sampling import BASE, LANE, ROOT, invoke, sha


def run(args):
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing basis diagnosis')
    args.work.mkdir(parents=True)
    path=LANE/'results/089-deep-path-diagnostic.json'
    trace=json.loads(path.read_text())
    if not trace.get('replay_valid'):
        raise ValueError('requires aggregate and counter replay')
    events=[r for r in trace['first_semantic_divergences'] if r['mode']=='polynomial']
    if len(events)!=8 or any(e['bounce']>=7 for e in events):
        raise ValueError('unexpected original eight paths')
    indices=trace['selected_pixels']
    rows=','.join('{'+','.join(str(x) for x in (indices.index(e['pixel']),e['pixel'],e['sample'],e['bounce']))+'}'for e in events)
    source=args.work/'basis.cpp'
    source.write_text(r'''
#include "n010_reference_snapshot.hpp"
#include <iostream>
#include <iomanip>
namespace N=phos::gi::research::n008;
struct Event {int slot,pixel,sample,bounce;};
static std::vector<double> load(const char* p){std::ifstream f(p,std::ios::binary|std::ios::ate);auto n=f.tellg();if(n!=8*8192*7*256)throw std::runtime_error("trace size");f.seekg(0);std::vector<double> a(size_t(n)/8);f.read(reinterpret_cast<char*>(a.data()),n);if(!f)throw std::runtime_error("trace read");return a;}
static N::V3 vec(const double* p){return {p[0],p[1],p[2]};}
static double error(N::V3 a,N::V3 b){return std::max({std::abs(a.x-b.x),std::abs(a.y-b.y),std::abs(a.z-b.z)});}
int main(int argc,char** argv){
 if(argc!=4)return 1;
 N::N010NetRng::load(argv[1]);auto cpu=load(argv[2]),gpu=load(argv[3]);
 Event events[]={EVENTS};std::cout<<std::setprecision(17)<<"[";bool first=true;
 for(auto e:events){
  size_t previous=((size_t(e.slot)*8192+e.sample)*7+e.bounce-1)*32,next=previous+32;
  N::V3 cn=vec(cpu.data()+previous+12),gn=vec(gpu.data()+previous+12),corrected=gn;
  if(cn.z!=0||gn.z!=0)throw std::runtime_error("not a signed-zero event");
  corrected.z=std::copysign(0.,cn.z);
  N::N010NetRng rng(305419896,e.pixel,e.sample);double u1=0,u2=0;
  for(int j=0;j<=e.bounce;++j){u1=rng.uniform();u2=rng.uniform();}
  auto predicted=N::Oracle::cosine_sample(gn,u1,u2),alternative=N::Oracle::cosine_sample(corrected,u1,u2);
  auto cd=vec(cpu.data()+next+4),gd=vec(gpu.data()+next+4);
  if(!first)std::cout<<",";first=false;
  std::cout<<"{\"pixel\":"<<e.pixel<<",\"sample\":"<<e.sample<<",\"hit_bounce\":"<<e.bounce
   <<",\"cpu_negative_zero\":"<<(std::signbit(cn.z)?"true":"false")<<",\"gpu_negative_zero\":"<<(std::signbit(gn.z)?"true":"false")
   <<",\"actual_direction_max_difference\":"<<error(cd,gd)
   <<",\"predicted_gpu_direction_max_error\":"<<error(predicted,gd)
   <<",\"zero_sign_only_counterfactual_cpu_direction_max_error\":"<<error(alternative,cd)<<"}";
 }
 std::cout<<"]\n";
}
'''.replace('EVENTS',rows))
    snapshot=BASE/'gpu-reference-snapshot-v1/n010_reference_snapshot.hpp'
    cp=BASE/'deep-path-diagnostic-v2/polynomial/cpu.trace'
    gp=BASE/'deep-path-diagnostic-v2/polynomial/gpu.trace'
    inputs=[path,cp,gp,snapshot,BASE/'sobol16x262144.bin',Path(__file__)]
    report=dict(schema='n010-signed-zero-basis-diagnostic/1',complete=False,gpu_run=False,
                eligible_for_references=False,classification='POSTHOC_DIAGNOSTIC_NOT_ADMISSION',
                input_sha256={str(p.relative_to(ROOT)):sha(p)for p in inputs},
                intervention='Replace only the sign bit of zero normal.z in the captured GPU normal with the captured CPU sign; keep GPU normal.x/y and identical uniform words. Calculate the next direction on CPU; no image repair or excluded samples.',steps=[])
    try:
        binary=args.work/'n010-basis-diagnostic'
        command=['g++','-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-pthread','-I'+str(snapshot.parent),str(source),'-o',str(binary)]
        report['steps'].append(invoke(command,args.work,'build'))
        row=invoke([str(binary),str(BASE/'sobol16x262144.bin'),str(cp),str(gp)],args.work,'runtime')
        report['steps'].append(row);report['rows']=json.loads(row['stdout'])
        report['generated_sha256']={'source':sha(source),'binary':sha(binary)}
        report['scope']='Eight post-hoc paths only. This diagnoses a deterministic basis-sign mechanism, not population bias, the other 46 pixels, CPU reference eligibility, or full GPU conformance.'
    except Exception as error:report['failure']=str(error)
    report['complete']=True;args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report.get(k)for k in ('complete','failure','rows')}))
    return 2 if report.get('failure')else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
