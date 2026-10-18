#!/usr/bin/env python3
"""Plan140: one private exporter build or one original full control per invocation."""
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

ROOT, RESULTS, OUT = D.ROOT,D.RESULTS,D.OUT
PLAN=RESULTS.parent/'experiments/140-compensated-full-deterministic-controls.md'
WORK=OUT/'compensated-full-deterministic-v1'
BUILD=RESULTS/'452-compensated-full-exporter-build.json'
NAMES=('A2','A2b','A4a','A4b','A8_authored','A8_frozen','A8_stale_rest_pose','A4c','A4d')


def case_output(name):
    return RESULTS/f'{453+NAMES.index(name):03d}-compensated-full-{name.lower()}.json'


def native(command,part,result,save):
    receipt=part/'native.resources.json'

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
        receipt.write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
            start_ticks=D.start_ticks(os.getpid()),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            elapsed_limit_seconds=180,command=command))+'\n')

    D.quiet();D.unchanged()
    result['command']=command;save()
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
            try:os.killpg(child.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            child.wait(timeout=5);code='ELAPSED_GUARD_PARTIALS_RETAINED'
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    result.update(returncode=code,elapsed_seconds=time.monotonic()-start,
                  child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)
    save();actual=json.loads(D.checked(receipt))
    if not (actual['pid']==child.pid and actual['pgid']==child.pid and type(actual['start_ticks']) is int
            and actual['cpu']==[120,120] and actual['address_space']==[4*1024**3]*2
            and actual['affinity']==[31] and actual['nice']==15 and actual['command']==command
            and result['elapsed_seconds']<180 and result['child_cpu_seconds']<=120 and code==0):
        raise ValueError('native/resource failure; no following control')
    result['terminal_identity_verified']=True


def bind(path):
    data=json.loads(D.checked(path))
    if not data['complete']:raise ValueError('terminal prerequisite missing')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in data.get(group,{}).items():D.checked(name,digest)
    return data


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',choices=('build','case'),required=True)
    ap.add_argument('--case',choices=NAMES)
    args=ap.parse_args()
    if (args.stage=='case')!=(args.case is not None):
        raise ValueError('--case required only for case stage')
    os.sched_setaffinity(0,{31})
    priority=os.getpriority(os.PRIO_PROCESS,0)
    if priority<15:os.nice(15-priority)
    resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    D.quiet()
    output=BUILD if args.stage=='build' else case_output(args.case)
    part=WORK/('build' if args.stage=='build' else args.case)
    if output.exists() or part.exists() or (args.stage=='build' and WORK.exists()):
        raise ValueError('refuse existing control/work; no retry')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),Path(D.__file__).resolve(),PLAN):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])!=D.checked(path):
            raise ValueError('commit exact recipe/source before execution')
    probe=bind(RESULTS/'449-compensated-raw-target-probe.json')
    arithmetic=bind(RESULTS/'450-compensated-raw-target-arithmetic.json')
    if not (probe['candidate_one_pixel_pass'] and arithmetic['all12_target_residuals_independent_nearest_binary64']
            and arithmetic['all12_compensated_deltas_independent_nearest_binary64']
            and arithmetic['all12_physical_operands_equal_original']):
        raise ValueError('candidate449/450 qualification required')
    binary=WORK/'build/n010_compensated_exporter'
    result=dict(schema='n010-compensated-full-control/1',stage=args.stage,name=args.case,
        numerical_variant='compensated-raw-target-v1',complete=False,control_pass=False,
        build_valid=False,all_pass=False,gpu_run=False,reference_admission=False,accepted_timing=False,
        source_commit=commit,input_sha256=D.INPUTS,
        classification='COMPENSATED_FULL_CONTROL_PART_IN_PROGRESS',
        tests='NOT_RUN; original full scientific control acquisition only')

    def save():
        output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

    try:
        if args.stage=='build':
            prototype=json.loads(D.checked(next(RESULTS.glob('254-*.json'))))
            exporter=OUT/'wide8-cpu-bvh-v1/exporter.cpp'
            D.checked(exporter,prototype['payload_sha256'][str(exporter)])
            header=OUT/'compensated-raw-target-candidate-v1/prepare/n010_rqmc_oracle.hpp'
            prepared=bind(RESULTS/'447-compensated-raw-target-source.json')
            D.checked(header,prepared['payload_sha256'][str(header)])
            command=list(next(r['command'] for r in prototype['attempts']
                if r['command'][0]=='c++' and r['command'][-1].endswith('n010_wide8_exporter')))
            command[-3]=str(part/'exporter.cpp');command[-1]=str(binary)
            compiler=Path(shutil.which(command[0])).resolve();D.checked(compiler)
            D.unchanged();part.mkdir(parents=True)
            (part/'exporter.cpp').write_bytes(exporter.read_bytes())
            (part/'n010_rqmc_oracle.hpp').write_bytes(header.read_bytes())
            result.update(compiler_realpath=str(compiler),exporter_source_byte_identical_to254=True,
                          header_byte_identical_to447=True)
            save();native(command,part,result,save)
            if not binary.read_bytes().startswith(b'\x7fELF') or Path(shutil.which(command[0])).resolve()!=compiler:
                raise ValueError('compiled format/identity differs')
            result.update(build_valid=True,classification='PRIVATE_COMPENSATED_FULL_EXPORTER_BUILD_COMPLETE')
        else:
            build=bind(BUILD)
            if not build['build_valid']:raise ValueError('complete reviewed build452 required')
            index=NAMES.index(args.case)
            if index:
                previous=bind(case_output(NAMES[index-1]))
                if not previous['control_pass']:raise ValueError('previous original full control must pass')
            proof=bind(next(RESULTS.glob(('225' if index>=7 else '226')+'-*.json')))
            if not proof['all_pass']:raise ValueError('original full deterministic/sidedness evidence failed')
            row=next(r for r in proof['rows'] if r['name']==args.case)
            if not row['pass_'] or not row['full_frame'] or row['spp']!=64:
                raise ValueError('original full64 control identity differs')
            command=list(row['command']);old_prefix=Path(command[command.index('--out')+1])
            old_meta=old_prefix.parent/(args.case+'.meta.json')
            meta=json.loads(D.checked(old_meta,proof['payload_sha256'][str(old_meta)]))
            if (meta['width'],meta['height'],meta['spp'],meta['seeds'])!=(128,96,64,[305419896,2596069104,81985529216486895,18364758544493064720]):
                raise ValueError('original full shape/count/seeds differ')
            scene=Path(command[command.index('--scene')+1])
            D.checked(scene,meta['scene_sha256'])
            old_payloads=[Path(p) for p in proof['payload_sha256'] if Path(p).parent==old_prefix.parent
                          and Path(p).name.startswith(args.case+'.') and Path(p).suffix in ('.f64','.pfm','.hits')]
            if len(old_payloads)!=21:raise ValueError('original21 complete payloads required')
            command[0]=str(binary);command[command.index('--out')+1]=str(part/args.case)
            D.unchanged();part.mkdir()
            save();native(command,part,result,save)
            fresh=json.loads((part/'native.stdout').read_text())
            (part/(args.case+'.meta.json')).write_text(json.dumps(fresh,indent=2)+'\n')
            for key in ('scene_sha256','geometry_sha256','width','height','spp','seeds','ray_offset','point_lights','triangles','oracle','version'):
                if fresh[key]!=meta[key]:raise ValueError('original physical metadata differs: '+key)
            if len(fresh['runs'])!=4:raise ValueError('four complete original seeds missing')
            for new,old in zip(fresh['runs'],meta['runs']):
                for key in ('seed','primary_hits','shadow_tests','shadow_blocked','backface_absorbed','all_split'):
                    if new[key]!=old[key]:raise ValueError('original counter/audit differs: '+key)
            identities=[]
            for old in sorted(old_payloads):
                new=part/old.name
                same=new.read_bytes()==D.checked(old,proof['payload_sha256'][str(old)])
                identities.append(dict(payload=old.name,original_sha256=proof['payload_sha256'][str(old)],
                                       sha256=D.sha(new),byte_identical=same))
                if not same:raise ValueError('full deterministic/sidedness payload differs: '+old.name)
            result.update(control_pass=True,classification='COMPENSATED_ORIGINAL_FULL_CONTROL_ALL21_BYTES_AND_AUDITS_EXACT',
                full_frame=True,width=128,height=96,spp=64,seeds=fresh['seeds'],
                original_result=str(next(RESULTS.glob(('225' if index>=7 else '226')+'-*.json'))),
                payload_identities=identities,native_metadata=fresh,candidate_full_control_count=index+1,
                original_full_inventory_unchanged=True)
        D.unchanged()
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as error:
        result.update(failure=str(error),classification='COMPENSATED_FULL_CONTROL_FAILURE_PARTIALS_RETAINED')
    result.update(complete=True,payload_sha256={str(p):D.sha(p) for p in part.iterdir() if p.is_file()} if part.exists() else {})
    save();print(result['classification'])
    return 0 if result['build_valid'] or result['control_pass'] else 2


if __name__=='__main__':
    raise SystemExit(main())
