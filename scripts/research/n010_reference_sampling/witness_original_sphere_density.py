#!/usr/bin/env python3
"""Plan137: prepare, build or acquire exact failed-sample operands separately."""
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
PLAN = RESULTS.parent/'experiments/137-original-sphere-density-operands.md'
WORK = OUT/'original-sphere-density-operands-v1'
OUTPUTS = {
    'prepare': RESULTS/'437-original-sphere-density-source.json',
    'build': RESULTS/'438-original-sphere-density-build.json',
    'probe': RESULTS/'439-original-sphere-density-witness.json',
}

GLOBALS = '''
// Plan137: diagnostic context only; all original arithmetic is retained.
inline bool n010_density_witness_enabled=false;
inline uint32_t n010_density_witness_k=0, n010_density_witness_split=0;
'''


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('nonunique diagnostic source anchor')
    return text.replace(old, new)


def log_statement(stage, light, index, target, distance2, cumulative):
    # The fields are existing operands. Only stderr observes their values.
    prefix = f'DENSITY_STEP {{"stage":"{stage}","k":%u,"split":%u,"light":%s,"index":%u'
    vectors = [('origin','current.origin'), ('source_normal','current.normal'),
               ('source_raw','current.raw.point'), ('target',target),
               ('direction','direction'), ('target_normal','normal')]
    fmt = prefix + ''.join(',"'+name+'":[%.17g,%.17g,%.17g]' for name, _ in vectors)
    fmt += ',"source_triangle":%u,"target_triangle":%u,"hit_t":%.17g,"d2":%.17g,"pdf":%.17g,"cosine":%.17g,"cumulative_log":%.17g}\n'
    args = ['n010_density_witness_k','n010_density_witness_split',light+'?"true":"false"',f'uint32_t({index})']
    args += [expr+'.'+axis for _,expr in vectors for axis in ('x','y','z')]
    args += ['current.raw.triangle', 'hit.tri' if stage == 'generate' else 'target.triangle',
             'hit.t', distance2, 'pdf','cosine',cumulative]
    return ('\n            if(n010_density_witness_enabled&&n010_density_witness_k==4)\n'
            '                std::fprintf(stderr,'+json.dumps(fmt)+',\n                    '+',\n                    '.join(args)+');\n')


def prepare():
    header = D.checked(D.HEADER).decode()
    source = D.checked(D.SOURCE).decode()
    start = header.index('    // Plan078:')
    end = header.index('    // Plan080:', start)
    original_body = header[start:end]
    context = '\n            n010_density_witness_k=k;n010_density_witness_split=split;'
    anchor = '            ++audit.strategy_counts[k][split];++audit.component_attempts;'
    generated_log = log_statement('generate','sphere||light_first','i','vertices.back().point',
                                  'hit.t*hit.t','sampled_log')
    point_anchor = '                    vertices.push_back({hit.tri,current.origin+direction*hit.t});'
    body = once(original_body, anchor, anchor+context)
    body = once(body, point_anchor, point_anchor+generated_log)
    if once(once(body, point_anchor+generated_log, point_anchor), anchor+context, anchor) != original_body:
        raise ValueError('whole_sample instrumentation inverse differs')
    changed = once(header, original_body, body)
    reconstructed_log = log_statement('reconstruct','light_first','i','target.point','d2','log_density')
    rec_anchor = '            log_density+=std::log(pdf)+std::log(cosine)-std::log(d2);\n            if(physical) {'
    changed = once(changed, rec_anchor, rec_anchor.replace('\n            if(physical)',reconstructed_log+'            if(physical)'))
    changed = once(changed, 'namespace phos::gi::research::n008 {',
                   'namespace phos::gi::research::n008 {'+GLOBALS)
    inverse = once(changed, 'namespace phos::gi::research::n008 {'+GLOBALS,
                   'namespace phos::gi::research::n008 {')
    inverse = once(inverse, rec_anchor.replace('\n            if(physical)',reconstructed_log+'            if(physical)'),rec_anchor)
    inverse = once(inverse, body, original_body)
    if inverse != header:
        raise ValueError('whole header inverse differs')
    enable_anchor = '        try {\n            oracle.sample_all_split'
    generated = once(source, enable_anchor,
                     '        n010_density_witness_enabled=(s==3265);\n'+enable_anchor)
    if once(generated, '        n010_density_witness_enabled=(s==3265);\n'+enable_anchor, enable_anchor) != source:
        raise ValueError('whole caller inverse differs')
    part = WORK/'prepare'
    part.mkdir(parents=True)
    (part/'n010_rqmc_oracle.hpp').write_text(changed)
    (part/'probe.cpp').write_text(generated)
    return dict(whole_header_inverse_exact=True, whole_caller_inverse_exact=True,
                thresholds_unchanged=True, original_transport_arithmetic_unchanged=True,
                classification='OPERAND_WITNESS_SOURCES_PREPARED_UNCOMPILED')


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
    for path in (Path(__file__).resolve(),Path(D.__file__).resolve(),D.SOURCE,D.PLAN,PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))]) != D.checked(path):
            raise ValueError('commit exact plan/source before use')
    prior = json.loads(D.checked(D.PROBE))
    if not (prior['complete'] and prior['failure_reproduced'] and prior['observation']['sample_index']==3265):
        raise ValueError('exact original435 reproduction required')
    for group in ('input_sha256','payload_sha256'):
        for path,digest in prior[group].items():
            D.checked(path,digest)
    result = dict(schema='n010-original-sphere-density-operands/1', stage=args.stage,
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
            binary=WORK/'build/n010_density_operands'
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
                result.update(build_valid=True,classification='PRIVATE_DENSITY_WITNESS_BUILD_COMPLETE')
            else:
                observation=json.loads((part/'native.stdout').read_text())
                text=(part/'native.stderr').read_text()
                observed=D.own_lines(text)
                expected=prior['original_witness_lines']
                reproduced=(code==77 and observation==prior['observation'] and observed==expected)
                if code not in (0,77):
                    raise ValueError('witness operational failure')
                steps=[json.loads(line[len('DENSITY_STEP '):]) for line in text.splitlines() if line.startswith('DENSITY_STEP ')]
                result.update(observation=observation,failure_reproduced=reproduced,
                              original_witness_lines=expected,observed_witness_lines=observed,
                              density_steps=steps,numerical_root_cause_established=False,
                              classification='ORIGINAL_DENSITY_FAILURE_OPERANDS_CAPTURED_NO_ADMISSION'
                              if reproduced else 'ORIGINAL_DENSITY_FAILURE_NOT_REPRODUCED_NO_ADMISSION')
            result['terminal_identity_verified']=True
        D.unchanged()
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='DENSITY_WITNESS_PART_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True,payload_sha256={str(p):D.sha(p) for p in part.iterdir() if p.is_file()} if part.exists() else {})
    save();print(result['classification'])
    return 0 if 'failure' not in result else 2


if __name__=='__main__':
    raise SystemExit(main())
