#!/usr/bin/env python3
"""Plan158: full raw-chain verification; never an all-split admission API."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys

import diagnose_selected_bounce_paths as D
import acquire_compensated_state_prefix as S
from run_primary_direction_sequence import require_no_other_research_worker

HELPERS = D.HERE.parent/'n010_comparison_readiness'
sys.path.insert(0,str(HELPERS))
import qualify_references as Q

PLAN = D.RESULTS.parent/'experiments/158-compensated-reference-raw-chain.md'
ORIGINAL = HELPERS/'point_guided_reference_provenance.py'
ORIGINAL_SHA = 'e22bb5b1e28e3c8463f5ecbb1049305ae6e4b566b9f81c9e6c21a891eba95e91'
VARIANT = 'compensated-all-split-mixture-v1'
BINARY = D.OUT/'compensated-prefix-build-v1/n010_compensated_prefix'
REFERENCE_ROOT = D.OUT/'compensated-reference-ladders-v1'
SELECTED = ('C1_T_B8','C2_T_B8','C3_T_B8','C4_T_B8','C5_T_B2','C5_T_B8','C6_T_B2','C6_T_B8')
PROOFS = ('452-compensated-full-exporter-build.json','525-compensated-prefix-source-prepare.json',
          '526-compensated-prefix-build.json','610-compensated-all-state-prefix-summary.json')
DESCRIPTION = D.RESULTS/'611-compensated-reference-chain-description.json'
OUTPUT = D.RESULTS/'612-compensated-reference-raw-chains.json'
COUNTERS = ('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')


def prerequisites(inputs):
    S.prerequisites()
    summary = S.L.bind(S.SUMMARY)
    source,edits,proof = S.program()
    scope = dict(__name__='n010_plan158_prefix',__file__=str(Path(S.__file__).resolve()),
        CANDIDATE_PLAN=S.PLAN,CANDIDATE_BASE=S.BASE,CANDIDATE_SUMMARY=S.SUMMARY,
        candidate_prerequisites=S.prerequisites,isolated_native=S.isolated_native,
        source_edits=edits,generated_program=source,composition_proof=proof)
    exec(compile(source,str(S.ORIGINAL)+'#plan158-readonly','exec'),scope)
    original,_ = scope['original_slots']()
    expected = [str(scope['paths'](case,phase)[0]) for case in range(26) for phase in range(3)]
    if (not summary['all_pass'] or summary['numerical_variant'] != 'compensated-raw-target-v1'
            or summary['records'] != expected or summary['native_invocations'] != 78
            or summary['low_dose_cases'] != 24 or summary['actual_prefix_cases'] != 2):
        raise ValueError('complete candidate state/prefix scope required')
    for case in range(26):
        slot = scope['selected_slot'](original,case);small,full = (8,16) if case < 24 else (8192,16384)
        for phase in range(3):
            record = scope['terminal'](case,phase)
            if ((record['cell'],record['vertices'],record['spp'],record['begin_spp']) !=
                    (slot['cell'],slot['vertices'],small if phase == 1 else full,small if phase == 2 else 0)
                    or (phase == 2 and not record['all21_payloads_scored_counters_and_interval_audits_exact'])):
                raise ValueError('candidate state/prefix record scope differs')
            for name,digest in record['input_sha256'].items():D.checked(Path(name),digest)
    for name,digest in list(D.INPUTS.items()):
        D.checked(Path(name),digest)
        if name in inputs and inputs[name] != digest:raise ValueError('conflicting chain input identity')
        inputs[name] = digest
    return {name:hashlib.sha256(D.checked(D.RESULTS/name)).hexdigest() for name in PROOFS}


def program():
    original = D.checked(ORIGINAL,ORIGINAL_SHA).decode();source = original;edits = []
    def change(before,after):
        nonlocal source
        source = D.once(source,before,after);edits.append((before,after))
    change("VARIANT = 'validated-point-guided-mixture'",'VARIANT = '+repr(VARIANT))
    change("BINARY = ROOT/'out/research/n010-comparison-readiness/point-guided-prefix-build-v1/n010_point_guided_prefix'",'BINARY = Path('+repr(str(BINARY))+')')
    change("KEYS = ('primary_hits', 'shadow_tests', 'shadow_blocked', 'backface_absorbed', 'proposal_null_samples')",'KEYS = '+repr(COUNTERS))
    start,end = source.index('PROOFS = ('),source.index('\n\ndef prerequisites(inputs):')
    change(source[start:end],'PROOFS = '+repr(PROOFS)+'\nSELECTED = '+repr(SELECTED)+'\n')
    start,end = source.index('def prerequisites(inputs):'),source.index('\ndef verify_reference(')
    change(source[start:end],'def prerequisites(inputs):\n    return _prerequisites(inputs)\n\n')
    change("Path(__file__).with_name('qualify_point_guided_references.py')",'Path(_chain_implementation)')
    change("'--spp', str(spp), '--threads', '16']","'--spp', str(spp), '--threads', '1']")
    change("';'.join(','.join(str(r[k]) for k in KEYS) for r in pm['runs'])", "';'.join(','.join(str(r[k]) for k in KEYS)+',0' for r in pm['runs'])")
    change("                or run['primary_hits'] > state['width']*state['height']*spp\n"
           "                or run['proposal_null_samples'] > state['width']*state['height']*spp\n",
           "                or run['primary_hits'] > state['width']*state['height']*spp\n")
    inverse = source
    for before,after in reversed(edits):inverse = D.once(inverse,after,before)
    if inverse != original:raise ValueError('whole retained reference verifier inverse differs')
    # Substitutions above do not touch actual assessor/manifest/support/SE/stop code.
    def suffix(text):return text[text.index('        manifest_path = directory/') :]
    if suffix(source) != suffix(original):raise ValueError('screen/support/SE/stop source changed')
    ast.parse(source)
    return source,edits,dict(whole_original_source_inverse_exact=True,
        assessor_manifest_signal_support_replicate_se_stop_bytes_exact=True,
        original_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(source.encode()).hexdigest())


def verify_raw_chain(directory,cell,vertices,spec,inputs,require_eligible=True):
    directory = directory.resolve();name = f'{cell}_T_B{vertices}'
    if name not in SELECTED or directory != REFERENCE_ROOT/name:
        raise ValueError('exact existing eight-slot raw-chain root required')
    q = json.loads(D.checked(directory/'qualification.json'))
    if q['computational_variant'] != VARIANT:raise ValueError('unknown raw-chain variant')
    source,_,composition = program()
    for path in (PLAN,Path(__file__).resolve(),ORIGINAL,Path(S.__file__).resolve(),S.PLAN,
                 Path(S.L.__file__).resolve(),S.L.PLAN,Path(Q.__file__).resolve(),
                 Path(Q.L.__file__).resolve(),Path(Q.convergence.__file__).resolve()):
        inputs[str(path)] = hashlib.sha256(D.checked(path)).hexdigest()
    scope = dict(__name__='n010_plan158_raw_only',__file__=str(Path(__file__).resolve()),
                 _prerequisites=prerequisites,_chain_implementation=str(Path(__file__).resolve()))
    exec(compile(source,str(ORIGINAL)+'#plan158-raw-only','exec'),scope)
    result = scope['verify_reference'](directory,cell,vertices,spec,inputs,require_eligible)
    for level in q['levels']:
        spp = level['spp'];meta = scope['read'](directory/f'n{spp}.meta.json',inputs)
        raw = scope['read'](directory/f'n{spp}.stdout.json',inputs)
        attempt = scope['read'](directory/f'n{spp}.attempt.json',inputs)
        receipt_path = directory/f'n{spp}.resource-limits.json'
        receipt = scope['read'](receipt_path,inputs)
        if (receipt['cpu'] != [172800]*2 or receipt['address_space'] != [4*1024**3]*2
                or receipt['affinity'] != [31] or receipt['nice'] != 15
                or receipt['command'] != attempt['command'] or receipt['elapsed_guard_seconds'] != 43200
                or type(receipt['pid']) is not int or receipt['pid'] <= 0 or receipt['pgid'] != receipt['pid']
                or type(receipt['start_ticks']) is not int or receipt['start_ticks'] <= 0
                or not isinstance(receipt['boot_id'],str) or len(receipt['boot_id']) != 36
                or attempt['native_pid'] != receipt['pid'] or not attempt['native_terminal']
                or meta['resource_limits_sha256'] != scope['sha'](receipt_path)
                or attempt['resource_limits_sha256'] != scope['sha'](receipt_path)
                or not 0 <= attempt['child_cpu_seconds'] <= 172800
                or not 0 <= attempt['wall_seconds_diagnostic'] < 43200
                or meta['prefix_begin'] != meta['sample_interval'][0]
                or raw['prefix_begin'] != meta['sample_interval'][0]
                or meta['audit_scope'] != 'new_sample_interval' or raw['audit_scope'] != meta['audit_scope']):
            raise ValueError('actual raw-chain resource/interval/terminal identity differs')
        for run in meta['runs']:
            audit = run['all_split']
            counts = ('auxiliary_primary_primes','proposal_bvh_queries','component_attempts','component_nulls','own_checks')
            maxima = ('max_own_log_error','max_conditioned_error_fraction','max_unconditioned_error_fraction')
            if (any(type(audit[key]) is not int or audit[key] < 0 for key in counts)
                    or audit['own_checks'] != audit['component_attempts']-audit['component_nulls']
                    or any(type(audit[key]) not in (int,float) or not scope['np'].isfinite(audit[key]) or audit[key] < 0 for key in maxima)
                    or audit['max_own_log_error'] > 1e-6 or audit['max_conditioned_error_fraction'] > 1):
                raise ValueError('actual full interval proposal/null/numerical audit differs')
    result.pop('pass')
    result.update(raw_chain_valid=True,reference_admission=False,source_composition=composition,
        classification='RAW_CHAIN_VALID_NO_DENSITY_BIAS_OR_REFERENCE_ADMISSION')
    scope['check_files'](inputs,{})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--describe',action='store_true');group.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    os.sched_setaffinity(0,{31});priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if any(os.environ.get(key) != '1' for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,((120,120) if args.describe else (1200,1200)))
    resource.setrlimit(resource.RLIMIT_AS,((2 if args.describe else 4)*1024**3,)*2)
    signal.alarm(180 if args.describe else 1800)
    if args.audit:require_no_other_research_worker()
    output = DESCRIPTION if args.describe else OUTPUT
    if output.exists():raise ValueError('fresh registered output required; no overwrite')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),S.PLAN,Path(S.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact158/157 source/recipe before use')
    _,edits,proof = program()
    for path in (Path(Q.__file__).resolve(),Path(Q.L.__file__).resolve(),Path(Q.convergence.__file__).resolve(),
                 Path(D.__file__).resolve(),Path(S.L.__file__).resolve(),Path(S.L.G.__file__).resolve(),
                 D.HERE/'run_primary_direction_sequence.py'):D.checked(path)
    result = dict(schema='n010-compensated-reference-raw-chain/1',complete=False,
        source_commit=commit,input_sha256=D.INPUTS,source_composition=proof,source_edits=edits,
        selected_transports=list(SELECTED),levels=list(Q.LEVELS),variant=VARIANT,rows=[],
        reference_admission=False,final_handoff_admitted=False,gpu_run=False,native_executed=False,
        tests='NOT_RUN; source metadata or scientific raw-chain replay only')
    if args.describe:
        result.update(complete=True,source_metadata_valid=True,raw_chains_replayed=False,
            classification='COMPENSATED_RAW_CHAIN_SOURCE_ONLY_ADMISSION_UNIMPLEMENTED')
    else:
        lock = json.loads(D.checked(D.RESULTS/'016-corpus-state-lock.json'))
        if set(lock['cells']) != {f'C{i}' for i in range(1,13)}:raise ValueError('complete corpus lock required')
        for name in SELECTED:
            cell,text = name.rsplit('_T_B',1);vertices = int(text)
            try:row = verify_raw_chain(REFERENCE_ROOT/name,cell,vertices,lock['cells'][cell],D.INPUTS)
            except (ValueError,OSError,KeyError,AssertionError) as error:row = dict(cell=cell,vertices=vertices,raw_chain_valid=False,failure=str(error))
            result['rows'].append(row)
        result.update(complete=True,raw_chains_replayed=True,
            all_raw_chains_valid=all(row['raw_chain_valid'] for row in result['rows']),
            classification='RAW_CHAIN_REPLAY_ONLY_NOT_REFERENCE_ADMISSION')
    for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)
    with output.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])
    return 0 if args.describe or result['all_raw_chains_valid'] else 2


if __name__ == '__main__':raise SystemExit(main())
