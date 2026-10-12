#!/usr/bin/env python3
"""N007 read-only CPU replay of saved GPU probe-to-image aggregation.

First reproduce unchanged GPU indirect with actual work/contributions/primary
hits. Optional per-work byte flags allow a shadow-filtered counterfactual only
AFTER the unchanged baseline image reconstruction passes. This program does
not infer visibility flags from a count or declare physical/historical truth.
"""
from __future__ import annotations
import argparse
import json
import math
import struct
from collections import defaultdict
from pathlib import Path

from component_contract import analyze, checked_file
from inspect_hdr import read_pfm

WORK = struct.Struct('<3i5I8f')
HIT = struct.Struct('<4f4I')
CONTRIBUTION = struct.Struct('<2I')
MAGIC = b'N007-STATE1\x00'

def load_state(raw: bytes) -> dict:
    if len(raw) != 148 or raw[:12] != MAGIC:
        raise ValueError('N007 raw frame-state size/magic mismatch')
    width,height=struct.unpack_from('<II',raw,12)
    values=struct.unpack_from('<24f8I',raw,20)
    return dict(width=width,height=height,
        camera=values[0:4],right=values[4:8],up=values[8:12],
        forward=values[12:16],origin=values[16:20],
        counts=values[24:28],limits=values[28:32])

def read_arrays(work_raw: bytes, contrib_raw: bytes, hits_raw: bytes):
    if len(work_raw)%WORK.size or len(contrib_raw)%CONTRIBUTION.size or len(hits_raw)%HIT.size:
        raise ValueError('N007 raw GPU array misaligned')
    work=list(WORK.iter_unpack(work_raw))
    contributions=list(CONTRIBUTION.iter_unpack(contrib_raw))
    hits=list(HIT.iter_unpack(hits_raw))
    if len(work)!=len(contributions):
        raise ValueError('N007 work/contribution length mismatch')
    return work,contributions,hits

def unit_direction(state: dict, x: int, y: int):
    w,h=state['width'],state['height']
    nx=(2*(x+0.5)/w)-1
    ny=1-(2*(y+0.5)/h)
    fw,rt,up=state['forward'],state['right'],state['up']
    d=[fw[i]+rt[i]*(nx*rt[3])+up[i]*(ny*up[3]) for i in range(3)]
    length=math.sqrt(sum(t*t for t in d))
    if not math.isfinite(length) or length<=0:
        raise ValueError('invalid N007 camera direction')
    return tuple(v/length for v in d)

