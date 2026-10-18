#!/usr/bin/env python3
"""Plan139: bounded compensated raw-target candidate, never reference admission."""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import time

import diagnose_original_sphere_pixel as D

ROOT, RESULTS, OUT = D.ROOT, D.RESULTS, D.OUT
PLAN = RESULTS.parent/'experiments/139-compensated-raw-target-candidate.md'
WORK = OUT/'compensated-raw-target-candidate-v1'
SNIPPET = ROOT/'src/research/n010_comparison_readiness/compensated_raw_target.inc.hpp'
OUTPUTS = {
    'prepare': RESULTS/'447-compensated-raw-target-source.json',
    'build': RESULTS/'448-compensated-raw-target-build.json',
    'probe': RESULTS/'449-compensated-raw-target-probe.json',
}


def prepare():
    parent = json.loads(D.checked(RESULTS/'442-original-sphere-density-source.json'))
    if not (parent['complete'] and parent['whole_header_inverse_exact'] and parent['whole_caller_inverse_exact']):
        raise ValueError('exact original diagnostic source442 required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in parent[group].items():D.checked(path,digest)
    directory = OUT/'original-sphere-density-operands-v2/prepare'
    header = D.checked(directory/'n010_rqmc_oracle.hpp').decode()
    source = D.checked(directory/'probe.cpp').decode()
    edits=[]
    changed=header

    def edit(old,new,count=1):
        nonlocal changed
        if changed.count(old)!=count:raise ValueError('nonunique candidate source anchor')
        changed=changed.replace(old,new);edits.append(dict(old=old,new=new,count=count))

    original_struct='    struct WholeRaw {uint32_t triangle{UINT32_MAX};V3 point{};};'
    candidate_struct='    struct WholeRaw {uint32_t triangle{UINT32_MAX};V3 point{},low{};};'
    edit(original_struct,candidate_struct+'\n'+D.checked(SNIPPET).decode())
    edit('const auto delta=target.point-current.origin;',
         'const auto delta=whole_precise_delta(target,current.origin);',2)
    edit('vertices.push_back({hit.tri,current.origin+direction*hit.t});',
         'vertices.push_back(whole_precise_hit(hit.tri,current.origin,direction,hit.t));',2)
    edit('                    sampled_log);',
         '                    sampled_log);\n                    whole_log_precision("generate",light_first,i,vertices.back(),whole_precise_delta(vertices.back(),current.origin));')
    edit('                    log_density);',
         '                    log_density);\n            whole_log_precision("reconstruct",light_first,uint32_t(i),target,delta);')
    restored=changed
    for row in reversed(edits):
        if restored.count(row['new'])!=row['count']:raise ValueError('candidate inverse anchor differs')
        restored=restored.replace(row['new'],row['old'])
    if restored!=header:raise ValueError('whole candidate header inverse differs')
    anchor=r'    std::cout << "{\"exception_caught\":false,\"completed_samples\":8192,"'
    pos=source.index(anchor)
    ending=source[pos:]
    tail=r'''
    const auto& audit=oracle.renderer_audit_;
    std::cout << std::setprecision(17)
              << "{\"exception_caught\":false,\"completed_samples\":8192,"
                 "\"pixel\":[96,77],\"seed\":" << seed
              << ",\"max_own_log_error\":" << audit.max_own_log_error
              << ",\"own_checks\":" << audit.own_checks
              << ",\"component_attempts\":" << audit.component_attempts
              << ",\"bvh_queries\":" << audit.bvh_queries
              << ",\"max_target_error_fraction\":" << audit.max_target_error_fraction
              << ",\"max_weight\":" << audit.max_weight << "}\n";
    return 0;
}
'''
    generated=source[:pos]+tail.lstrip('\n')
    if generated[:pos]+ending!=source:raise ValueError('whole candidate caller inverse differs')
    part=WORK/'prepare';part.mkdir(parents=True)
    (part/'n010_rqmc_oracle.hpp').write_text(changed)
    (part/'probe.cpp').write_text(generated)
    (part/'source-edits.json').write_text(json.dumps(dict(header=edits,caller_old=ending,caller_new=tail.lstrip('\n')),indent=2)+'\n')
    return dict(whole_header_inverse_exact=True,whole_caller_inverse_exact=True,
                thresholds_unchanged=True,physical_spawn_uses_original_high_point=True,
                density_arithmetic_changed=True,chosen_family_density_override=False,
                classification='COMPENSATED_RAW_TARGET_CANDIDATE_PREPARED_UNCOMPILED')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',choices=tuple(OUTPUTS),required=True)
    args = ap.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    if args.stage == 'prepare':
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    output, part = OUTPUTS[args.stage], WORK/args.stage
    if output.exists() or part.exists() or (args.stage == 'prepare' and WORK.exists()):
        raise ValueError('refuse existing work/result; no retry')
    D.quiet()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),Path(D.__file__).resolve(),D.SOURCE,D.PLAN,PLAN,SNIPPET):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))]) != D.checked(path):
            raise ValueError('commit exact plan/source before use')
    failed = json.loads(D.checked(RESULTS/'437-original-sphere-density-source.json'))
    if failed.get('failure') != 'nonunique diagnostic source anchor' or failed.get('payload_sha256') != {}:
        raise ValueError('exact precompiler437 selector failure required')
    for name, digest in failed['input_sha256'].items():
        D.checked(name,digest)
    prior = json.loads(D.checked(RESULTS/'444-original-sphere-density-witness.json'))
    if not (prior['complete'] and prior['failure_reproduced'] and prior['observation']['sample_index']==3265):
        raise ValueError('exact original435 reproduction required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in prior[group].items():
            D.checked(path,digest)
    result = dict(schema='n010-compensated-raw-target-candidate/1', stage=args.stage,
        complete=False, all_pass=False, reference_admission=False, accepted_timing=False,
        gpu_run=False, posthoc=True, build_valid=False, failure_reproduced=False,
        source_commit=commit, input_sha256=D.INPUTS,
        classification='POSTHOC_DENSITY_WITNESS_PART_IN_PROGRESS',
        tests='NOT_RUN; bounded scientific numerical diagnosis only')

    def save():
        output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

    try:
        if args.stage == 'prepare':
            start=time.monotonic();before=time.process_time()
            result.update(prepare(), elapsed_seconds=time.monotonic()-start,
                          cpu_seconds=time.process_time()-before)
            if result['elapsed_seconds'] >= 180 or result['cpu_seconds'] > 120:
                raise ValueError('source preparation resource boundary exceeded')
            result['execution'] = dict(affinity=sorted(os.sched_getaffinity(0)),
                nice=os.getpriority(os.PRIO_PROCESS,0),cpu_limit_seconds=120,
                elapsed_limit_seconds=180,address_space_limit_bytes=4*1024**3)
        else:
            previous = OUTPUTS['prepare' if args.stage == 'build' else 'build']
            artifact=json.loads(D.checked(previous))
            if not artifact['complete'] or (args.stage=='build' and not artifact.get('whole_header_inverse_exact')) or (
                    args.stage=='probe' and not artifact.get('build_valid')):
                raise ValueError('complete reviewed prior part required')
            for group in ('input_sha256','payload_sha256'):
                for path,digest in artifact[group].items():
                    D.checked(path,digest)
            binary=WORK/'build/n010_compensated_target_probe'
            compiler=None
            if args.stage=='build':
                build=json.loads(D.checked(D.BUILD))
                command=list(build['command'])
                command[command.index('-I')+1]=str(WORK/'prepare')
                command[-3]=str(WORK/'prepare/probe.cpp');command[-1]=str(binary)
                compiler=Path(shutil.which(command[0])).resolve();D.checked(compiler)
            else:
                command=[str(binary),str(D.NET),str(D.SCENE)]
            D.unchanged();D.quiet();part.mkdir()
            receipt=part/'native.resources.json'

            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(120,120))
                resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
                receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
                    start_ticks=D.start_ticks(os.getpid()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
                    elapsed_limit_seconds=180,command=command))+'\n')

            result.update(command=command,compiler_realpath=str(compiler) if compiler else None);save()
            before=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic()
            with (part/'native.stdout').open('wb') as out,(part/'native.stderr').open('wb') as err:
                child=subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
                result['native_pid']=child.pid;save()
                try:
                    code=child.wait(timeout=180)
                except subprocess.TimeoutExpired:
                    actual=json.loads(receipt.read_text())
                    if (actual['pid'],actual['pgid'],actual['start_ticks'])!=(child.pid,child.pid,D.start_ticks(child.pid)):
                        raise ValueError('owned process identity differs; refuse signalling')
                    try:
                        os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=5);code='ELAPSED_GUARD_PARTIALS_RETAINED'
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            result.update(returncode=code,elapsed_seconds=time.monotonic()-start,
                          child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
            save();actual=json.loads(D.checked(receipt))
            if not (actual['pid']==child.pid and actual['pgid']==child.pid and type(actual['start_ticks']) is int
                    and actual['cpu']==[120,120] and actual['address_space']==[4*1024**3]*2
                    and actual['affinity']==[31] and actual['nice']==15 and actual['command']==command
                    and result['elapsed_seconds']<180 and result['child_cpu_seconds']<=120):
                raise ValueError('resource boundary differs')
            if args.stage=='build':
                if code!=0 or not binary.read_bytes().startswith(b'\x7fELF'):
                    raise ValueError('operand witness build failed; no native follows')
                if Path(shutil.which(command[0])).resolve()!=compiler:
                    raise ValueError('compiler identity changed')
                result.update(build_valid=True,classification='PRIVATE_COMPENSATED_RAW_TARGET_BUILD_COMPLETE')
            else:
                observation=json.loads((part/'native.stdout').read_text())
                text=(part/'native.stderr').read_text()
                if code not in (0,77):
                    raise ValueError('candidate operational failure')
                steps=[json.loads(line[len('DENSITY_STEP '):]) for line in text.splitlines() if line.startswith('DENSITY_STEP ')]
                precision=[json.loads(line[len('RAW_PRECISION '):]) for line in text.splitlines() if line.startswith('RAW_PRECISION ')]
                original_generated=[row for row in prior['density_steps'] if row['stage']=='generate']
                generated=[row for row in steps if row['stage']=='generate']
                generation_exact=generated==original_generated
                candidate_pass=(code==0 and observation.get('exception_caught') is False
                    and observation.get('completed_samples')==8192 and observation.get('pixel')==[96,77]
                    and observation.get('seed')==81985529216486895
                    and type(observation.get('max_own_log_error')) in (float,int)
                    and 0<=observation['max_own_log_error']<=1e-6
                    and observation.get('own_checks',0)>0 and generation_exact
                    and len(steps)==12 and len(precision)==12)
                result.update(observation=observation,candidate_one_pixel_pass=candidate_pass,
                    original_generation_rows_bit_exact=generation_exact,
                    density_steps=steps,raw_precision_steps=precision,
                    classification='COMPENSATED_TARGET_ONE_PIXEL8192_PASS_NO_REFERENCE_ADMISSION'
                    if candidate_pass else 'COMPENSATED_TARGET_ONE_PIXEL_NOT_PASS_NO_REFERENCE_ADMISSION')
            result['terminal_identity_verified']=True
        D.unchanged()
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='DENSITY_WITNESS_PART_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True,payload_sha256={str(p):D.sha(p) for p in part.iterdir() if p.is_file()} if part.exists() else {})
    save();print(result['classification'])
    return 0 if 'failure' not in result else 2


if __name__=='__main__':
    raise SystemExit(main())
