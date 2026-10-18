#!/usr/bin/env python3
"""Plan157: unchanged109 full state/prefix science for the compensated candidate."""
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
import cover_wide8_original_controls as C
import acquire_compensated_level5_full as L

PLAN = D.RESULTS.parent/'experiments/157-compensated-all-state-prefix-acquisition.md'
DESCRIPTION = D.RESULTS/'531-compensated-state-prefix-description.json'
BASE = D.OUT/'compensated-state-prefix-v1'
SUMMARY = D.RESULTS/'610-compensated-all-state-prefix-summary.json'
ORIGINAL = D.HERE/'acquire_wide8_state_prefix.py'
ORIGINAL_SHA = 'f4245ab95bd2fef5836c2957407cc389315a85d1ab8b4e8b9d4ab23796495e98'


def prerequisites():
    L.prerequisites()
    diag = L.bind(L.OUTPUT)
    if (not diag['all_pass'] or not diag['terminal_identity_verified']
            or diag['numerical_variant'] != 'compensated-raw-target-v1'
            or diag['physical_gate_decision'] != 'NOT_APPLICABLE_ORIGINAL_DIAGNOSTIC_ONLY'):
        raise ValueError('complete separate candidate level5 diagnostic required')
    prep = L.bind(D.RESULTS/'525-compensated-prefix-source-prepare.json')
    build = L.bind(D.RESULTS/'526-compensated-prefix-build.json')
    if (not prep['source_preparation_valid'] or not build['build_valid']
            or not build['terminal_identity_verified']
            or build['numerical_variant'] != 'compensated-raw-target-v1'):
        raise ValueError('exact candidate source/prefix compiler proof required')
    return build


def program():
    original = D.checked(ORIGINAL,ORIGINAL_SHA).decode();source = original;edits = []
    def replace(before,after):
        nonlocal source
        source = D.once(source,before,after);edits.append((before,after))
    replace("PLAN = D.RESULTS.parent / 'experiments/109-wide8-state-prefix-checkpoints.md'",'PLAN = CANDIDATE_PLAN')
    replace("BASE = D.OUT / 'wide8-state-prefix-v1'",'BASE = CANDIDATE_BASE')
    replace("SUMMARY = D.RESULTS / '351-wide8-all-state-prefix-summary.json'",'SUMMARY = CANDIDATE_SUMMARY')
    replace("f'{273+3*case+phase:03d}-wide8-state-prefix-{label}.json'", "f'{532+3*case+phase:03d}-compensated-state-prefix-{label}.json'")
    replace('    os.nice(15)', '    priority = os.getpriority(os.PRIO_PROCESS,0)\n    if priority < 15:os.nice(15-priority)')
    start,end = "    for stem in ('225',", '    if args.summarize:\n        resource.setrlimit'
    old = source[source.index(start):source.index(end)]
    replace(old,'    candidate_prerequisites()\n')
    replace("'wide8-cpu-bvh-v1/n010_wide8_exporter' if phase == 0\n                      else 'wide8-prefix-build-v1/n010_wide8_prefix'",
        "'compensated-full-deterministic-v1/build/n010_compensated_exporter' if phase == 0\n                      else 'compensated-prefix-build-v1/n010_compensated_prefix'")
    replace("    work.mkdir(parents=True)", "    work.mkdir(parents=True)\n    (work/'generated-driver.py').write_text(generated_program)\n    (work/'source-edits.json').write_text(json.dumps(source_edits,indent=2)+'\\n')")
    for before,after in (
        ("schema='n010-wide8-all-state-prefix-summary/1'", "schema='n010-compensated-all-state-prefix-summary/1', numerical_variant='compensated-raw-target-v1', source_composition_proof=composition_proof"),
        ("schema='n010-wide8-state-prefix-step/1'", "schema='n010-compensated-state-prefix-step/1', numerical_variant='compensated-raw-target-v1', source_composition_proof=composition_proof"),
    ):replace(before,after)
    replace("receipt.write_text(json.dumps(dict(pid=os.getpid(),", "receipt.write_text(json.dumps(dict(pid=os.getpid(), pgid=os.getpgrp(),\n            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),elapsed_limit_seconds=28800,")
    replace('proc = subprocess.run(command, capture_output=True, text=True, timeout=28800, preexec_fn=limits)',
            'proc = isolated_native(command, receipt, limits)')
    replace('        resource.setrlimit(resource.RLIMIT_CPU, (600,) * 2)\n        meta = json.loads(proc.stdout)',
        "        if (actual['pid'] != actual['pgid'] or actual['pid'] != proc.pid\n                or actual['start_ticks'] != proc.start_ticks or actual['command'] != command\n                or actual['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()\n                or actual['elapsed_limit_seconds'] != 28800 or result['elapsed_seconds'] >= 28800\n                or result['child_cpu_seconds'] > 21600):\n            raise ValueError('owned candidate state/prefix native resource identity differs')\n        result['terminal_identity_verified'] = True\n        resource.setrlimit(resource.RLIMIT_CPU, (600,) * 2)\n        meta = json.loads(proc.stdout)")
    replace("    receipt = json.loads(D.checked(Path(data['resource_receipt'])))", "    if not data['terminal_identity_verified'] or data['numerical_variant'] != 'compensated-raw-target-v1':\n        raise ValueError('candidate terminal identity required')\n    receipt = json.loads(D.checked(Path(data['resource_receipt'])))")
    inverse = source
    for before,after in reversed(edits):inverse = D.once(inverse,after,before)
    if inverse != original:raise ValueError('whole109 source inverse differs')
    trees = [ast.parse(text) for text in (original,source)]
    exact = {}
    for name in ('original_slots','selected_slot'):
        nodes = [next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name == name) for tree in trees]
        exact[name] = ast.dump(nodes[0],include_attributes=False) == ast.dump(nodes[1],include_attributes=False)
    begin,end = '        meta = json.loads(proc.stdout)', '        for path, digest in list(D.INPUTS.items()):'
    blocks = [text[text.index(begin):text.index(end)] for text in (original,source)]
    exact['full_terminal_analysis_bytes'] = blocks[0] == blocks[1]
    exact['full_terminal_analysis_ast'] = ast.dump(ast.parse('def analysis():\n'+blocks[0]),include_attributes=False) == ast.dump(ast.parse('def analysis():\n'+blocks[1]),include_attributes=False)
    if not all(exact.values()):raise ValueError('canonical scope or full terminal physical/prefix analysis differs')
    return source,edits,dict(whole109_source_inverse_exact=True,original_scientific_blocks_exact=exact)


