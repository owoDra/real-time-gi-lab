#!/usr/bin/env python3
"""Post-hoc description of every retained 169/178 sample; no timing admission."""
import datetime
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
sys.path.insert(0,str(ROOT/'scripts/research/n010_comparison_readiness'))
import calibrate_renderer as C


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(values):
    values = sorted(values)
    if not values or any(not math.isfinite(v) for v in values):
        raise ValueError('invalid retained diagnostic values')
    return {'count':len(values),'minimum':values[0],'median':statistics.median(values),
            'maximum':values[-1],'p10_nearest_rank':values[math.ceil(.1*len(values))-1],
            'p90_nearest_rank':values[math.ceil(.9*len(values))-1]}


def main():
    output = RESULTS/'183-bulk-calibration-precision-posthoc-diagnosis.json'
    if output.exists():
        raise ValueError('refuse existing post-hoc report; no overwrite')
    core = Path(C.__file__).resolve()
    if sha(core)!='64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d':
        raise ValueError('original schedule/analysis source changed')
    inputs = {str(p):sha(p) for p in (Path(__file__).resolve(),core)}
    lock_path = RESULTS/'026-dynamic-execution-state-lock.json'
    lock = json.loads(lock_path.read_bytes()); inputs[str(lock_path)] = sha(lock_path)
    cohort = C.boundaries(lock)
    campaigns = []
    for number,sizing_number,stem,digest,work in (
        (169,168,'bulk-pfm-calibration',
         'dddca3bfa7d2f0847e683352593519165829963d49fd173a29b698ba825d6add',
         'bulk-pfm-calibration-accepted-v1'),
        (178,177,'hidden-ide-bulk-pfm-calibration',
         '1f25e8a3430254b5c010d0208e3e77e3d2d2985aa42421f51de978b219a55870',
         'hidden-ide-bulk-pfm-accepted-v1')):
        path = RESULTS/f'{number}-{stem}-full-renderer.json'
        if sha(path)!=digest:
            raise ValueError('immutable campaign identity changed')
        data = json.loads(path.read_bytes()); inputs[str(path)] = digest
        sizing_path = next(RESULTS.glob(f'{sizing_number}-*.json'))
        sizing = json.loads(sizing_path.read_bytes()); inputs[str(sizing_path)] = sha(sizing_path)
        if (data['mode']!='accepted' or data['all_pass'] or not sizing['all_pass']
            or not sizing['complete'] or data['plan_sha256']!=sha(sizing_path)
            or data['lock_sha256']!=sha(lock_path)
            or [r['boundary'] for r in data['rows']]!=cohort[:len(data['rows'])]):
            raise ValueError('campaign/sizing scope differs')
        campaign = {'result':number,'complete':data['complete'],'accepted':False,'rows':[]}
        for index,row in enumerate(data['rows']):
            boundary = row['boundary']['id']
            blocks = []
            for block_index,block in enumerate(row['blocks']):
                samples = block['tagged_samples']
                schedule = C.schedule(sizing['rows'][index]['frozen_dose'],block_index)
                if (len(samples)!=64 or any(any(s[k]!=r[k] for k in r)
                    for s,r in zip(samples,schedule))):
                    raise ValueError('original fixed sample schedule differs')
                frame_paths = []
                for frame in range(64):
                    directory = ROOT/'out/research/n010-comparison-readiness'/work/boundary/f'block-{block_index}'/'frames'/str(frame)
                    if (directory/'gpu').is_dir():
                        directory = directory/'gpu'
                    frame_paths.append(directory/'total.pfm')
                mtimes = [p.stat().st_mtime_ns for p in frame_paths]
                gaps = [(b-a)/1000 for a,b in zip(mtimes,mtimes[1:])]
                if any(gap<0 for gap in gaps):
                    raise ValueError('retained output mtimes not monotone')
                measured = [s for s in samples if not s['warmup']]
                summary = {'block':block_index,'all_64_samples_retained':True,
                    'file_paths':[str(p.relative_to(ROOT)) for p in frame_paths],
                    'observed_total_file_mtimes_ns':mtimes,
                    'file_gap_us':describe(gaps),
                    'all_frame_gpu_us':describe([s['gpu_us'] for s in samples]),
                    'measured_control_gpu_us':describe([s['gpu_us'] for s in measured if s['kind']=='control']),
                    'measured_effect_gpu_us':describe([s['gpu_us'] for s in measured if s['kind']=='effect']),
                    'measured_renderer_wall_us':describe([s['wall_us'] for s in measured]),
                    'measured_maintenance_gpu_us':describe([s['maintenance_gpu_us'] for s in measured]),
                    'measured_control_known_work_gpu_us':describe([s['known_work_gpu_us'] for s in measured if s['kind']=='control']),
                    'measured_effect_B_known_work_gpu_us':describe([s['known_work_gpu_us'] for s in measured if s['kind']=='effect' and s['arm']=='B']),
                    'diagnostic_gpu_to_file_cadence_ratio':statistics.median(s['gpu_us'] for s in samples)/statistics.median(gaps)}
                blocks.append(summary)
            full = len(blocks)==8 and 'analysis' in row
            analysis = C.analysis(row['blocks']) if full else None
            if full and analysis!=row['analysis']:
                raise ValueError('original complete decision replay differs')
            campaign['rows'].append({'boundary':boundary,'complete_blocks':len(blocks),
                'numerical_verdict':('PASS' if analysis['all_pass'] else 'FAIL') if full else 'INCOMPLETE_NOT_ASSIGNED',
                'original_analysis':analysis,'blocks':blocks,
                'failed_original_gates':[name for name,passed in analysis['gates'].items() if not passed] if full else None})
        campaigns.append(campaign)
    for path,digest in inputs.items():
        if sha(Path(path))!=digest:
            raise ValueError('input changed during CPU diagnosis')
    result = {'schema':'n010-bulk-calibration-precision-posthoc-diagnosis/1',
        'complete':True,'gpu_run':False,'classification':'POST_HOC_DIAGNOSTIC_ONLY_NO_TIMING_ADMISSION',
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':inputs,'campaigns':campaigns,'new_samples':False,'thresholds_changed':False,
        'subtraction_or_correction':False,'subset_accepted':False,
        'scope':'Every complete retained 64-sample block, including warmups, from all 16 boundaries in 169 and all 4 started boundaries in 178. Incomplete native invocation and unstarted boundaries receive no numerical verdict. Original full-boundary analyses exactly replayed.',
        'payload_scope':'Original summary bytes hashed. File mtimes read and retained as filesystem observations only; payload content and all fixture identities not independently rehashed here. No new native execution, timestamps or radiance.',
        'causation':'No controlled causal comparison. Different campaign times, sized doses and environment policies; output-file cadence is not GPU busy/idle time or a clock/power measurement. Known-work/maintenance components are descriptive and never subtracted from full timing.',
        'tests':'NOT_RUN; post-hoc scientific-data description, no runtime regression validation',
        'readiness':'NOT_ESTABLISHED; all original six gates remain mandatory',
        'direct_max_relative_error_1_0':'UNRESOLVED / 未解決; included without masks'}
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    for campaign in campaigns:
        print('campaign',campaign['result'])
        for row in campaign['rows']:
            b=row['blocks'][0]
            print(row['boundary'],row['numerical_verdict'],
                  'GPU median us',round(b['all_frame_gpu_us']['median'],2),
                  'file cadence median us',round(b['file_gap_us']['median'],2),
                  'failed',row['failed_original_gates'])


if __name__=='__main__':
    main()
