#!/usr/bin/env python3
"""034 independent full-buffer CPU audit. Candidate membership, not RIS probability proof."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import restir_gi_device_build as D
import restir_gi_device_model as M
import restir_gi_device_process as P
import anchor_process_limits as C

B=D.B;F=M.F


def near(a,b,packed=False):return np.isclose(a,b,rtol=2e-5 if packed else 3e-4,atol=2e-6 if packed else 3e-6)


def guarded(path,size):
    data=path.read_bytes();M.need(len(data)==size+512,'complete guarded payload size')
    M.need(data[:256]==bytes([0x5a])*256 and data[-256:]==bytes([0x5a])*256,'saved buffer canaries')
    return data[256:-256]


def unpack_snapshot(folder,stage,w,h):
    n=w*h;pitch,_,indices=M.layout(w,h)
    reservoir=guarded(folder/(stage+'-reservoirs.bin'),pitch*64)
    outputs=guarded(folder/(stage+'-results.bin'),(n*2+64)*16)
    M.need(outputs[n*32:]==bytes(64*16),'full unwritten output padding')
    packed=np.frombuffer(reservoir,M.PACKED).reshape(2,pitch)
    results=np.frombuffer(outputs,'<f4',count=n*8).reshape(n,2,4)
    mask=np.ones(pitch,bool);mask[indices]=False
    M.need(packed[:,mask].tobytes()==bytes(2*int(mask.sum())*32),'all padded reservoir addresses untouched')
    M.need(np.isfinite(results).all(),'finite result fields')
    return reservoir,outputs,packed,results,indices


def pixel_audit(data,results,raw,pool,case,variant):
    total,candidates=M.expected_candidates(pool,case,variant);count=len(data)
    M.need(np.isfinite(data['weight']).all() and (data['weight']>=0).all(),'finite nonnegative packed weights')
    M.need(np.isfinite(data['position']).all() and (data['unused']==0).all(),'finite position/unused')
    state=(data['misc']&255)==total;state&=(data['misc']>>16)==0
    state&=(results[:,0,3]==total)
    state&=(data['position']==raw[:,0,:3]).all(axis=1)
    state&=data['normal']==(0 if case==4 else 0x7fff7fff)
    age=(data['misc']>>8)&255;decoded=M.decode(data['radiance'])
    M.need(np.isfinite(decoded).all() and (decoded>=0).all(),'packed color finite nonnegative')
    legal=[];errors=[];expected_weights=[];expected_colors=[];eligible=[]
    for candidate in candidates:
        rgb=candidate['rgb'];weight=candidate['weight'];shaded=candidate['shaded']
        # GPU diagnostic is packedDecode(selectedRGB) - selectedRGB.
        decoded_expected=rgb+results[:,1,:3]
        ok=candidate['valid'] & (age==candidate['age'])
        ok&=near(data['weight'],weight)&near(results[:,1,3],weight)
        ok&=near(results[:,0,:3],shaded).all(axis=1)
        ok&=near(decoded,decoded_expected,packed=True).all(axis=1)
        bound=F(.02)*np.maximum(np.maximum(np.abs(rgb),np.abs(decoded)),F(1e-6))
        ok&=(np.abs(results[:,1,:3])<=bound).all(axis=1)
        legal.append(ok);eligible.append(candidate['valid'])
        errors.append(np.abs(results[:,0,:3]-shaded));expected_weights.append(weight);expected_colors.append(rgb)
    legal=np.stack(legal);membership=legal.any(axis=0)
    if case in (2,3,4):state&=(results[:,0,:3]==0).all(axis=1)
    state&=(results[:,0,:3]>=0).all(axis=1)
    arrays=dict(state_pass=state,membership_pass=membership,legal_candidates=legal,eligible_candidates=np.stack(eligible),
                observed_m=data['misc']&255,expected_m=total,observed_age=age,observed_weight=data['weight'],
                expected_weights=np.stack(expected_weights),candidate_ages=np.stack([c['age'] for c in candidates]),observed_rgb=results[:,0,:3],candidate_rgb=np.stack(expected_colors),
                absolute_shaded_errors=np.stack(errors),packed_decode=decoded,packing_error=results[:,1,:3])
    return bool(state.all() and membership.all()),arrays


def ledger_audit(ledger):
    live={};peak=0
    for i,row in enumerate(ledger['events']):
        M.need(row['sequence']==i and row['device_context']==1,'allocation event order/device')
        key=row['allocation_id']
        if row['action']=='allocate':
            M.need(key not in live and row['bytes']>0,'allocation identity');live[key]=row['bytes']
        else:
            M.need(row['action']=='free' and live.pop(key,None)==row['bytes'],'free exact owned allocation')
        current=sum(live.values());peak=max(peak,current);M.need(row['live_bytes']==current and current<=256*1024**2,'full allocation running total/cap')
    M.need(len(ledger['events'])==20 and not live and ledger['teardown_zero'] and ledger['live_bytes_at_teardown']==0 and ledger['true_peak_owned_bytes']==peak,'ten complete owned lifetimes/true peak')
    return peak


def audit(path):
    path=path.resolve();receipt=B.read(path);size=receipt['size'];root=P.root_for(size);out=Path(str(root)+'-audit')
    M.need(path==root/'result.json' and not out.exists(),'canonical exclusive audit')
    out.mkdir();pins={str(path):B.SHA(path)}
    r=dict(schema='m001-restir034-full-analytic-audit/1',source_commit=D.committed(),complete=False,all_pass=False,
           classification='INVALID_ANALYTIC_GPU_CONTROL',size=size,input_sha256=pins,configurations=[],gpu_executed=False,
           quality_admitted=False,accepted_timing=False,ris_choice_probability_proof=False)
    C.write(out/'receipt-before.json',dict(native_receipt=str(path),native_receipt_sha256=B.SHA(path)))
    try:
        r['effective_parent_limits']=C.limits()
        M.need(receipt['complete'] and receipt['all_pass'] and receipt['source_commit']==r['source_commit'] and receipt['gpu_process_attempts']==1,'one successful same-source acquisition')
        B.rehash(receipt['input_sha256']);pins.update(receipt['input_sha256'])
        for k,v in receipt['payload_sha256'].items():
            p=root/k;M.need(B.SHA(p)==v,'all GPU payload identity');pins[str(p)]=v
        plan=B.read(root/'plan.json');w,h=map(int,size.split('x'));inputs=Path(plan['proof']['inputs']);native=root/'native'
        peak=ledger_audit(B.read(native/'allocation-ledger.json'));r['true_peak_owned_bytes']=peak
        units=[json.loads(line) for line in (native/'units.jsonl').read_text().splitlines()]
        M.need(len(units)==576,'all unit begin/completion rows')
        ticks=[]
        for i in range(288):
            begin,end=units[2*i:2*i+2];M.need(begin['event']=='begin' and end['event']=='complete' and begin['unit']==end['unit']==i and 0<=end['gpu_us_diagnostic']<=250000,'bounded submitted unit')
            ticks.append(end['gpu_us_diagnostic'])
        with (out/'all-unit-diagnostic-us.npy').open('xb') as f:np.save(f,np.asarray(ticks))
        device=B.read(native/'device.json');M.need(device['name']=='AMD Radeon 8060S Graphics (RADV STRIX_HALO)' and device['robust_buffer_access'] and not device['accepted_timing'],'target identity')
        for case in range(8):
            folder=inputs/f'fixture-{case}';raw=np.fromfile(folder/'binding-3.bin','<f4').reshape(w*h,3,4);offsets=(folder/'binding-4.bin').read_bytes()
            for variant in range(6):
                stem=f'f{case}-p{variant}';capture=native/stem;q=B.read(capture/'complete.json')
                M.need(q['complete'] and q['fixture']==case and q['variant']==variant and q['canaries_and_readonly_pass'] and q['cold_reset_exact'],'native full buffer/readonly/reset checks')
                snapshots={stage:unpack_snapshot(capture,stage,w,h) for stage in ('seed','cold','warm','reset')}
                seed=snapshots['seed'];cold=snapshots['cold'];warm=snapshots['warm'];reset=snapshots['reset'];pitch=M.layout(w,h)[0];indices=seed[4]
                M.need(seed[0][pitch*32:]==bytes(pitch*32),'seed untouched destination array')
                M.need(cold[0][:pitch*32]==seed[0][:pitch*32] and warm[0][:pitch*32]==cold[0][pitch*32:],'full padded source preserved/copied')
                M.need(cold[:2]==reset[:2],'full cold/reset byte identity')
                stage_rows=[]
                for stage,source_index,frame,pass_index in [('seed',0,0,0),('cold',0,0,variant),('warm',0,1,variant),('reset',0,0,variant)]:
                    snap=snapshots[stage];output_index=0 if stage=='seed' else 1;source=snap[2][source_index,indices]
                    pool=M.candidates(source,raw,w,h,case,pass_index,frame,offsets)
                    passed,arrays=pixel_audit(snap[2][output_index,indices],snap[3],raw,pool,case,pass_index)
                    with (out/(stem+'-'+stage+'-all-pixels.npz')).open('xb') as f:np.savez_compressed(f,**arrays)
                    row=dict(stage=stage,pixels=w*h,all_pass=passed,state_failures=int((~arrays['state_pass']).sum()),membership_failures=int((~arrays['membership_pass']).sum()))
                    stage_rows.append(row);r['configurations'].append(dict(fixture=case,variant=variant,**row))
                    M.need(passed,'full pixel/state/candidate/normalization audit failed '+stem+' '+stage)
        M.need(len(r['configurations'])==192,'all 48 configurations/four snapshots')
        B.rehash(pins);r.update(complete=True,all_pass=True,classification='ANALYTIC_GPU_DIMENSION_PASS',pixels_audited=w*h*192,
                              saved_snapshot_pairs=192,owned_allocations=10,unit_dispatches=240,unit_copies=48,validation_layers='NOT_RUN')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r['payload_sha256']=B.inventory(out);C.write(out/'result.json',r)
    print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','pixels_audited','error')}),flush=True)
    return 0 if r['all_pass'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',type=Path,required=True);args=parser.parse_args();sys.exit(audit(args.receipt))
