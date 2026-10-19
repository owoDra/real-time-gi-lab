#!/usr/bin/env python3
"""Plan168: one prospective full-C1 four-core execution-equivalence pilot."""
import argparse
import ast
import hashlib
import os
from pathlib import Path
import subprocess

import diagnose_selected_bounce_paths as D

PLAN = D.RESULTS.parent/'experiments/168-bounded-four-core-execution-pilot.md'
ORIGINAL = D.HERE/'acquire_thread_private_equivalence.py'
ORIGINAL_SHA = '7967029b0ed5450fc9abc6743b1d211391183fbfa8a636393f447434e3caf038'
OUTPUT = D.RESULTS/'720-four-core-full-c1-equivalence.json'
WORK = D.OUT/'four-core-full-c1-equivalence-v1'


def program():
    original = D.checked(ORIGINAL,ORIGINAL_SHA).decode();source = original;edits = []
    def change(before,after):
        nonlocal source
        source = D.once(source,before,after);edits.append((before,after))
    change("PLAN = D.RESULTS.parent/'experiments/163-thread-private-full-frame-equivalence-pilot.md'",'PLAN = _pilot_plan')
    change('def paths(step):return D.RESULTS/f\'{623 if step == "baseline" else 624}-thread-private-{step}-equivalence.json\',BASE/step',
        "def paths(step):\n    if step == 'baseline':return D.RESULTS/'623-thread-private-baseline-equivalence.json',BASE/'baseline'\n    return _pilot_output,_pilot_work")
    change('args = parser.parse_args()',"args = parser.parse_args(['--step','candidate'])")
    change('os.sched_setaffinity(0,{31})','os.sched_setaffinity(0,{28,29,30,31})')
    change("current = bind(D.RESULTS/'490-compensated-full-a6a-seed1.json')",
           "current = bind(D.RESULTS/'493-compensated-full-a6b-seed0.json')")
    change('threads=threads,actual_affinity=[31]',
        "threads=threads,actual_affinity=[28,29,30,31],execution_profile='four-core-low-priority-v1',\n"
        '        source_composition_proof=_pilot_composition')
    change("or own['affinity'] != [31]","or own['affinity'] != [28,29,30,31]")
    change("classification='FULL_C1_SINGLE_CORE_EXECUTION_EQUIVALENCE_STEP_PASS'",
        "classification='FULL_C1_FOUR_CORE_EXECUTION_EQUIVALENCE_STEP_PASS'")
    anchor = "            result['native_pid'] = child.pid;save()\n"
    observation = '''            # Read only the owned native's threads; no host acceptance gate.
            snapshots=[]
            for _ in range(250):
                if child.poll() is not None:break
                try:
                    tasks=sorted(Path(f'/proc/{child.pid}/task').iterdir(),key=lambda p:int(p.name))
                    snapshots=[]
                    for task in tasks:
                        status=task.joinpath('status').read_text()
                        fields=task.joinpath('stat').read_text().rsplit(')',1)[1].split()
                        snapshots.append(dict(tid=int(task.name),nice=int(fields[16]),
                            cpu_seconds=(int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK'),
                            allowed_cpu_list=status.split('Cpus_allowed_list:')[1].splitlines()[0].strip()))
                    if len(tasks)>=5:break
                except (FileNotFoundError,ProcessLookupError,PermissionError):pass
                time.sleep(.02)
            result['owned_os_thread_snapshot_diagnostic']=snapshots;save()
'''
    change(anchor,anchor+observation)
    inverse = source
    for before,after in reversed(edits):inverse = D.once(inverse,after,before)
    if inverse != original:raise ValueError('whole163 four-core source inverse differs')
    begin = "        meta = json.loads((work/'native.stdout').read_text());run = meta['runs'][0]"
    end = '        for name,digest in list(D.INPUTS.items()):D.checked(Path(name),digest)'
    blocks = [text[text.index(begin):text.index(end,text.index(begin))] for text in (original,source)]
    if blocks[0] != blocks[1]:raise ValueError('original full scientific terminal analysis differs')
    scientific_ast_exact = ast.dump(ast.parse('def analysis():\n'+blocks[0]),include_attributes=False) == ast.dump(ast.parse('def analysis():\n'+blocks[1]),include_attributes=False)
    if not scientific_ast_exact:raise ValueError('original analysis AST differs')
    ast.parse(source)
    return source,dict(original_sha256=ORIGINAL_SHA,whole163_source_inverse_exact=True,
        full_scientific_terminal_analysis_bytes_exact=True,full_scientific_terminal_analysis_ast_exact=True,
        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),source_edits=edits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true',required=True);parser.parse_args()
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),ORIGINAL,
                 D.RESULTS/'493-compensated-full-a6b-seed0.json',
                 D.RESULTS/'717-private-estimator-identity-and-physical-evidence-transfer.md'):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact pilot source/recipe and retained evidence before native')
    if not {28,29,30,31}.issubset(os.sched_getaffinity(0)):
        raise ValueError('four original owned-process CPU targets unavailable')
    core_ids=[(Path(f'/sys/devices/system/cpu/cpu{i}/topology/physical_package_id').read_text().strip(),
               Path(f'/sys/devices/system/cpu/cpu{i}/topology/core_id').read_text().strip()) for i in (28,29,30,31)]
    if len(set(core_ids)) != 4:raise ValueError('four distinct physical cores required')
    source,proof = program()
    scope = dict(__name__='n010_plan168',__file__=str(Path(__file__).resolve()),_pilot_plan=PLAN,
        _pilot_output=OUTPUT,_pilot_work=WORK,_pilot_composition=proof)
    exec(compile(source,str(ORIGINAL)+'#plan168','exec'),scope)
    return scope['main']()


if __name__ == '__main__':raise SystemExit(main())
