#!/usr/bin/env python3
"""Plan152: describe all8 non-PT raw evidence paths; execute no native/replay."""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/152-full-non-pt-raw-evidence-intake.md'
OUTPUT = RESULTS/'511-full-non-pt-raw-intake-description.json'


def main():
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if any(os.environ.get(k) != '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')):
        raise ValueError('one numerical thread required even for source description')
    resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    signal.alarm(60)
    if OUTPUT.exists():raise ValueError('refuse existing metadata output')
    import non_pt_raw_provenance as N
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    inputs, functions = {},{}
    for path in (PLAN,Path(__file__).resolve(),Path(N.__file__).resolve()):
        raw = path.read_bytes()
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))]) != raw:
            raise ValueError('commit exact152 source/recipe before description')
        inputs[str(path)] = hashlib.sha256(raw).hexdigest()
        if path.suffix == '.py':
            tree = ast.parse(raw,filename=str(path))
            functions[str(path)] = {n.name:hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest()
                for n in tree.body if isinstance(n,ast.FunctionDef)}
    def read(path):
        raw = path.read_bytes();inputs[str(path)] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)
    scope = read(RESULTS/'503-selected-reportable-timing-scope.json')
    build, lock = read(N.BUILD),read(N.LOCK)
    selected = {r['id'] for r in scope['rows'] if not r['role'].startswith('pt-')}
    if selected != set(N.SCOPE) or len(selected) != 8 or scope['full_union_count'] != 36:
        raise ValueError('original full8/non-PT union36 identities differ')
    if not (build['complete'] and build['build_valid']):raise ValueError('actual506 private build required')
    for path in map(Path,build['binaries'].values()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if build['payload_sha256'][str(path)] != digest:raise ValueError('506 executable bytes changed')
        inputs[str(path)] = digest
    rows, number = [],513
    for boundary in N.SCOPE:
        work = ROOT/'out/research/n010-comparison-readiness/raw-query-pilot-cases-v1'/boundary
        cell, role, dynamic = N.identity(boundary)
        retained = boundary == 'static-C7-dense-rc'
        row = dict(boundary_id=boundary,cell=cell,role=role,dynamic=dynamic,frames=5 if dynamic else 1,
            command=N.command(boundary,work/'capture',build,lock),
            environment_switches={'PHOS_N010_RAW_QUERY_CAPTURE':str(work/'raw-queries.jsonl')},
            native_acquisition_implemented=False,full_intake_runtime_executed=False)
        if role != 'dense-rc':
            row['environment_switches'].update(PHOS_N010_MEMORY_LEDGER=str(work/'capture/allocation-ledger.json'),
                PHOS_N009_CONTRACT=str(N.CONTRACT))
        if retained:
            row.update(retained_native=str(RESULTS/'507-raw-query-static-c7-dense-pilot.json'),
                explicit_posthoc_replay=str(RESULTS/'509-posthoc-c7-dense-raw-query-replay.json'),
                repeat_forbidden=True)
        else:
            row.update(future_result=str(RESULTS/f'{number}-raw-query-{boundary}-pilot.json'),
                fresh_work_required=not work.exists())
            number += 1
        rows.append(row)
    result = dict(schema='n010-full-non-pt-raw-intake-description/1',complete=True,
        classification='FULL_EIGHT_ROLE_INTAKE_SOURCE_AND_COMMAND_METADATA_ONLY',
        source_commit=commit,input_sha256=inputs,source_function_ast_sha256=functions,
        rows=rows,non_pt_count=8,new_trajectory_commands=7,retained_native_count=1,
        native_executed=False,raw_evidence_replayed=False,quality_scoring_executed=False,
        accepted_timing=False,reference_admission=False,final_handoff_admitted=False,
        remaining=['One-case bounded acquisition driver','Actual independent full8 raw intake execution',
            'Independent setup/readback/submit/wait receipts and final cost accounting',
            'Full36 union/final120 auditor and all-split reference dispatch'],
        tests='NOT_RUN; source/AST/command/binary-identity metadata only')
    with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    signal.alarm(0)
    print(result['classification'],len(rows))


if __name__ == '__main__':main()
