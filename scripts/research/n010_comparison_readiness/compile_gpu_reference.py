#!/usr/bin/env python3
"""Bounded compiler trial; mark binary64 arithmetic NoContraction in SPIR-V."""
import argparse
import json
from pathlib import Path
import resource
import struct
import subprocess
from reference_provenance import ROOT,sha

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))

def decorate(raw):
    words=list(struct.unpack('<'+'I'*(len(raw)//4),raw))
    if words[0]!=0x07230203:raise ValueError('invalid SPIR-V')
    ops=[];i=5
    while i<len(words):
        count,opcode=words[i]>>16,words[i]&65535
        if not count or i+count>len(words):raise ValueError('invalid SPIR-V instruction')
        ops.append((opcode,words[i:i+count]));i+=count
    double_types={w[1] for op,w in ops if op==22 and w[2]==64}
    double_types|={w[1] for op,w in ops if op==23 and w[2] in double_types}
    # Scalar explicit expressions and vector scaling. No FMA intrinsic is
    # permitted; the source compiler emits separate arithmetic operations.
    arithmetic={127,129,131,133,136,142,143,144,145,146,147,148}
    targets={w[2] for op,w in ops if op in arithmetic and w[1] in double_types}
    for op,w in ops:
        if op==12 and len(w)>5 and w[1] in double_types and w[4]==50:
            raise ValueError('unexpected GLSL Fma intrinsic; do not accept contraction')
    additions=[]
    for target in sorted(targets):additions += [(3<<16)|71,target,42] # OpDecorate NoContraction
    result=words[:5];inserted=False
    for op,w in ops:
        if not inserted and 19<=op<=39:
            result+=additions;inserted=True
        result+=w
    if not inserted:raise ValueError('missing SPIR-V type declarations')
    return struct.pack('<'+'I'*len(result),*result),len(targets)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing compiler attempt')
    args.work.mkdir(parents=True)
    source=ROOT/'shaders/research/n010_comparison_readiness/n010_gpu_oracle.comp.glsl'
    compiler=ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'
    input_source=args.work/'input.comp.glsl'
    input_source.write_text(source.read_text().replace('precise ',''))
    output=args.work/'unannotated.spv'
    command=[str(compiler),'-V','--target-env','vulkan1.2','-S','comp',str(input_source),'-o',str(output)]
    result={'schema':'n010-gpu-reference-compiler/1','complete':False,'all_pass':False,
            'gpu_run':False,'source_sha256':sha(source),'compiler_sha256':sha(compiler),
            'script_sha256':sha(Path(__file__)),'command':command,
            'limits':{'address_space_bytes':2*1024**3,'cpu_seconds':60,'elapsed_seconds':75},
            'scope':'Compiler trial only. No reference eligibility; GLSL precise dataflow replaced by explicit NoContraction on every binary64 arithmetic result.'}
    try:
        process=subprocess.run(command,text=True,capture_output=True,timeout=75,preexec_fn=limits)
        result.update(returncode=process.returncode,stdout=process.stdout,stderr=process.stderr)
        if process.returncode==0:
            data,count=decorate(output.read_bytes())
            final=args.work/'n010_gpu_oracle.spv';final.write_bytes(data)
            result.update(no_contraction_arithmetic_results=count,shader_sha256=sha(final),
                          unannotated_shader_sha256=sha(output),all_pass=True)
    except subprocess.TimeoutExpired as error:
        result.update(returncode=None,failure='elapsed compiler budget exceeded',stdout=(error.stdout or b'').decode() if isinstance(error.stdout,bytes) else error.stdout,stderr=(error.stderr or b'').decode() if isinstance(error.stderr,bytes) else error.stderr)
    result['complete']=True
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS' if result['all_pass'] else 'FAIL')
    raise SystemExit(0 if result['all_pass'] else 2)