def isolated_native(command,receipt,limits):
    def ticks(pid):
        try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
        except FileNotFoundError:return None
    child = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        start_new_session=True,preexec_fn=limits)
    own = json.loads(receipt.read_text())
    try:stdout,stderr = child.communicate(timeout=28800)
    except subprocess.TimeoutExpired:
        if (own['pid'],own['pgid'],own['start_ticks']) != (child.pid,child.pid,ticks(child.pid)):
            raise ValueError('owned state/prefix native changed; refuse signalling')
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        stdout,stderr = child.communicate(timeout=5)
        raise subprocess.TimeoutExpired(command,28800,output=stdout.encode(),stderr=stderr.encode())
    result = subprocess.CompletedProcess(command,child.returncode,stdout,stderr)
    result.pid = child.pid;result.start_ticks = own['start_ticks']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--describe',action='store_true')
    parser.add_argument('--case-index',type=int,choices=range(26))
    parser.add_argument('--phase',type=int,choices=range(3))
    parser.add_argument('--summarize',action='store_true');args = parser.parse_args()
    if args.describe or args.summarize:
        if args.case_index is not None or args.phase is not None or (args.describe and args.summarize):
            parser.error('description/summary cannot mix with cases/phases')
    elif args.case_index is None or args.phase is None:parser.error('one explicit case/phase required')
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if args.describe:
        if DESCRIPTION.exists():raise ValueError('fresh source/scope description required')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),L.PLAN,Path(L.__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact157/156 recipes/drivers first')
    for module in (C,D,L,L.G):D.checked(Path(module.__file__).resolve())
    D.checked(D.HERE/'run_primary_direction_sequence.py')
    source,edits,proof = program()
    scope = dict(__name__='n010_plan157',__file__=str(Path(__file__).resolve()),
        CANDIDATE_PLAN=PLAN,CANDIDATE_BASE=BASE,CANDIDATE_SUMMARY=SUMMARY,
        candidate_prerequisites=prerequisites,isolated_native=isolated_native,
        source_edits=edits,generated_program=source,composition_proof=proof)
    exec(compile(source,str(Path(__file__).resolve()),'exec'),scope)
    if not args.describe:return scope['main']()
    original,_ = scope['original_slots']()
    rows = []
    for case in range(26):
        slot = scope['selected_slot'](original,case);small,full = (8,16) if case < 24 else (8192,16384)
        for phase in range(3):
            output,work = scope['paths'](case,phase)
            rows.append(dict(case_index=case,phase=phase,cell=slot['cell'],vertices=slot['vertices'],
                spp=small if phase == 1 else full,begin_spp=small if phase == 2 else 0,
                seeds=list(D.SEEDS),output=str(output),work=str(work)))
    if len(rows) != 78 or len({row['output'] for row in rows}) != 78:raise ValueError('full original78 slots required')
    result = dict(schema='n010-compensated-state-prefix-description/1',complete=True,
        source_scope_metadata_valid=True,source_commit=commit,input_sha256=D.INPUTS,proof=proof,
        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),source_edits=edits,
        rows=rows,classification='COMPENSATED_FULL78_STATE_PREFIX_SOURCE_ONLY_NOT_RUN',
        gpu_run=False,native_executed=False,reference_admission=False,accepted_timing=False,
        tests='NOT_RUN; source/AST/inverse/full-scope metadata only')
    with DESCRIPTION.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__ == '__main__':main()
