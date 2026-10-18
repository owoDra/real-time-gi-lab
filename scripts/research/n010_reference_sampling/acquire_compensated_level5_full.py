#!/usr/bin/env python3
"""Plan156: exact105 diagnostic analysis with452, one explicit native only."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess

import cover_wide8_original_controls as C
import diagnose_selected_bounce_paths as D
import acquire_compensated_full_sphere_seed as G

PLAN = D.RESULTS.parent/'experiments/156-compensated-full-level5-diagnostic.md'
ORIGINAL = D.HERE/'acquire_original_level5_wide8.py'
ORIGINAL_SHA = '9e29c2e6ee4f7facf42cc7b81ace44d593db8465191b57ad2ef52eb2f78f76e5'
DESCRIPTION = D.RESULTS/'528-compensated-full-level5-description.json'
OUTPUT = D.RESULTS/'529-compensated-full-level5-diagnostic.json'
WORK = D.OUT/'compensated-level5-full-v1'


def bind(path):
    proof = json.loads(D.checked(path))
    if not proof['complete']:raise ValueError('complete pinned prerequisite required: '+str(path))
    for group in ('input_sha256','payload_sha256'):
        for name,digest in proof.get(group,{}).items():D.checked(Path(name),digest)
    return proof


def prerequisites():
    build = bind(D.RESULTS/'452-compensated-full-exporter-build.json')
    if not build['build_valid'] or not build['terminal_identity_verified']:
        raise ValueError('terminal452 candidate build required')
    for n in (*range(473,482),483,484,486,487):
        paths = list(D.RESULTS.glob(str(n)+'-*.json'))
        if len(paths) != 1:raise ValueError('unique candidate control required')
        proof = bind(paths[0])
        flag = 'control_pass' if n <= 481 else 'all_pass'
        if not proof[flag] or proof['numerical_variant'] != 'compensated-raw-target-v1':
            raise ValueError('candidate full physical prerequisite failed')
    for name in G.NAMES:
        parts = [G.retained_part(name,i) for i in range(4)]
        for part in parts:
            for path,digest in part['input_sha256'].items():D.checked(Path(path),digest)
        if not parts[-1]['full_four_seed_physical_pass']:
            raise ValueError('full candidate four-seed physical PASS required')
        if name == 'A6b' and not parts[-1]['independent_iid']['pass_']:
            raise ValueError('candidate independent A6b IID PASS required')
    return build


def program():
    original = D.checked(ORIGINAL,ORIGINAL_SHA).decode()
    source = original;edits = []
    def replace(before,after):
        nonlocal source
        source = D.once(source,before,after);edits.append((before,after))
    replace("WORK = D.OUT / 'wide8-original-level5-full-v1'",'WORK = CANDIDATE_WORK')
    replace("OUTPUT = D.RESULTS / '258-wide8-original-level5-full-artifact.json'",'OUTPUT = CANDIDATE_OUTPUT')
    replace("PLAN = D.RESULTS.parent / 'experiments/105-original-full-level5-artifact.md'",'PLAN = CANDIDATE_PLAN')
    replace('    os.nice(15)', '    priority = os.getpriority(os.PRIO_PROCESS,0)\n    if priority < 15:os.nice(15-priority)')
    replace("    prototype = C.pinned_result('254')", "    candidate = candidate_prerequisites()\n    prototype = C.pinned_result('254')")
    replace("    binary = D.OUT / 'wide8-cpu-bvh-v1/n010_wide8_exporter'\n    D.checked(binary, prototype['payload_sha256'][str(binary)])",
        "    binary = D.OUT / 'compensated-full-deterministic-v1/build/n010_compensated_exporter'\n    D.checked(binary, candidate['payload_sha256'][str(binary)])")
    replace("schema='n010-wide8-original-full-level5-artifact/1'", "schema='n010-compensated-full-level5-artifact/1',\n                  numerical_variant='compensated-raw-target-v1', resource_receipt=str(receipt),\n                  source_composition_proof=composition_proof")
    replace("    WORK.mkdir()", "    WORK.mkdir()\n    (WORK/'source-edits.json').write_text(json.dumps(source_edits,indent=2)+'\\n')\n    (WORK/'generated-driver.py').write_text(generated_program)")
    replace("receipt.write_text(json.dumps(dict(pid=os.getpid(),", "receipt.write_text(json.dumps(dict(pid=os.getpid(), pgid=os.getpgrp(),\n            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),elapsed_limit_seconds=1800,")
    replace("proc = subprocess.run(command, capture_output=True, text=True, timeout=1800, preexec_fn=limits)",
        "proc = isolated_native(command, receipt, limits)")
    # Metadata labels only; preserve the complete terminal numerical-analysis block.
    for before,after in (
        ("classification='ORIGINAL_FULL_LEVEL5_NATIVE_ACQUIRING'", "classification='COMPENSATED_FULL_LEVEL5_NATIVE_ACQUIRING'"),
        ("classification='ORIGINAL_FULL_LEVEL5_NATIVE_TERMINAL_ANALYSIS_PENDING'", "classification='COMPENSATED_FULL_LEVEL5_NATIVE_TERMINAL_ANALYSIS_PENDING'"),
        ("classification='ORIGINAL_FULL_LEVEL5_FAILURE_PARTIALS_RETAINED'", "classification='COMPENSATED_FULL_LEVEL5_FAILURE_PARTIALS_RETAINED'"),
        ("classification='ORIGINAL_FULL_LEVEL5_DIAGNOSTIC_COMPLETE_NO_ADMISSION'", "classification='COMPENSATED_FULL_LEVEL5_DIAGNOSTIC_COMPLETE_NO_ADMISSION'"),
        ("scope='One original full256 diagnostic artifact; no A6b analytic/IID gate or reference admission'", "scope='One candidate full256 diagnostic artifact; no A6b analytic/IID gate or reference admission'"),
    ):replace(before,after)
    replace("        if proc.returncode:\n", "        if (actual['pid'] != actual['pgid'] or actual['pid'] != proc.pid\n                or actual['start_ticks'] != proc.start_ticks or actual['affinity'] != [31]\n                or actual['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip()\n                or actual['elapsed_limit_seconds'] != 1800 or actual['command'] != command\n                or result['elapsed_seconds'] >= 1800 or result['child_cpu_seconds'] > 1200):\n            raise ValueError('owned candidate native terminal/resource identity differs')\n        result['terminal_identity_verified'] = True\n        if proc.returncode:\n")
    # Only this post-analysis metadata differs; the analysis itself stays exact.
    replace("                      original_full_artifacts_retained=14,", "                      original_full_artifacts_retained=14, candidate_full_artifacts_retained=17,")
    inverse = source
    for before,after in reversed(edits):inverse = D.once(inverse,after,before)
    if inverse != original:raise ValueError('whole105 source inverse differs')
    start,end = '        fresh = json.loads(proc.stdout)', '        result.update(complete=True, all_pass=True,'
    old_analysis = original[original.index(start):original.index(end)]
    new_analysis = source[source.index(start):source.index(end)]
    if old_analysis != new_analysis:raise ValueError('original terminal physical analysis bytes differ')
    trees = [ast.parse(text) for text in (original,source)]
    diagnostics = [[ast.dump(node.value,include_attributes=False) for node in ast.walk(tree)
                    if isinstance(node,ast.keyword) and node.arg == 'analytic_diagnostic']
                   for tree in trees]
    if len(diagnostics[0]) != 1 or diagnostics[0] != diagnostics[1]:
        raise ValueError('original NOT_GATED analytic diagnostic computation differs')
    return source,edits,dict(whole105_source_inverse_exact=True,
        not_gated_analytic_diagnostic_expression_ast_exact=True,
        terminal_physical_analysis_bytes_exact=True,terminal_physical_analysis_ast_exact=
        ast.dump(ast.parse('def analysis():\n'+old_analysis),include_attributes=False) ==
        ast.dump(ast.parse('def analysis():\n'+new_analysis),include_attributes=False))


def isolated_native(command,receipt,limits):
    def ticks(pid):
        try:return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
        except FileNotFoundError:return None
    child = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
        start_new_session=True,preexec_fn=limits)
    own = json.loads(receipt.read_text())
    try:stdout,stderr = child.communicate(timeout=1800)
    except subprocess.TimeoutExpired:
        if (own['pid'],own['pgid'],own['start_ticks']) != (child.pid,child.pid,ticks(child.pid)):
            raise ValueError('owned native identity changed; refuse signalling')
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        stdout,stderr = child.communicate(timeout=5)
        raise subprocess.TimeoutExpired(command,1800,output=stdout.encode(),stderr=stderr.encode())
    result = subprocess.CompletedProcess(command,child.returncode,stdout,stderr)
    result.pid = child.pid;result.start_ticks = own['start_ticks']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--describe',action='store_true');group.add_argument('--acquire',action='store_true')
    args = parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    if args.describe:
        if DESCRIPTION.exists():raise ValueError('fresh source description required; no overwrite')
        resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
        signal.alarm(180)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve()):
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(D.ROOT))]) != D.checked(path):
            raise ValueError('commit exact156 source/recipe first')
    for module in (C,D,G):D.checked(Path(module.__file__).resolve())
    D.checked(D.HERE/'run_primary_direction_sequence.py')
    source,edits,proof = program()
    if args.describe:
        result = dict(schema='n010-compensated-full-level5-description/1',complete=True,
            source_metadata_valid=True,source_commit=commit,input_sha256=D.INPUTS,proof=proof,
            generated_source_sha256=hashlib.sha256(source.encode()).hexdigest(),source_edits=edits,
            classification='COMPENSATED_LEVEL5_SOURCE_ONLY_NATIVE_NOT_RUN',gpu_run=False,
            native_executed=False,reference_admission=False,accepted_timing=False,
            original_analysis_is_diagnostic_not_gated=True,tests='NOT_RUN; source/AST/inverse metadata only')
        with DESCRIPTION.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(result['classification']);return
    if OUTPUT.exists() or WORK.exists():raise ValueError('fresh scientific output required; no retry')
    scope = dict(__name__='n010_plan156',__file__=str(Path(__file__).resolve()),
        CANDIDATE_WORK=WORK,CANDIDATE_OUTPUT=OUTPUT,CANDIDATE_PLAN=PLAN,
        candidate_prerequisites=prerequisites,isolated_native=isolated_native,source_edits=edits,
        composition_proof=proof,generated_program=source)
    exec(compile(source,str(Path(__file__).resolve()),'exec'),scope)
    return scope['main']()


if __name__ == '__main__':main()
