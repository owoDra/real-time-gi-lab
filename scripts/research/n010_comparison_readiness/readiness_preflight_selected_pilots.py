#!/usr/bin/env python3
"""Plan154: complete selected-pilot timing validity with unchanged five gates."""
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

import selected_reportable_pilot_provenance as T
from selected_reportable_pilot_provenance import C, P, R
from build_raw_query_pilots import quiet

PLAN = R.RESULTS.parent/'experiments/154-full-selected-pilot-readiness-adapter.md'
ORIGINAL = Path(__file__).with_name('readiness_preflight.py')
ORIGINAL_SHA = '87985c62edd7ad9a7a8e931e0f36264d939a4e4774507fe0653ac9d483857e2c'
DESCRIPTION = R.RESULTS/'523-full-selected-pilot-adapter-description.json'
OUTPUT = R.RESULTS/'524-full-selected-pilot-readiness-audit.json'
WORK = R.BASE/'selected-pilot-readiness-v1'
GATES = ('refs','correctness','dynamic','static','provenance')


def program():
    original = R.checked(ORIGINAL,ORIGINAL_SHA).decode()
    source, edits = original,[]
    def change(before, after):
        nonlocal source
        C.require(source.count(before) == 1 and after not in source, 'nonunique154 source overlay')
        source = source.replace(before,after,1);edits.append((before,after))
    change('from reference_provenance import physical_proof,verify_reference',
        'from reference_provenance import physical_proof\nfrom hybrid_reference_provenance import verify_reference')
    change("ap.add_argument('--calibration',type=Path,required=True)",
        "ap.add_argument('--timing-scope',dest='calibration',type=Path,required=True)")
    change('a=ap.parse_args()\n','a=ap.parse_args()\n _require_output(a.output)\n')
    begin = source.index(' def calibration():\n')
    end = source.index(" gate('demonstrated_full_renderer_timing_capability',calibration)",begin)
    change(source[begin:end],''' def calibration():
  if a.calibration.resolve()!=_timing_scope:
   raise ValueError('exact503 full selected timing scope required')
  return _verify_selected(a.lock,a.references,result['inputs'])
''')
    change(" gate('demonstrated_full_renderer_timing_capability',calibration)",
        " gate('valid_complete_selected_timing_quality_memory_pilots',calibration)")
    change("'schema':'n010-readiness-preflight/1'","'schema':'n010-full-selected-pilot-readiness/1'")
    change(" a.output.write_text(json.dumps(result,indent=2)+'\\n');print(result['classification'])",
        " _finish(result)\n print(result['classification'])")
    def bodies(text):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text))
            if isinstance(n,ast.FunctionDef) and n.name in GATES}
    C.require(bodies(source) == bodies(original) and set(bodies(source)) == set(GATES),
        'five original non-timing gate ASTs changed')
    restored = source
    for before,after in reversed(edits):
        C.require(restored.count(after) == 1, 'nonunique154 source inverse')
        restored = restored.replace(after,before,1)
    C.require(restored == original, 'whole original source inverse differs')
    ast.parse(source)
    return source,dict(whole_source_inverse_exact=True,other_five_gate_asts_identical=True,
        original_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(source.encode()).hexdigest(),
        selected_full36_timing_route_implemented=True,all_split_reference_dispatch_implemented=False,
        scope='Known original/exact-prefix/hybrid references only; unknown variants fail closed')


def main():
    parser = argparse.ArgumentParser(description=__doc__,add_help=False)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--describe',action='store_true');mode.add_argument('--audit',action='store_true')
    args, forwarded = parser.parse_known_args()
    C.require(not args.describe or not forwarded, 'description takes no gate arguments')
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:os.nice(15-priority)
    C.require(all(os.environ.get(k) == '1' for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')),
        'one numerical thread required')
    resource.setrlimit(resource.RLIMIT_CPU,((120,120) if args.describe else (1200,1200)))
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
    signal.alarm(180 if args.describe else 1800)
    if not args.describe:quiet()
    destination = DESCRIPTION if args.describe else OUTPUT
    C.require(not destination.exists(), 'fresh registered audit/description required; no overwrite')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (PLAN,Path(__file__).resolve(),Path(T.__file__).resolve()):
        C.require(subprocess.check_output(['git','show',commit+':'+str(path.relative_to(R.ROOT))]) == R.checked(path),
            'commit exact154 source/registration before use')
    source, composition = program()
    inventory = T.inventory()
    if args.describe:
        result = dict(schema='n010-full-selected-pilot-adapter-description/1',complete=True,
            classification='FULL_36_TIMING_ADAPTER_SOURCE_AND_SCOPE_ONLY',source_commit=commit,
            source_composition=composition,inventory=inventory,input_sha256=R.INPUTS,
            native_executed=False,raw_evidence_replayed=False,quality_scoring_executed=False,
            accepted_timing=False,final_handoff_admitted=False,
            tests='NOT_RUN; source inverse/five gate AST/scope metadata only')
        R.unchanged()
        with destination.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(result['classification']);return 0
    def output_guard(path):
        C.require(path.resolve() == OUTPUT and not OUTPUT.exists(), 'actual154 audit requires fresh524')
    def verify(lock, refs, inputs):return T.verify(lock,refs,WORK,inputs)
    def finish(result):
        result.update(complete=True,gpu_run=False,posthoc=True,accepted_timing=False,
            source_composition=composition,declared_pilot_inventory=inventory,
            input_sha256=R.INPUTS,
            payload_sha256={str(p):P.sha(p) for p in WORK.rglob('*') if p.is_file()},
            tests='NOT_RUN; scientific full evidence/provenance/quality readiness audit only')
        # Original gate reads use their separate input map; preserve both maps.
        for name,digest in list(result['inputs'].items()):R.checked(name,digest)
        R.unchanged()
        with OUTPUT.open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    previous = sys.argv
    sys.argv = [str(ORIGINAL),*forwarded]
    scope = dict(__name__='__main__',__file__=str(ORIGINAL),_require_output=output_guard,
        _timing_scope=T.SCOPE,_verify_selected=verify,_finish=finish)
    try:
        exec(compile(source,str(ORIGINAL)+'#plan154','exec'),scope)
    finally:sys.argv = previous


if __name__ == '__main__':main()
