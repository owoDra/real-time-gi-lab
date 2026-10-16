#!/usr/bin/env python3
"""Plan 058: bounded C7-only diagnostic; original full 186 stays unexecuted."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess

from deferred_image_calibration_program import program, environment
from run_primary_direction_sequence import require_no_other_research_worker

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RESULTS=ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN=RESULTS.parent/'experiments/058-fixed-grid-and-short-boundary-diagnostics.md'


class BoundedSubprocess:
    def __init__(self):self.receipts=[]

    def __getattr__(self,name):return getattr(subprocess,name)

    def run(self,command,**kwargs):
        if len(command)>2 and command[:2]==['bash','scripts/run_with_vulkan.sh']:
            require_no_other_research_worker()
            out=Path(command[command.index('--out')+1]);receipt=out.parent/(out.name+'.resource-limits.json')
            record={'receipt_path':str(receipt),'command':command}
            self.receipts.append(record)
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(30,30))
                receipt.write_text(json.dumps({'pid':os.getpid(),
                    'start_ticks':int((Path('/proc')/str(os.getpid())/'stat').read_text().rsplit(')',1)[1].split()[19]),
                    'cpu':list(resource.getrlimit(resource.RLIMIT_CPU)),
                    'address_space':list(resource.getrlimit(resource.RLIMIT_AS)),
                    'elapsed_limit_seconds':30,'command':command})+'\n')
            kwargs.update(timeout=30,preexec_fn=limits)
            try:
                proc=subprocess.run(command,**kwargs)
                data=receipt.read_bytes();actual=json.loads(data)
                if actual['cpu']!=[30,30] or actual['command']!=command:raise ValueError('native resource receipt differs')
                record.update(receipt_sha256=hashlib.sha256(data).hexdigest(),actual=actual,returncode=proc.returncode)
                return proc
            except subprocess.TimeoutExpired as error:
                (out.parent/(out.name+'.timeout.stdout')).write_bytes(error.stdout or b'')
                (out.parent/(out.name+'.timeout.stderr')).write_bytes(error.stderr or b'')
                record['failure']='ELAPSED_GUARD_PARTIALS_RETAINED'
                raise
        return subprocess.run(command,**kwargs)


def main():
    require_no_other_research_worker()
    prior=RESULTS/'195-fixed-grid-scramble-diagnosis.json'
    d=json.loads(prior.read_bytes())
    if not (d.get('complete') or (d.get('failure') and d.get('classification')=='OPERATIONAL_FAILURE_PARTIALS_RETAINED')):
        raise ValueError('actual prior CPU diagnostic termination required')
    inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        Path(__file__).resolve(),PLAN,prior,RESULTS/'193-selected-bounce-path-diagnosis.json',
        RESULTS/'194-posthoc-depth-weight-and-rqmc-interpretation.json')}
    original,scope,proof=program(Path(__file__).resolve())
    source=original;edits=[]
    def replace(old,new):
        nonlocal source
        if source.count(old)!=1:raise ValueError('one-boundary diagnostic anchor differs')
        source=source.replace(old,new);edits.append((old,new))
    replace("_expected_result='185-deferred-image-calibration-sizing.json' if a.mode=='sizing' else '186-deferred-image-calibration-full-renderer.json'",
            "_expected_result='INVALID_SIZING_MODE' if a.mode=='sizing' else '196-deferred-c7-precision-diagnostic.json'")
    replace("_expected_work='deferred-image-calibration-sizing-v1' if a.mode=='sizing' else 'deferred-image-calibration-accepted-v1'",
            "_expected_work='INVALID_SIZING_MODE' if a.mode=='sizing' else 'deferred-c7-precision-diagnostic-v1'")
    replace('lock=_read(a.lock,_inputs);cohort=boundaries(lock)',
            "lock=_read(a.lock,_inputs);cohort=[b for b in boundaries(lock) if b['id']=='C7-hwrt']")
    replace("result={'schema':'n010-deferred-image-renderer-calibration/1'",
            "result={'accepted_timing':False,'diagnostic_only':True,'schema':'n010-deferred-c7-precision-diagnostic/1'")
    replace('WITNESSES={}', 'WITNESSES={}\nsubprocess=_bounded_subprocess')
    replace(" result['fixture_input_sha256']=_inputs",
            " _inputs.update("+repr(inputs)+")\n result['fixture_input_sha256']=_inputs\n result['diagnostic_dispatch_proof']=_diagnostic_proof\n result['diagnostic_native_resources']=_bounded_subprocess.receipts")
    restored=source
    for old,new in reversed(edits):
        if restored.count(new)!=1:raise ValueError('diagnostic inverse count differs')
        restored=restored.replace(new,old)
    if restored!=original:raise ValueError('whole diagnostic inverse differs')
    functions=lambda s:s[s.index('def execute('):s.index("if __name__=='__main__':")]
    if functions(source)!=functions(original):raise ValueError('scientific function bodies changed')
    diagnostic_proof={'whole_plan054_generated_inverse_exact':True,
        'execute_schedule_analysis_byte_identical':True,
        'parent_generated_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'diagnostic_generated_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'dispatch_edits':[{'old':a,'new':b} for a,b in edits],
        'scope':'C7 HWRT only; original eight-block numerical classifier, never full timing admission'}
    scope.update(_bounded_subprocess=BoundedSubprocess(),_diagnostic_proof=diagnostic_proof)
    exec(compile(source,str(Path(__file__))+'#plan058','exec'),scope)


if __name__=='__main__':main()
