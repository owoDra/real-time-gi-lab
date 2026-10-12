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

def software_primary_geometry(cpu_path: Path, gpu_path: Path) -> dict:
    """Compare device-readback std430 triangles with the CPU world-space snapshot."""
    raw=cpu_path.read_bytes()
    gpu=gpu_path.read_bytes()
    if len(raw)<8:
        raise ValueError('truncated CPU geometry state')
    version,count=struct.unpack_from('<II',raw,0)
    if version!=1 or count>100_000_000 or len(raw)!=8+count*52:
        raise ValueError('malformed CPU geometry state')
    if len(gpu)!=count*64:
        raise ValueError('GPU primary triangle readback byte length mismatch')
    mismatched=0
    first=None
    for k in range(count):
        tri=raw[8+k*52:8+(k+1)*52]
        packed=(tri[0:12]+bytes(4)+tri[12:24]+bytes(4)+
                tri[24:36]+bytes(4)+tri[36:52])
        if gpu[k*64:(k+1)*64]!=packed:
            mismatched+=1
            if first is None:first=k
    return {'match':mismatched==0,'checked_triangles':count,
            'mismatched_triangles':mismatched,'first_mismatch_index':first}

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

PROBE_FIELDS = {
    'work_items','gpu_hit_items','gpu_positive_contributions',
    'gpu_traversal_mismatches','gpu_positive_traversal_mismatches',
    'gpu_positive_matched_traversal','gpu_positive_shadow_blocked',
    'gpu_positive_shadow_clear','gpu_positive_other_zero',
    'gpu_positive_fixed_prediction_mismatches',
    'gpu_positive_replay_candidate','zero_gpu_but_positive_unshadowed',
    'invalid_gpu_hit_flags','invalid_contribution_ids'
}

def validate_probe_capture(base: Path, files: dict, audit: dict, count: int) -> dict:
    if set(files)!={'work','hits','contributions','audit'}:
        raise ValueError('incomplete GPU probe capture files')
    if not isinstance(count,int) or count<0 or count>100_000_000:
        raise ValueError('invalid GPU work count')
    if set(audit)!=PROBE_FIELDS or any(not isinstance(v,int) or v<0 for v in audit.values()):
        raise ValueError('invalid GPU probe audit')
    if audit['work_items']!=count:
        raise ValueError('GPU work count/audit mismatch')
    for name,size in [('work',64),('hits',32),('contributions',8)]:
        if checked_file(base,files[name]).stat().st_size!=count*size:
            raise ValueError('GPU probe payload byte count mismatch: '+name)
    if audit!=json.loads(checked_file(base,files['audit']).read_text()):
        raise ValueError('GPU probe audit differs from hashed file')
    contrib=checked_file(base,files['contributions']).read_bytes()
    hits=checked_file(base,files['hits']).read_bytes()
    count_positive=sum(v>0 for _,v in struct.iter_unpack('<2I',contrib))
    count_hits=sum(fields[7]==1 for fields in struct.iter_unpack('<4f4I',hits))
    if count_positive!=audit['gpu_positive_contributions'] or count_hits!=audit['gpu_hit_items']:
        raise ValueError('GPU probe audit disagrees with raw GPU payload')
    if audit['gpu_traversal_mismatches']>count or (
        audit['gpu_positive_traversal_mismatches']>audit['gpu_traversal_mismatches']):
        raise ValueError('GPU probe traversal mismatch counters invalid')
    if audit['gpu_positive_matched_traversal']+audit['gpu_positive_traversal_mismatches']>count_positive:
        raise ValueError('GPU probe matched-positive overflow')
    if (audit['gpu_positive_shadow_blocked']+
        audit['gpu_positive_shadow_clear']+
        audit['gpu_positive_other_zero'])!=audit['gpu_positive_matched_traversal']:
        raise ValueError('GPU probe matched-positive shadow counts invalid')
    if audit['gpu_positive_replay_candidate']>audit['gpu_positive_shadow_blocked']:
        raise ValueError('GPU shadow candidate exceeds occluded count')
    return audit

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
    if set(data)!={'schema_version','frame','state_files','cpu','gpu',
                   'cpu_counts','probe_work_items','gpu_probe','gpu_probe_audit'}:
        raise ValueError('manifest structure mismatch')
    states=data['state_files']
    required={'frame','geometry'}
    if frame['backend']=='software':
        required.add('gpu_primary_geometry')
    if set(states)!=required:
        raise ValueError('required CPU/GPU raw state snapshots missing')
    base=path.resolve().parent
    for key,declared in (('frame','frame_state_sha256'),('geometry','geometry_state_sha256')):
        checked_file(base,states[key])
        if states[key]['sha256']!=frame[declared]:
            raise ValueError(f'{key} state SHA differs from recorded fingerprint')
    geometry_attestation=None
    if frame['backend']=='software':
        geometry_attestation=software_primary_geometry(
            checked_file(base,states['geometry']),
            checked_file(base,states['gpu_primary_geometry']))
    cpu=components(base,data['cpu'],w*h,(w,h))
    gpu=components(base,data['gpu'],w*h,(w,h))
    probe_audit=validate_probe_capture(base,data['gpu_probe'],
        data['gpu_probe_audit'],data['probe_work_items'])
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
    geometry_match=geometry_attestation is None or geometry_attestation['match']
    testable=primary['match'] and direct_match and reconstruction and geometry_match
    probe_replay_testable=testable and probe_audit['gpu_positive_matched_traversal']>0 and (
        probe_audit['gpu_positive_fixed_prediction_mismatches']==0 and
        probe_audit['invalid_gpu_hit_flags']==0 and
        probe_audit['invalid_contribution_ids']==0)
    blockers=(['primary_hit_mismatch'] if not primary['match'] else []) + (
        ['direct_mismatch'] if not direct_match else []) + (
        ['component_reconstruction_mismatch'] if not reconstruction else []) + (
        ['gpu_primary_triangle_bytes_mismatch'] if not geometry_match else []) + (
        ['gpu_probe_replay_fixed_mismatch'] if probe_audit[
            'gpu_positive_fixed_prediction_mismatches'] else []) + (
        ['gpu_probe_payload_invalid'] if (
            probe_audit['invalid_gpu_hit_flags'] or
            probe_audit['invalid_contribution_ids']) else []) + [
        'gpu_camera_ubo_and_secondary_state_not_independently_attested'
        if geometry_match and geometry_attestation is not None
        else 'gpu_geometry_upload_and_source_state_not_independently_attested']
    return {
        'schema_version':1,'classification':'diagnostic-only','frame':frame,
        'primary':primary,'signal':signal,
        'primary_geometry_attestation':geometry_attestation,
        'gpu_probe_shadow_audit':probe_audit,
        'probe_shadow_replay_testable':probe_replay_testable,
        'gpu_probe_shadowed_positive_detected':
            probe_replay_testable and probe_audit['gpu_positive_replay_candidate']>0,
        'component_comparison':comparison,
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
