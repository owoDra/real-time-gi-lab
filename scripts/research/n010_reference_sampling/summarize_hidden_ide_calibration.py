#!/usr/bin/env python3
"""Post-hoc CPU replay of all retained 178 decisions; never acquire/correct timing."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

from hidden_ide_timing_provenance import (
    ROOT, HERE, RESULTS, D, replay_environment, verify_calibration,
)
from reference_provenance import read
from qualify_hybrid_references import check_files
from readiness_preflight import replay
from run_primary_direction_sequence import require_no_other_research_worker
import calibrate_renderer as C

OUTPUT = RESULTS/'179-hidden-ide-calibration-decision-and-replay.json'
CALIBRATION = RESULTS/'178-hidden-ide-bulk-pfm-calibration-full-renderer.json'
CORE_SHA = '64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    require_no_other_research_worker()
    D.require(args.output.resolve()==OUTPUT and not OUTPUT.exists(),'fresh registered CPU replay output required')
    inputs = {}
    calibration = read(CALIBRATION,inputs)
    policy_path = ROOT/'out/research/n010-comparison-readiness/hidden-ide-bulk-pfm-accepted-v1/visibility-policy.json'
    policy = read(policy_path,inputs)
    D.require(policy.get('complete') and policy==calibration.get('visibility_policy')
        and D.sha(policy_path)==calibration.get('visibility_policy_sha256'),
        'terminal source-bound calibration/environment record required')
    core = Path(C.__file__).resolve()
    D.require(D.sha(core)==CORE_SHA,'original scientific calibration source changed')
    lock_path = RESULTS/'026-dynamic-execution-state-lock.json'
    lock = read(lock_path,inputs)
    sizing_path = RESULTS/'177-hidden-ide-bulk-pfm-calibration-sizing.json'
    sizing = read(sizing_path,inputs)
    cohort = C.boundaries(lock)
    D.require(calibration['schema']=='n010-hidden-ide-bulk-pfm-renderer-calibration/1'
        and calibration['mode']=='accepted' and calibration['lock_sha256']==D.sha(lock_path)
        and calibration['plan_sha256']==D.sha(sizing_path)
        and sizing['complete'] and sizing['all_pass']
        and [r['boundary'] for r in sizing['rows']]==cohort
        and [r['boundary'] for r in calibration['rows']]==cohort[:len(calibration['rows'])],
        'original fixed full-corpus order/actual sizing identity differs')
    check_files(calibration['fixture_input_sha256'],inputs)
    rows = []
    peak = blocks_replayed = samples_replayed = 0
    for index,row in enumerate(calibration['rows']):
        boundary = cohort[index]
        dose = sizing['rows'][index]['frozen_dose']
        blocks = row['blocks']
        D.require(1<=len(blocks)<=8,'retained block scope differs')
        for block_index,block in enumerate(blocks):
            records = C.schedule(dose,block_index)
            expected = [dict(s,**{k:v for k,v in r.items() if k not in s})
                        for s,r in zip(block['samples'],records)]
            D.require(block['boundary']==boundary and block['returncode']==0
                and len(block['samples'])==64 and block['tagged_samples']==expected
                and [s['dose'] for s in block['samples']]==[r['dose'] for r in records]
                and replay(block['allocation_ledger']) and block['allocation_ledger_replay_pass'],
                'original retained schedule/sample or owned-memory ledger replay differs')
            peak = max(peak,block['allocation_ledger']['true_peak_owned_bytes'])
            blocks_replayed += 1
            samples_replayed += len(block['samples'])
        summary = {'boundary':boundary['id'],'blocks_replayed':len(blocks),
                   'raw_blocks_complete':len(blocks)==8,
                   'scientific_boundary_complete':len(blocks)==8 and 'analysis' in row,
                   'numerical_verdict':'INCOMPLETE_NOT_ASSIGNED'}
        if summary['scientific_boundary_complete']:
            actual = C.analysis(blocks)
            D.require(actual==row.get('analysis'),'original eight-block analysis replay differs')
            summary.update(numerical_verdict='PASS' if actual['all_pass'] else 'FAIL',
                           analysis=actual)
        elif len(blocks)<8:
            D.require('analysis' not in row,'partial boundary cannot have full scientific decision')
        rows.append(summary)
    scientific_complete = len(rows)==16 and all(r['scientific_boundary_complete'] for r in rows)
    if calibration['complete']:
        D.require(scientific_complete,'complete calibration omitted required original scope')
        D.require(calibration['numerical_all_pass']==all(r['numerical_verdict']=='PASS' for r in rows),
                  'stored full scientific decision differs')
    environment = {'replay_pass':False}
    try:
        replay_environment(calibration,'accepted',inputs)
        environment['replay_pass'] = True
    except (ValueError,OSError,KeyError) as error:
        environment['failure'] = str(error)
    admission = {'accepted':False}
    try:
        admission['proof'] = verify_calibration(lock_path,inputs)
        admission['accepted'] = True
    except (ValueError,OSError,KeyError) as error:
        admission['failure'] = str(error)
    for p in (Path(__file__).resolve(),core,HERE/'hidden_ide_timing_provenance.py',
              RESULTS.parent/'experiments/052-prospective-hidden-ide-full-calibration.md'):
        inputs[str(p)] = D.sha(p)
    check_files(inputs,{})
    require_no_other_research_worker()
    result = {'schema':'n010-hidden-ide-calibration-decision-and-replay/1',
        'complete':True,'gpu_run':False,'analysis_status':'POST_HOC_CPU_REPLAY_NO_NEW_MEASUREMENT',
        'classification':('COMPLETE_CALIBRATION_FULL_PROOF_ACCEPTED' if admission['accepted']
            else 'COMPLETE_CALIBRATION_FAIL_NOT_ACCEPTED' if calibration['complete']
            else 'INCOMPLETE_CALIBRATION_NOT_ACCEPTED'),
        'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'calibration':{'path':str(CALIBRATION.relative_to(ROOT)),'sha256':D.sha(CALIBRATION),
                       'bytes':CALIBRATION.stat().st_size,'complete':calibration['complete'],
                       'all_pass':calibration['all_pass']},
        'required_boundaries':16,'completed_boundaries':sum(r['scientific_boundary_complete'] for r in rows),
        'passing_boundaries':sum(r['numerical_verdict']=='PASS' for r in rows),
        'failing_boundaries':sum(r['numerical_verdict']=='FAIL' for r in rows),
        'rows':rows,'process_blocks_replayed':blocks_replayed,'timestamp_samples_replayed':samples_replayed,
        'all_retained_original_schedules_and_analysis_replay_exact':True,
        'all_retained_ledgers_teardown_zero_within_8_GiB':True,
        'maximum_true_peak_owned_bytes':peak,'environment':environment,'strict_admission':admission,
        'accepted_timing':admission['accepted'],'subset_accepted':False,
        'thresholds_changed':False,'retry':False,'input_sha256':inputs,
        'fixture_input_hash_count_rechecked':len(calibration['fixture_input_sha256']),
        'full_raw_native_payload_manifest_replay_complete':admission['accepted'],
        'payload_scope':'Producer image/scratch/native manifests retained in exact 178. Strict intake rejects incomplete/scientifically failed inputs before native payload replay. Full accepted intake requires every native payload; independent summary schedules/statistics/ledgers, environment snapshots and frozen inputs are replayed here. No radiance/timestamp regeneration.',
        'causation':'No causal attribution of prior/current timing failures from visibility/accounting observations.',
        'reference_admission':False,'readiness':'NOT_ESTABLISHED; all original six gates remain mandatory',
        'direct_max_relative_error_1_0':'UNRESOLVED / 未解決; included without masks',
        'tests':'NOT_RUN; scientific-analysis/provenance replay, no software regression claim'}
    OUTPUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ('classification','completed_boundaries','passing_boundaries',
        'failing_boundaries','process_blocks_replayed','timestamp_samples_replayed',
        'maximum_true_peak_owned_bytes','environment','strict_admission')},indent=2))


if __name__=='__main__':
    main()
