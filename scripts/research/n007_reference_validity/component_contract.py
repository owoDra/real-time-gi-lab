#!/usr/bin/env python3
"""N007 matched-state component gate, diagnostic only; no historical reclassification.

Reads private PFM/SSBO captures. Rejects missing bytes, forged path digests,
wrong dimensions, nonfinite/negative radiance, invalid IDs or divergent states.
Statistical convergence and independent physical validity are out of scope here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from inspect_hdr import read_pfm

INVALID = 0xFFFFFFFF
HIT_BYTES = 32
ABS_T = 2e-4
REL_T = 2e-5
SEEDS = [305419896, 2596069104, 81985529216486895, 18364758544493064720]

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def checked_file(base: Path, record: dict) -> Path:
    if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
        raise ValueError('artifact requires path and sha256')
    rel = Path(record['path'])
    if rel.is_absolute() or not rel.parts or '..' in rel.parts:
        raise ValueError('artifact path must be relative and non-traversing')
    full = (base/rel).resolve()
    if not full.is_relative_to(base.resolve()):
        raise ValueError('artifact escaped evidence directory')
    if not re.fullmatch('[0-9a-f]{64}', record['sha256']):
        raise ValueError('invalid SHA256')
    if sha(full.read_bytes()) != record['sha256']:
        raise ValueError(f'artifact SHA mismatch: {rel}')
    return full

def load_hits(path: Path, n: int) -> list[tuple]:
    raw = path.read_bytes()
    if len(raw) != n*HIT_BYTES:
        raise ValueError('HitData std430 byte length mismatch')
    hits = []
    for a,b,c,t,primitive,material,instance,flag in struct.iter_unpack('<4f4I',raw):
        if flag == 0:
            if not (math.isinf(t) and t>0 and (primitive,material,instance)==(INVALID,)*3):
                raise ValueError('invalid miss sentinel')
        elif flag == 1:
            if not (math.isfinite(t) and t>=1e-4 and all(math.isfinite(v) for v in (a,b,c))):
                raise ValueError('invalid hit normal/distance')
            if INVALID in (primitive,material,instance):
                raise ValueError('invalid hit identity')
            if abs(math.sqrt(a*a+b*b+c*c)-1) >= 1e-3:
                raise ValueError('nonunit geometric normal')
        else:
            raise ValueError('invalid primary-hit flag')
        hits.append((a,b,c,t,primitive,material,instance,flag))
    return hits

def primary_comparison(cpu: list[tuple], gpu: list[tuple]) -> dict:
    mask=ids=distance=normals=0
    for a,b in zip(cpu,gpu):
        if a[7]!=b[7]:
            mask+=1
            continue
        if not a[7]:
            continue
        if a[4:7]!=b[4:7]:ids+=1
        if abs(a[3]-b[3])>max(ABS_T,abs(a[3])*REL_T):distance+=1
        if sum(a[i]*b[i] for i in range(3))<0.9999:normals+=1
    return {'mask_mismatches':mask,'identity_mismatches':ids,
            'distance_mismatches':distance,'normal_mismatches':normals,
            'cpu_hit_pixels':sum(hit[7] for hit in cpu),
            'gpu_hit_pixels':sum(hit[7] for hit in gpu),
            'both_hit_pixels':sum(a[7] and b[7] for a,b in zip(cpu,gpu)),
            'match':not (mask or ids or distance or normals)}

def image_comparison(a: dict, b: dict) -> dict:
    delta=[x-y for x,y in zip(a['rgb'],b['rgb'])]
    return {'whole_frame_rgb_rms':math.sqrt(sum(v*v for v in delta)/len(delta)),
            'max_abs':max(map(abs,delta),default=0),
            'different_channels':sum(v!=0 for v in delta)}

def components(base: Path, record: dict, n: int, dims: tuple[int,int]) -> dict:
    expected={'hits','direct','indirect','total'}
    if set(record)!=expected:
        raise ValueError(f'capture requires {sorted(expected)}')
    hits=load_hits(checked_file(base,record['hits']),n)
    imgs={key:read_pfm(checked_file(base,record[key])) for key in ('direct','indirect','total')}
    for name,img in imgs.items():
        if (img['width'],img['height'])!=dims or img['nonfinite_channels'] or img['negative_channels']:
            raise ValueError(f'{name}: invalid dimensions/linear radiance')
        rgb=img['rgb']
        if any(rgb[i]!=rgb[i+1] or rgb[i]!=rgb[i+2] for i in range(0,len(rgb),3)):
            raise ValueError(f'{name}: expected achromatic original N-series image')
    excess=[]
    for d,i,t in zip(imgs['direct']['rgb'],imgs['indirect']['rgb'],imgs['total']['rgb']):
        # Same shader additions and float32 PFM serialization, four-ULP envelope.
        bound=max(2e-7,4*2**-23*max(abs(t),abs(d)+abs(i)))
        excess.append(abs(d+i-t)-bound)
    reconstruction={'max_excess_over_float32_bound':max(0,max(excess,default=0)),
                    'passed':all(x<=0 for x in excess)}
    return {'hits':hits,'images':imgs,'reconstruction':reconstruction}

def analyze(path: Path) -> dict:
    data=json.loads(path.read_text())
    if data.get('schema_version')!=1 or not isinstance(data.get('frame'),dict):
        raise ValueError('unsupported matched-state manifest')
    frame=data['frame']
    fields={'source_commit','scene_asset_sha256','frame_state_sha256',
            'geometry_state_sha256','frame_id','width','height','seeds','spp','backend'}
    if set(frame)!=fields:
        raise ValueError('incomplete or extraneous frame provenance')
    if not re.fullmatch('[a-f0-9]{40}',frame['source_commit']):
        raise ValueError('invalid source commit')
    for key in ('scene_asset_sha256','frame_state_sha256','geometry_state_sha256'):
        if not re.fullmatch('[a-f0-9]{64}',frame[key]):
            raise ValueError(f'invalid {key}')
    w,h=frame['width'],frame['height']
    if not (isinstance(w,int) and isinstance(h,int) and w>0 and h>0
            and w*h<=100_000_000):
        raise ValueError('invalid capture dimensions')
    if not (isinstance(frame['frame_id'],int) and frame['frame_id']>=0):
        raise ValueError('invalid frame ID')
    if frame['backend'] not in ('software','hwrt'):
        raise ValueError('unknown backend')
    if frame['seeds']!=SEEDS:
        raise ValueError('frozen N007 seed set mismatch')
    if frame['spp'] not in (512,1024,2048,4096,8192):
        raise ValueError('frozen N007 SPP mismatch')
    if set(data)!={'schema_version','frame','state_files','cpu','gpu','cpu_counts'}:
        raise ValueError('manifest structure mismatch')
    states=data['state_files']
    if set(states)!={'frame','geometry'}:
        raise ValueError('required raw state snapshots missing')
    base=path.resolve().parent
    for key,declared in (('frame','frame_state_sha256'),('geometry','geometry_state_sha256')):
        checked_file(base,states[key])
        if states[key]['sha256']!=frame[declared]:
            raise ValueError(f'{key} state SHA differs from recorded fingerprint')
    cpu=components(base,data['cpu'],w*h,(w,h))
    gpu=components(base,data['gpu'],w*h,(w,h))
    counts=data['cpu_counts']
    if set(counts)!={'primary_hits','secondary_hits','shadow_tested',
                     'shadow_blocked','shadow_clear','positive_samples'}:
        raise ValueError('missing visibility counters')
    if not all(isinstance(v,int) and v>=0 for v in counts.values()):
        raise ValueError('invalid CPU counters')
    if counts['shadow_tested']!=counts['shadow_blocked']+counts['shadow_clear']:
        raise ValueError('shadow counter invariant failed')
    if counts['primary_hits']<sum(hit[7] for hit in cpu['hits']):
        raise ValueError('primary hit count contradicts primary mask')
    primary=primary_comparison(cpu['hits'],gpu['hits'])
    comparison={k:image_comparison(cpu['images'][k],gpu['images'][k])
                for k in ('direct','indirect','total')}
    def signal_summary(img):
        # Achromatic PFM channels have already been validated.
        values=img['rgb'][::3]
        return {'positive_pixels':sum(v>0 for v in values),
                'max_value':max(values,default=0),
                'mean_value':sum(values)/len(values) if values else 0}
    signal={
        side:{k:signal_summary(data['images'][k])
              for k in ('direct','indirect','total')}
        for side,data in (('cpu',cpu),('gpu',gpu))
    }
    # A triage-only decomposition guard; not the statistical eligibility threshold.
    direct_match=comparison['direct']['max_abs']<=1e-5
    reconstruction=cpu['reconstruction']['passed'] and gpu['reconstruction']['passed']
    testable=primary['match'] and direct_match and reconstruction
    blockers=(['primary_hit_mismatch'] if not primary['match'] else []) + (
        ['direct_mismatch'] if not direct_match else []) + (
        ['component_reconstruction_mismatch'] if not reconstruction else []) + [
        'gpu_geometry_upload_and_source_state_not_independently_attested']
    return {
        'schema_version':1,'classification':'diagnostic-only','frame':frame,
        'primary':primary,'signal':signal,'component_comparison':comparison,
        'reconstruction':{'cpu':cpu['reconstruction'],'gpu':gpu['reconstruction']},
        'indirect_model_difference_testable':testable,
        'indirect_mismatch_detected':testable and comparison['indirect']['max_abs']>1e-5,
        'cross_device_state_independently_verified':False,
        'physical_correctness_proven':False,'historical_causation_proven':False,
        'convergence_evaluated':False,'blockers':blockers}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    result=analyze(args.manifest)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print(json.dumps({'primary_match':result['primary']['match'],
                      'gpu_reconstruction_passed':result['reconstruction']['gpu']['passed'],
                      'indirect_model_difference_testable':result['indirect_model_difference_testable'],
                      'physical_correctness_proven':False},indent=2))
if __name__=='__main__':main()
