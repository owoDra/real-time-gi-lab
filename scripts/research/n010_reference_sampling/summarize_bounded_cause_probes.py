#!/usr/bin/env python3
"""Post-hoc replay of completed 195--197; no acquisitions or admission."""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
sys.path.insert(0, str(ROOT/'scripts/research/n010_comparison_readiness'))
import calibrate_renderer as C
from readiness_preflight import replay
from run_primary_direction_sequence import require_no_other_research_worker

INPUTS = {}


def read(path, expected=None):
    path = Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('input identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed: '+str(path))
    INPUTS[str(path)] = digest
    return raw


def describe(values):
    return dict(count=len(values), minimum=min(values),
                median=statistics.median(values), maximum=max(values))


def main():
    output = RESULTS/'198-bounded-cause-probes-posthoc-replay.json'
    if output.exists():
        raise ValueError('refuse existing post-hoc report')
    require_no_other_research_worker()
    os.sched_setaffinity(0, {max(os.sched_getaffinity(0))})
    os.nice(15)
    read(__file__)
    read(C.__file__, '64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d')
    read(sys.modules['readiness_preflight'].__file__)
    read(sys.modules['run_primary_direction_sequence'].__file__)
    sizing = json.loads(read(RESULTS/'185-deferred-image-calibration-sizing.json',
        '58dba169986246adc16898e89f351d6ca1643d6e16a9f247e6934183f3838b32'))
    dose = next(r['frozen_dose'] for r in sizing['rows'] if r['boundary']['id']=='C7-hwrt')
    grid_path = RESULTS/'195-fixed-grid-scramble-diagnosis.json'
    grid = json.loads(read(grid_path,
        'fb8241581d78b70cfc2c6db6e73643021392b051f370472d6c10a58618471733'))
    if not grid['complete'] or grid['reference_admission']:
        raise ValueError('grid scope differs')
    variants = {r['variant']:r for r in grid['variants']}
    ratios = {k:variants['nested'][k]/variants['original'][k] for k in
              ('indirect_replicate_variance_sum','max_pairwise_indirect_p99','mean_path_variance_sum')}
    campaigns = []
    for number, digest in (
        (196, '24833b87c6edfd8e748687ab5f5efc8971bfdb998515f687331f1f7aec6c986f'),
        (197, 'd07cd05eca73c18e0e9bc0f755e6674d73963f8ff0db2aa2b17def783a79fe71')):
        path = next(RESULTS.glob(f'{number}-*.json'))
        data = json.loads(read(path, digest))
        if not data['complete'] or not data['diagnostic_only'] or data['accepted_timing'] or len(data['rows'])!=1:
            raise ValueError('diagnostic scope differs')
        row = data['rows'][0]
        if row['boundary']['id']!='C7-hwrt' or len(row['blocks'])!=8:
            raise ValueError('cohort differs')
        decision = C.analysis(row['blocks'])
        if decision!=row['analysis'] or data['all_pass']!=decision['all_pass']:
            raise ValueError('original numerical decision replay differs')
        receipts = data['diagnostic_native_resources']
        if len(receipts)!=8:
            raise ValueError('resource receipt count differs')
        for i,(block,receipt) in enumerate(zip(row['blocks'],receipts)):
            tags = block['tagged_samples']
            schedule = C.schedule(dose,i)
            if (len(tags)!=64 or len(block['samples'])!=64 or
                any(any(sample[k]!=record[k] for k in record) for sample,record in zip(tags,schedule)) or
                any(any(tag[k]!=sample[k] for k in sample) for tag,sample in zip(tags,block['samples']))):
                raise ValueError('original sample schedule differs')
            actual = json.loads(read(receipt['receipt_path'],receipt['receipt_sha256']))
            if (actual!=receipt['actual'] or actual['cpu']!=[30,30] or
                actual['elapsed_limit_seconds']!=30 or receipt['returncode']!=0 or
                actual['command']!=block['command'] or block['returncode']!=0):
                raise ValueError('native resource receipt differs')
            if not replay(block['allocation_ledger']) or not block['allocation_ledger_replay_pass']:
                raise ValueError('owned ledger replay failed')
            out = Path(block['command'][block['command'].index('--out')+1])
            spool = json.loads(read(out/'deferred-image-serialization.json',
                block['deferred_image_serialization_sha256']))
            if (spool!=block['deferred_image_serialization'] or not spool['complete'] or
                spool['written_frames']!=64 or spool['retained_frames']!=64 or
                spool['rgba_capacity_bytes_after_flush']!=0 or
                spool['rgba_capacity_peak_bytes']>spool['rgba_capacity_limit_bytes']):
                raise ValueError('CPU spool receipt differs')
            if not all(block[k] for k in ('known_work_probe_validation','images_byte_equal','images_byte_equal_to_original_046')):
                raise ValueError('acquisition image/scratch validation absent')
        samples = [s for block in row['blocks'] for s in block['samples']]
        zero = [s for s in samples if s['dose']==0]
        campaigns.append(dict(result=number, numerical_analysis_replay_exact=True,
            all_512_schedule_and_sample_records_replayed=True, native_receipts_rehashed=True,
            all_owned_ledgers_replayed=True, cpu_spool_receipts_rehashed=True,
            acquisition_image_scratch_checks_all_pass=True,
            independent_full_native_payload_rehash=False,
            all_pass=decision['all_pass'], original_analysis=decision,
            gpu_interval_sum_seconds=sum(s['gpu_us'] for s in samples)*1e-6,
            zero_dose_full_gpu_us=describe([s['gpu_us'] for s in zero]),
            zero_dose_known_work_gpu_us=describe([s['known_work_gpu_us'] for s in zero]),
            maximum_true_peak_owned_bytes=max(b['allocation_ledger']['true_peak_owned_bytes'] for b in row['blocks'])))
    observation = data['natural_idle_observation']
    if not observation['user_declared_idle']:
        raise ValueError('idle observation missing')
    external = []
    for client, deltas in observation['surviving_client_engine_deltas_ns'].items():
        if any(not isinstance(v,int) or v<0 for v in deltas.values()):
            raise ValueError('counter reset requires separate interpretation')
        if any(deltas.values()):
            external.append(dict(client=client,
                processes=observation['after']['clients'][client]['processes'],
                engine_delta_milliseconds={k:v/1e6 for k,v in deltas.items()}))
    require_no_other_research_worker()
    for p,digest in list(INPUTS.items()):
        read(p,digest)
    result = dict(schema='n010-bounded-cause-probes-posthoc-replay/1',
        complete=True, classification='POST_HOC_DIAGNOSIS_NO_ADMISSION',
        gpu_run=False, source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256=INPUTS, tests='NOT_RUN; scientific retained-data replay only',
        reference_admission=False, accepted_timing=False, n010_ready=False,
        fixed_grid_nested_over_original=ratios,
        fixed_grid_scope='256 prospectively fixed C1 pixels; 8192 and four seeds; no whole-frame, second-level or other-state admission',
        timing_diagnostics=campaigns,
        idle_observation=dict(
            coarse_interval_seconds=(observation['after']['end_monotonic_ns']-observation['before']['start_monotonic_ns'])*1e-9,
            clients_with_positive_engine_deltas=external,
            inaccessible_same_uid_pids_before=observation['before']['inaccessible_same_uid_pids'],
            inaccessible_same_uid_pids_after=observation['after']['inaccessible_same_uid_pids'],
            created_clients=observation['created_clients'], disappeared_clients=observation['disappeared_clients'],
            scope='No exact per-query overlap, global-quiescence, causal interference or clock/power diagnosis'),
        conclusion='Neither nested scrambling on this fixed grid nor deferred serialization plus a user-idle interval establishes the required repair. No full reference ladder or full 186 is dispatched by this replay.')
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(complete=True,report=str(output),fixed_grid_ratios=ratios,
                         timing_all_pass=[c['all_pass'] for c in campaigns]),indent=2))


if __name__=='__main__':
    main()
