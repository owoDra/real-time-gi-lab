#!/usr/bin/env python3
"""022 CPU-only process, intake and stop contracts; synthetic device fixtures."""
import argparse
import copy
import json
from pathlib import Path
from unittest.mock import patch
import integrated_pt_process as T
import integrated_pt_audit as A
R,C,G=T.R,T.C,T.G


def run(out):
    T.committed();out=T.P.new_root(out);rows=[];inputs={str(p):C.sha(p) for p in T.OWN}
    result=dict(schema='m001-integrated022-process-cpu-contracts/1',complete=False,all_pass=False,gpu_executed=False,synthetic_device_fixtures_only=True,source_commit=G.head(),input_sha256=inputs,rows=rows)
    def check(name,value):
        rows.append(dict(name=name,pass_=bool(value)))
        if not value:raise ValueError('022 process CPU contract: '+name)
    def reject(name,f):
        try:f()
        except (ValueError,KeyError,TypeError,FileNotFoundError):check(name,True)
        else:check(name,False)
    def write(p,r):p.write_text(json.dumps(r))
    try:
        R.require(len(T.sequence())==1805,'022 registered unit count');check('exact-producer-fit-filter-composite-counts',[sum(x[0]==kind for x in T.sequence()) for kind in ('producer','geometry','fit','filter','composite')]==[450,1,1350,3,1])
        device=dict(timestamp_valid_bits=64,timestamp_period_ns=10.)
        events=[]
        for j,(kind,s,p,n) in enumerate(T.sequence()):
            events.extend([dict(event='begin',unit=j,kind=kind,stage=s,start=p,count=n),dict(event='complete',unit=j,timestamp_begin=j*200100+100,timestamp_end=j*200100+200,gpu_us_diagnostic=1.)])
        end=events[-1]['timestamp_end']+100;envelope=dict(timestamp_begin=0,timestamp_end=end,gpu_us_including_pauses=end*.01,active_unit_sum_us=1805.,accepted_timing=False)
        report=T.journal_report(events,device,envelope);check('complete-journal-envelope-and-active-separate',report['completed_units']==1805 and report['gpu_frame_envelope_including_pauses_us_diagnostic']>report['active_gpu_unit_sum_us_diagnostic'])
        wrapped=copy.deepcopy(events);offset=(1<<48)-1000
        for e in wrapped[1::2]:
            for key in ('timestamp_begin','timestamp_end'):e[key]=(e[key]+offset)&((1<<48)-1)
        envwrap={**envelope,'timestamp_begin':offset,'timestamp_end':(end+offset)&((1<<48)-1)};check('actual-timestamp-wrap-arithmetic',T.journal_report(wrapped,{**device,'timestamp_valid_bits':48},envwrap)['completed_units']==1805)
        for name,mut in (
            ('partial-journal',lambda e:e.pop()),('extra-journal',lambda e:e.extend(e[-2:])),('producer-range',lambda e:e[0].update(count=256)),('reordered-fit',lambda e:e[902].update(stage=1)),('false-completion',lambda e:e[1].update(event='incomplete')),('unit-timestamp-word',lambda e:e[1].update(timestamp_begin=-1)),('unit-duration',lambda e:e[1].update(gpu_us_diagnostic=2.)),('nonfinite-duration',lambda e:e[1].update(gpu_us_diagnostic=float('nan')))):
            x=copy.deepcopy(events);mut(x);reject(name,lambda x=x:T.journal_report(x,device,envelope))
        for name,update in (('invalid-timestamp-bits',{'timestamp_valid_bits':0}),('nonfinite-period',{'timestamp_period_ns':float('inf')})):reject(name,lambda u=update:T.journal_report(events,{**device,**u},envelope))
        for name,update in (('false-active-total',{'active_unit_sum_us':1}),('hidden-pauses',{'gpu_us_including_pauses':1805}),('accepted-timing-forbidden',{'accepted_timing':True})):reject(name,lambda u=update:T.journal_report(events,device,{**envelope,**u}))
        logical=[57600*8*4,80,57600*8*4,57600*75*4,57600*6*4,57600*4,57600*3*4,57600*3*4,57600*4*4,57600*4*4,128]
        specs=[(4096,0x100000,0),(8192,0x20000,0)]+[(size,32 if j<10 else 16,6) for j,size in enumerate(logical)];levents=[];live=0
        for j,(size,usage,props) in enumerate(specs):live+=size;levents.append(dict(sequence=j,device_context=1,allocation_id=j+1,bytes=size,live_bytes=live,memory_type=0,requested_properties=props,buffer_usage=usage,action='allocate',phase='synthetic-startup'))
        peak=live
        for old in list(reversed(levents.copy())):live-=old['bytes'];levents.append({**old,'sequence':len(levents),'action':'free','live_bytes':live})
        ledger=dict(schema='n010-allocation-lifetimes/1',device_contexts=1,teardown_zero=True,live_bytes_at_teardown=0,true_peak_owned_bytes=peak,events=levents,phases=[dict(name='synthetic',peak_bytes=peak,live_bytes_at_end=0)])
        complete=dict(aggregate_reserved_peak=peak,aggregate_reserved_at_teardown=0)
        check('full-as-scratch-pipeline-lifetimes',T.ledger_report(ledger,complete)['allocation_pairs']==13)
        for name,mut in (('missing-owned-free',lambda x:x['events'].pop()),('false-live-counter',lambda x:x['events'][0].update(live_bytes=0)),('wrong-free-size',lambda x:x['events'][-1].update(bytes=1)),('nonzero-teardown',lambda x:x.update(live_bytes_at_teardown=1)),('wrong-true-peak',lambda x:x.update(true_peak_owned_bytes=1)),('missing-as-accounting',lambda x:x['events'][0].update(buffer_usage=32)),('too-small-pipeline-buffer',lambda x:x['events'][2].update(bytes=1)),('extra-device-context',lambda x:x.update(device_contexts=2))):
            x=copy.deepcopy(ledger);mut(x);reject(name,lambda x=x:T.ledger_report(x,complete))
        reject('aggregate-cap-reconciliation',lambda:T.ledger_report(ledger,{**complete,'aggregate_reserved_peak':peak+1}))
        # Real filesystem/exclusive plan paths with a small synthetic input;
        # guarded() is forbidden throughout, so no test can launch native GPU.
        base=out/'synthetic-plan';base.mkdir();state=base/'state';state.mkdir();(state/'geometry-state.bin').write_bytes(b'synthetic-only');pins={str(state/'geometry-state.bin'):C.sha(state/'geometry-state.bin')}
        proof=dict(primary_capture=str(state),selected_spp=16,integrated_executable='/synthetic-never-executed/integrated-pt',integrated_shader_directory='/synthetic-shaders')
        with patch.object(T,'BASE',base),patch.object(T,'prepare_inputs',return_value=(pins.copy(),proof.copy())),patch.object(T,'quiet'),patch.object(T.G,'guarded',side_effect=AssertionError('CPU test attempted native GPU')):
            root=base/(T.tag('H01',2)+'-v1');path=T.new_plan('H01',2,root);original=json.loads(path.read_text());check('one-state-only-native-command',T.validate_plan(path)['command']==T.command(proof,root,2) and '--input' not in original['command'] and '--frames' not in original['command'])
            reject('prepare-refuses-existing-output',lambda:T.new_plan('H01',2,root));reject('later-target-needs-terminal-audit',lambda:T.previous_gate('H01',8,base))
            for name,mut in (('plan-source',lambda p:p.update(source_commit='0'*40)),('plan-authority',lambda p:p.update(gpu_processes_authorized=2)),('plan-timing',lambda p:p.update(accepted_timing=True)),('plan-command',lambda p:p['command'].append('--extra')),('plan-proof',lambda p:p['proof'].update(selected_spp=64)),('plan-input-hash',lambda p:p['input_sha256'].update(extra='0'*64))):
                x=copy.deepcopy(original);mut(x);write(path,x);reject(name,lambda:T.validate_plan(path));write(path,original)
            (root/'started.json').write_text('{}');reject('started-plan-never-relaunches',lambda:T.validate_plan(path));(root/'started.json').unlink()
            (root/'capture').mkdir();reject('partial-capture-never-relaunches',lambda:T.validate_plan(path));(root/'capture').rmdir()
            # A valid scientific loss and invalid numerical receipt both block
            # the next target. No permissive alternate rung or later-cell path.
            audit=base/(T.tag('H01',2)+'-terminal-audit-v1');audit.mkdir();a=dict(complete=True,valid=True,gpu_executed=True,source_commit=G.head(),cell='H01',depth=2,classification='INTEGRATED_TARGET_QUALITY_FAIL',decision=dict(selected_image_pass=False,reference_bias_pass=True,pass_=False),payload_sha256={});write(audit/'result.json',a)
            reject('scientific-loss-stops-next-target',lambda:T.previous_gate('H01',8,base));a.update(valid=False,classification='STOP_NO_RETRY');write(audit/'result.json',a);reject('invalid-numerics-stops-next-target',lambda:T.previous_gate('H01',8,base))
        # Exercise independent all-pixel fsum scoring with nontrivial finite
        # reference/error fields. These are synthetic CPU arrays, not evidence.
        import numpy as np
        reference={n:np.linspace(.1,.3,57600).reshape(180,320)*(j+1) for j,n in enumerate(('direct','indirect','total'))};values={n:v*1.01 for n,v in reference.items()};metrics,errors=A.score(values,reference)
        check('independent-fsum-all-pixels',all(abs(v['nrmse']-.01)<1e-14 and v['pixels']==57600 and v['scoring_exclusions']==0 for v in metrics.values()))
        T.F.rehash(inputs);result.update(complete=True,all_pass=True,total_new_process_contracts=len(rows),guarded_gpu_calls=0)
    except Exception as e:result.update(complete=True,error=repr(e))
    result['payload_sha256']={str(p.relative_to(out)):C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()};G.write(out/'result.json',result);print(json.dumps({k:result.get(k) for k in ('all_pass','error','total_new_process_contracts','gpu_executed')}));return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=run(a.out.resolve());raise SystemExit(0 if r['all_pass'] else 2)
