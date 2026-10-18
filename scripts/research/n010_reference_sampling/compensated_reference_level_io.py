#!/usr/bin/env python3
"""Plan161: mechanical one-level library; CLI is source description only."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import textwrap
import time
from types import SimpleNamespace

import numpy as np
import compensated_reference_chain as P
from compensated_reference_chain import D, Q, require_no_other_research_worker

PLAN = D.RESULTS.parent/'experiments/161-compensated-single-level-io-component.md'
ORIGINAL = P.HELPERS/'qualify_point_guided_references.py'
ORIGINAL_SHA = 'cb9ce1e58a612cd66e6f2af1492e575b49e8ff3f003b6bef38d6e2112d77cc2e'
DESCRIPTION = D.RESULTS/'620-compensated-single-level-io-description.json'


def write(path,value,fresh=False):
    with path.open('x' if fresh else 'w') as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def analysis_program():
    original = D.checked(ORIGINAL,ORIGINAL_SHA).decode()
    begin = original.index('                fresh = json.loads(proc.stdout)\n')
    end = original.index('                # Audit actual complete level outputs',begin)
    block = textwrap.dedent(original[begin:end])
    before = "meta_path = directory/f'n{spp}.meta.json'\n"
    after = "fresh['resource_limits_sha256'] = sha(receipt)\n"+before
    source = D.once(block,before,after)
    if D.once(source,after,before) != block:raise ValueError('whole original032 analysis inverse differs')
    suffix = "manifests.append({'spp': spp"
    if source[source.index(suffix):] != block[block.index(suffix):]:
        raise ValueError('original manifest/assessor/SE/support/attempt bytes changed')
    ast.parse(source)
    return source,dict(original_sha256=ORIGINAL_SHA,
        original_analysis_sha256=hashlib.sha256(block.encode()).hexdigest(),
        generated_analysis_sha256=hashlib.sha256(source.encode()).hexdigest(),
        whole_original_analysis_inverse_exact=True,original_assessor_support_se_stop_suffix_bytes_exact=True,
        original_assessor_support_se_stop_suffix_ast_exact=(
            ast.dump(ast.parse(source[source.index(suffix):]),include_attributes=False) ==
            ast.dump(ast.parse(block[block.index(suffix):]),include_attributes=False)))


def identity():
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),P.PLAN,Path(P.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact161/158 source/recipe before use')
    return commit


def start_ticks(pid):
    try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
    except FileNotFoundError:return None


def acquire_level(selected,spp):
    """For a future registered scientific launcher, after its assessment gates.

    This component implements I/O, not the missing scientific launcher,
    density/bias assessment, feasibility decision or reference admission.
    Exactly one call per process; no acquisition option is exposed by main().
    """
    require_no_other_research_worker()
    if selected not in P.SELECTED or spp not in Q.LEVELS:raise ValueError('exact original8/six-level scope required')
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required')
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if os.getpriority(os.PRIO_PROCESS,0) != 15:raise ValueError('exact nice15 required')
    hard = resource.getrlimit(resource.RLIMIT_CPU)[1]
    if hard != resource.RLIM_INFINITY and hard < 172800:
        raise ValueError('fresh caller process must permit original native CPU ceiling')
    resource.setrlimit(resource.RLIMIT_CPU,(1200,172800))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    signal.alarm(1800)
    commit = identity()
    source,composition = analysis_program()
    inputs = D.INPUTS
    proofs = P.prerequisites(inputs)
    lock = json.loads(D.checked(D.RESULTS/'016-corpus-state-lock.json'))
    if set(lock['cells']) != {f'C{i}' for i in range(1,13)}:raise ValueError('complete original corpus lock required')
    cell,text = selected.rsplit('_T_B',1);vertices = int(text);spec = lock['cells'][cell]
    state = Q.L.read_state(D.ROOT/spec['state_directory'])
    if state['sha256'] != spec['state_sha256']:raise ValueError('canonical locked state differs')
    for path in (D.ROOT/spec['state_directory']).iterdir():
        if path.is_file():D.checked(path)
    scene = Q.scene_for_state(state,vertices)
    directory = P.REFERENCE_ROOT/selected;scene_path = directory/'scene.n008'
    previous,prior = None,{}
    qualification = directory/'qualification.json'
    if spp == Q.LEVELS[0]:
        if directory.exists():raise ValueError('first level refuses existing slot/partials')
        q = dict(cell=cell,transport=f'T_B{vertices}',state_sha256=state['sha256'],
            computational_variant=P.VARIANT,proof_sha256=proofs,levels=[],classification='INELIGIBLE')
        levels,manifests = q['levels'],[]
    else:
        P.verify_raw_chain(directory,cell,vertices,spec,inputs,require_eligible=False)
        old_bytes = qualification.read_bytes();q = json.loads(old_bytes);levels = q['levels']
        if (q['classification'] != 'INELIGIBLE' or len(levels) >= len(Q.LEVELS)
                or spp != Q.LEVELS[len(levels)]):raise ValueError('next consecutive nonqualified level only')
        previous = json.loads(D.checked(directory/f'n{levels[-1]["spp"]}.meta.json'))
        prior = levels[-1]['all_payload_sha256']
        manifests = [{'spp':level['spp'],'references':[dict(seed=seed,
            path=f'o.n{level["spp"]}.s{i}.total.pfm',sha256=level['all_payload_sha256'][f'o.n{level["spp"]}.s{i}.total.pfm'])
            for i,seed in enumerate(Q.L.N007_SEEDS)]} for level in levels]
        if scene_path.read_text() != scene.text():raise ValueError('same candidate canonical scene required')
    prefix = directory/f'o.n{spp}'
    names = [f'n{spp}.{suffix}' for suffix in ('attempt.json','resource-limits.json','stdout.json','stderr.log',
        'meta.json','raw-chain-audit.json')]+[f'screen-n{spp}.json',f'qualification-before-n{spp}.json']
    if any((directory/name).exists() for name in names) or list(directory.glob(f'o.n{spp}.*')):
        raise ValueError('existing level/partials; no overwrite/retry')
    if previous:
        snapshot = directory/f'qualification-before-n{spp}.json'
        with snapshot.open('xb') as stream:stream.write(old_bytes)
        if snapshot.read_bytes() != old_bytes:raise ValueError('prior qualification archive differs')
        # Preserve the exact prior input under its immutable archived identity.
        inputs.pop(str(qualification),None)
        D.checked(snapshot)
    else:
        directory.mkdir(parents=True)
        with scene_path.open('x') as stream:stream.write(scene.text())
        q['scene_sha256'] = D.sha(scene_path)
    D.checked(scene_path);D.checked(Q.NET);D.checked(P.BINARY)
    command = [str(P.BINARY),'--net',str(Q.NET),'--scene',str(scene_path),'--out',str(prefix),
        '--seeds',','.join(map(str,Q.L.N007_SEEDS)),'--spp',str(spp),'--threads','1']
    if previous:
        command += ['--resume-prefix',str(directory/f'o.n{previous["spp"]}'),'--resume-spp',str(previous['spp']),
            '--resume-counters',';'.join(','.join(str(run[k]) for k in P.COUNTERS)+',0' for run in previous['runs'])]
    receipt = directory/f'n{spp}.resource-limits.json'
    attempt_path = directory/f'n{spp}.attempt.json'
    raw_path,log_path = directory/f'n{spp}.stdout.json',directory/f'n{spp}.stderr.log'
    attempt = dict(command=command,source_commit=commit,pass_=False,native_terminal=False,
        input_sha256=dict(inputs),proof_sha256=proofs,source_composition=composition,
        sample_interval=[previous['spp'] if previous else 0,spp],previous_payload_sha256=prior)
    attempt['pass'] = attempt.pop('pass_')
    if previous:attempt['previous_qualification_snapshot'] = dict(path=str(snapshot),sha256=D.sha(snapshot))
    def save():write(attempt_path,attempt)
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(172800,172800))
        write(receipt,dict(pid=os.getpid(),pgid=os.getpgrp(),start_ticks=start_ticks(os.getpid()),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),command=command,
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_guard_seconds=43200),True)
    write(attempt_path,attempt,True)
    def terminal_payloads():return {str(path):D.sha(path) for path in directory.glob(f'o.n{spp}.*') if path.is_file()}
    try:
        for name,digest in list(inputs.items()):D.checked(Path(name),digest)
        require_no_other_research_worker()
        before = resource.getrusage(resource.RUSAGE_CHILDREN);started = time.monotonic()
        signal.alarm(0)
        with raw_path.open('xb') as stdout,log_path.open('xb') as stderr:
            child = subprocess.Popen(command,cwd=D.ROOT,stdout=stdout,stderr=stderr,
                start_new_session=True,preexec_fn=limits)
            attempt['native_pid'] = child.pid;save()
            try:code = child.wait(timeout=43200)
            except subprocess.TimeoutExpired:
                own = json.loads(receipt.read_text())
                if child.poll() is None:
                    if ((own['pid'],own['pgid'],own['start_ticks']) != (child.pid,child.pid,start_ticks(child.pid))
                            or own['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()):
                        raise ValueError('owned native changed; refuse signalling')
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                child.wait(timeout=5);code='ELAPSED_GUARD_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        attempt.update(native_terminal=True,returncode=code,wall_seconds_diagnostic=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            stdout_sha256=D.sha(raw_path),stderr_sha256=D.sha(log_path),terminal_payload_sha256=terminal_payloads(),
            resource_limits_sha256=D.sha(receipt))
        save();signal.alarm(1800)
        own = json.loads(receipt.read_text())
        if (code != 0 or own['pid'] != child.pid or own['pgid'] != child.pid
                or type(own['start_ticks']) is not int or own['start_ticks'] <= 0
                or own['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                or own['command'] != command or own['cpu'] != [172800]*2 or own['address_space'] != [4*1024**3]*2
                or own['affinity'] != [31] or own['nice'] != 15 or own['elapsed_guard_seconds'] != 43200
                or attempt['wall_seconds_diagnostic'] >= 43200 or attempt['child_cpu_seconds'] > 172800):
            raise ValueError('native/actual resource failure; retain all partials')
        namespace = dict(proc=SimpleNamespace(stdout=raw_path.read_text()),spp=spp,Q=Q,P=P,json=json,np=np,
            sha=D.sha,directory=directory,scene=scene,scene_path=scene_path,proofs=proofs,
            previous=previous,prior=prior,attempt=attempt,attempt_path=attempt_path,receipt=receipt,
            manifests=manifests,levels=levels,q=q,state=state,result=dict(source_commit=commit),
            check_files=lambda first,second:[D.checked(Path(p),h) for group in (first,second) for p,h in group.items()],
            inputs=inputs)
        exec(compile(source,'<n010-plan161-original032-analysis>','exec'),namespace)
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        attempt.update(failure=str(error),pass_=False,terminal_payload_sha256=terminal_payloads())
        attempt['pass'] = attempt.pop('pass_');save();signal.alarm(0)
        raise
    # Do not rewrite the attempt after the independent reader has observed it.
    audit_path = directory/f'n{spp}.raw-chain-audit.json'
    try:
        proof = P.verify_raw_chain(directory,cell,vertices,spec,inputs,require_eligible=False)
        write(audit_path,proof,True)
    except (ValueError,OSError,KeyError,AssertionError) as error:
        write(audit_path,dict(raw_chain_valid=False,reference_admission=False,failure=str(error)),True)
        signal.alarm(0);raise
    signal.alarm(0)
    return dict(raw_chain_valid=True,reference_admission=False,qualification=q,raw_chain_audit=str(audit_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe',action='store_true',required=True)
    parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(180)
    if DESCRIPTION.exists():raise ValueError('fresh source description required')
    commit = identity();_,proof = analysis_program()
    for module in (P.S,P.S.L,Q,Q.L,Q.convergence):D.checked(Path(module.__file__).resolve())
    result = dict(schema='n010-compensated-single-level-io-description/1',complete=True,
        classification='SINGLE_LEVEL_IO_SOURCE_ONLY_SCIENTIFIC_LAUNCHER_UNIMPLEMENTED',source_commit=commit,
        source_composition=proof,input_sha256=D.INPUTS,selected_transports=list(P.SELECTED),
        levels=list(Q.LEVELS),seeds=list(Q.L.N007_SEEDS),root=str(P.REFERENCE_ROOT),binary=str(P.BINARY),
        one_native_per_future_call=True,automatic_queue=False,scientific_launcher_implemented=False,
        native_executed=False,raw_evidence_replayed=False,prerequisites_executed=False,reference_admission=False,
        tests='NOT_RUN; source/AST/analysis inverse/original8-slot scope metadata only')
    for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
    write(DESCRIPTION,result,True);signal.alarm(0)
    print(result['classification'])


if __name__ == '__main__':main()
