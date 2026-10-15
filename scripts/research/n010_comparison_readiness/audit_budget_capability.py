#!/usr/bin/env python3
"""Assemble guarded programs and observe the new ceiling in a fresh CPU child."""
import argparse
import builtins
import json
import os
from pathlib import Path
import resource
import subprocess
import sys

import budget_reference_provenance as B
import qualify_budget_references as qualification
import finish_budget_readiness as finish
import readiness_preflight_budget as preflight
import retire_budget_redundant_hybrid as retirement
from reference_provenance import ROOT, sha
from qualify_hybrid_references import check_files
from retire_point_guided_at_boundary import NEW_SOURCES, PLAN


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing operational witness')
    args.work.mkdir(parents=True)
    inputs = {str(path.resolve()): sha(path) for path in
        (PLAN, *(Path(__file__).with_name(name) for name in NEW_SOURCES))}
    result = {'schema': 'n010-operational-budget-capability-and-program-assembly/1',
        'complete': False, 'all_pass': False, 'gpu_run': False,
        'native_acquisition_run': False, 'eligible_for_references': False,
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'classification': 'OFFLINE_OPERATIONAL_CAPABILITY_AND_SOURCE_ASSEMBLY_ONLY',
        'inputs': inputs, 'programs': [],
        'scope': 'Fresh Python CPU limit witness and exact guarded program construction; no sampler invocation, acquisition, runtime regression validation or readiness'}
    try:
        for name, module, nested in [('qualification', qualification, False), ('comparison', finish, True),
                                     ('preflight', preflight, True), ('retirement', retirement, False)]:
            original, source = module.program()
            inputs[str(original)] = sha(original)
            path = args.work/(name+'-adapter.py.txt')
            path.write_text(source)
            compile(source, str(path), 'exec')
            inputs[str(path.resolve())] = sha(path)
            item = {'name': name, 'guarded_source': str(original), 'adapter_program': str(path.resolve()),
                'adapter_compiles': True}
            if nested:
                captured = []
                def capture_compile(text, filename, mode):
                    captured.append((text, filename))
                    return builtins.compile(text, filename, mode)
                old_argv = sys.argv
                try:
                    sys.argv = ['operational-assembly', '--help']
                    builtins.exec(builtins.compile(source, str(path), 'exec'), {
                        '__name__': '__main__', '__file__': module.__file__,
                        'compile': capture_compile, 'exec': lambda *arguments: None})
                finally:
                    sys.argv = old_argv
                if len(captured) != 1:
                    raise ValueError('expected exactly one constructed final program')
                text, filename = captured[0]
                final = args.work/(name+'-final.py.txt')
                final.write_text(text)
                code = compile(text, filename, 'exec')
                if 'budget_reference_provenance' not in code.co_names:
                    raise ValueError('final program lacks budget-aware provenance')
                inputs[str(final.resolve())] = sha(final)
                item.update(final_program=str(final.resolve()), final_compiles=True,
                            final_program_not_executed=True)
            result['programs'].append(item)
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (B.AS_BYTES, B.AS_BYTES))
            resource.setrlimit(resource.RLIMIT_CPU, (B.CPU_SECONDS, B.CPU_SECONDS))
        code = ('import json,os,resource; print(json.dumps({"uid":os.getuid(),'
                '"cpu_seconds":list(resource.getrlimit(resource.RLIMIT_CPU)),'
                '"address_space_bytes":list(resource.getrlimit(resource.RLIMIT_AS))}))')
        command = [sys.executable, '-c', code]
        child = subprocess.run(command, text=True, capture_output=True, preexec_fn=limits, timeout=30)
        for name, data in [('child.stdout.json', child.stdout), ('child.stderr.log', child.stderr)]:
            path = args.work/name
            path.write_text(data)
            inputs[str(path.resolve())] = sha(path)
        observed = json.loads(child.stdout)
        if (child.returncode != 0 or observed['uid'] != os.getuid()
                or observed['cpu_seconds'] != [B.CPU_SECONDS, B.CPU_SECONDS]
                or observed['address_space_bytes'] != [B.AS_BYTES, B.AS_BYTES]):
            raise ValueError('fresh unprivileged child did not establish declared resource bounds')
        result['actual_fresh_child'] = {'command': command, 'returncode': child.returncode, 'observed': observed,
            'role': 'Python resource capability witness; no renderer or reference computation'}
        check_files(inputs, {})
        result['all_pass'] = True
    except (ValueError, OSError, KeyError, AssertionError, SyntaxError, subprocess.SubprocessError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'all_pass': result['all_pass'], 'failure': result.get('failure'),
        'programs': result['programs'], 'actual_child': result.get('actual_fresh_child')}))
    raise SystemExit(0 if result['all_pass'] else 2)