def aggregate_probes(work: list[tuple], contributions: list[tuple],
                     shadow_flags: bytes | None=None):
    """Mirror GPU merge, storage per-output rounded mean, and per-key mean."""
    if shadow_flags is not None and len(shadow_flags)!=len(work):
        raise ValueError('per-work shadow flags length mismatch')
    outputs=defaultdict(lambda: [0,0,0])
    owners=[]
    for i,(w,c) in enumerate(zip(work,contributions)):
        key=(w[0],w[1],w[2],w[3])
        ray_index, output_id = w[4],w[5]
        if c[0]!=output_id or c[1]>65535:
            raise ValueError('GPU work/output identity or quantization invalid')
        if shadow_flags is not None and shadow_flags[i] not in (0,1,2,3):
            raise ValueError('unexpected shadow label')
        o=outputs[output_id]
        o[0]+=c[1]
        o[1]+=1
        # 1 means CPU replay independently classified this positive GPU
        # contribution as shadow-blocked; no other category is suppressed.
        if shadow_flags is None or shadow_flags[i]!=1:
            o[2]+=c[1]
        if ray_index==0:
            owners.append((output_id,key))
    if len(owners)!=len(outputs):
        raise ValueError('GPU output grouping not one-to-one with ray-zero owners')
    summed=defaultdict(lambda:[0,0,0])
    for output_id,key in owners:
        original,count,filtered=outputs[output_id]
        if count<=0:
            raise ValueError('empty GPU output group')
        gpu_mean=(original+count//2)//count
        filtered_mean=(filtered+count//2)//count
        acc=summed[key]
        acc[0]+=gpu_mean
        acc[1]+=1
        acc[2]+=filtered_mean
    return dict(summed),len(outputs)

def replay_image(state: dict,hits: list[tuple],probes: dict,
                 counterfactual: bool=False):
    w,h=state['width'],state['height']
    if len(hits)!=w*h or state['counts'][1:3]!=(w,h):
        raise ValueError('GPU hit pixels/viewport mismatch')
    result=[]
    origin=state['origin']
    camera=state['camera']
    for pixel,hit in enumerate(hits):
        flag=hit[7]
        if flag==0:
            result.append(0.)
            continue
        if flag!=1:
            raise ValueError('invalid GPU first-hit flag')
        direction=unit_direction(state,pixel%w,pixel//w)
        pos=[camera[i]+direction[i]*hit[3] for i in range(3)]
        intensity=0.
        for cascade in range(state['counts'][3]):
            spacing=origin[3]*float(1<<cascade)
            if not math.isfinite(spacing) or spacing<=0:
                raise ValueError('invalid GPU probe spacing')
            key=tuple(math.floor((pos[i]-origin[i])/spacing) for i in range(3))+(cascade,)
            acc=probes.get(key)
            if acc:
                numerator=acc[2] if counterfactual else acc[0]
                intensity+=numerator/(acc[1]*65535.)
        result.append(intensity)
    return result

def compare_images(original: list[float],replayed: list[float]):
    if len(original)!=len(replayed):
        raise ValueError('GPU indirect replay pixel-count mismatch')
    errors=[a-b for a,b in zip(original,replayed)]
    return dict(max_abs_error=max((abs(x) for x in errors),default=0.),
        rgb_rms_error=math.sqrt(sum(x*x for x in errors)/len(errors)) if errors else 0.,
        positive_original_pixels=sum(x>0 for x in original),
        positive_replayed_pixels=sum(x>0 for x in replayed),
        positivity_disagreement_pixels=sum((x>0)!=(y>0) for x,y in zip(original,replayed)))

def replay_capture(root: Path, shadow_flags: Path | None=None) -> dict:
    manifest=root/'component-manifest.json'
    diagnostic=analyze(manifest)
    if not diagnostic['primary']['match']:
        raise ValueError('GPU/CPU primary mismatch blocks replay')
    m=json.loads(manifest.read_text())
    if m['frame']['backend']!='software' or (
            diagnostic['primary_geometry_attestation'] or {}).get('match') is not True:
        raise ValueError('software GPU primary geometry not attested')
    files=m['gpu_probe']
    work_raw=checked_file(root,files['work']).read_bytes()
    contribution_raw=checked_file(root,files['contributions']).read_bytes()
    hits_raw=checked_file(root,m['gpu']['hits']).read_bytes()
    state=load_state(checked_file(root,m['state_files']['frame']).read_bytes())
    work,contrib,hits=read_arrays(work_raw,contribution_raw,hits_raw)
    if len(work)!=m['probe_work_items']:
        raise ValueError('GPU work item count differs from provenance')
    image=read_pfm(checked_file(root,m['gpu']['indirect']))
    rgb=image['rgb'][::3]
    if (image['width'],image['height'])!=(state['width'],state['height']):
        raise ValueError('GPU PFM/primary dimensions diverge')
    flags=None
    if shadow_flags is not None:
        flags=shadow_flags.read_bytes()
    probes,groups=aggregate_probes(work,contrib,flags)
    original=replay_image(state,hits,probes)
    comparison=compare_images(rgb,original)
    # Tolerance is only a numerical implementation guard; positivity must
    # reproduce exactly to claim an image-level baseline.
    passed=(comparison['max_abs_error']<=1e-6 and
            comparison['positivity_disagreement_pixels']==0)
    result=dict(schema_version=1,classification='diagnostic-only',
        input_work_items=len(work),output_groups=groups,unique_probe_keys=len(probes),
        baseline=comparison,baseline_reconstruction_passed=passed,
        shadow_counterfactual_eligible=False,
        physical_correctness_proven=False,historical_causation_proven=False)
    if flags is not None:
        if not passed:
            raise ValueError('baseline probe-to-image replay failed; counterfactual prohibited')
        filtered=replay_image(state,hits,probes,counterfactual=True)
        result['shadow_counterfactual_eligible']=True
        result['counterfactual']={
            'positive_pixels':sum(x>0 for x in filtered),
            'positive_pixels_removed':sum(a>0 and v==0 for a,v in zip(original,filtered)),
            'positive_pixels_reduced':sum(a>v+1e-12 for a,v in zip(original,filtered)),
            'original_image_sum':sum(original),
            'filtered_image_sum':sum(filtered),
            'max_abs_delta':max((abs(a-v) for a,v in zip(original,filtered)),default=0.),
        }
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',required=True,type=Path)
    ap.add_argument('--shadow-flags',type=Path,help='Optional independent per-work byte visibility labels')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    result=replay_capture(args.capture,args.shadow_flags)
    dest=args.output or args.capture/'probe-image-replay.json'
    dest.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':
    main()
