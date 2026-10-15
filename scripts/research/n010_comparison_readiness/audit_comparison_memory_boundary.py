#!/usr/bin/env python3
"""Post-hoc CPU-only linked-source coverage and retained owned-memory audit."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from reference_provenance import ROOT, RESULTS, read, sha
from readiness_preflight import replay

BUILD = ROOT/'build/n009'
TARGETS = ('phos-n010-capture', 'phos-n010-pixel-pt')
ALLOC = re.compile(r'(?:\.\s*allocateMemory|\bvkAllocateMemory)\s*\(')
FREE = re.compile(r'(?:\.\s*freeMemory|\bvkFreeMemory)\s*\(')
HOOKS = {'n010_b002_vulkan.cpp', 'n010_vk_context.cpp'}
PILOTS = ('013-c7-pt-cohort-pilot.json', '019-controlled-dynamic-cohort.json',
          '024-c8-pt-quality-ladder.json', '025-c9-pt-quality-ladder.json',
          '031-c1-b2-pt-quality-ladder.json', '037-controlled-dynamic-pt1024.json')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse retained memory-boundary audit overwrite')
    a.work.mkdir(parents=True)
    inputs = {}
    for path in (Path(__file__), Path(__file__).with_name('readiness_preflight.py'),
                 BUILD/'build.ninja', ROOT/'src/research/n010_comparison_readiness/CMakeLists.txt',
                 ROOT/'src/research/n010_comparison_readiness/allocation_ledger.hpp',
                 Path(__file__).with_name('generate_memory_hooks.py')):
        inputs[str(path.resolve())] = sha(path)
    driver = read(ROOT/'out/research/n010-comparison-readiness/continuation-replayed-point-guided-v1/status.json', {})
    result = {'schema': 'n010-comparison-owned-memory-boundary-audit/1',
        'complete': False, 'all_pass': False, 'gpu_run': False, 'build_run': False,
        'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'classification': 'POST_HOC_LINKED_SOURCE_AND_RETAINED_LEDGER_AUDIT_ONLY',
        'scope': 'Application-owned Vulkan allocations in the two frozen comparison executables; no new runtime/calibration/whole-corpus claim',
        'limitations': 'Direct call-site and compiled project dependency audit, not a formal proof of arbitrary dynamically loaded code; driver-private, OS and CPU heap allocations are outside the declared owned-Vulkan scope',
        'inputs': inputs, 'linked_targets': [], 'pilot_rows': [], 'unsupported_rows': [],
        'scoring_exclusions': 0}
    try:
        ninja = (BUILD/'build.ninja').read_text()
        rules = {line.split(': ',1)[0][6:]: line.split(': ',1)[1]
                 for line in ninja.splitlines() if line.startswith('build ') and ': ' in line}
        for target in TARGETS:
            binary = BUILD/target
            expected = driver['input_sha256'][str(binary)]
            if sha(binary) != expected:
                raise ValueError('comparison binary differs from frozen driver')
            inputs[str(binary)] = expected
            link = rules[target]
            objects = [p for p in link.split(' |',1)[0].split()[1:] if p.endswith('.o')]
            required = HOOKS if target.endswith('capture') else {'n010_b002_vulkan.cpp'}
            sources, project_dependencies, object_records = set(), set(), []
            if not objects:
                raise ValueError('empty linked object closure')
            for obj in objects:
                rule = rules[obj]
                if not rule.startswith('CXX_COMPILER__'):
                    raise ValueError('unexpected object compiler rule')
                source = Path(rule.split()[1])
                if not source.is_absolute():
                    source = BUILD/source
                source = source.resolve()
                sources.add(source)
                command = ['ninja','-C',str(BUILD),'-t','deps',obj]
                proc = subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
                raw = a.work/(target+'-'+str(len(object_records))+'.deps.txt')
                raw.write_text(proc.stdout)
                inputs[str(raw.resolve())] = sha(raw)
                if proc.returncode or 'VALID' not in proc.stdout.splitlines()[0]:
                    raise ValueError('compiled dependency information unavailable/stale')
                for name in proc.stdout.splitlines()[1:]:
                    if not name.startswith('    '):
                        continue
                    dep = Path(name.strip())
                    if not dep.is_absolute():
                        dep = BUILD/dep
                    dep = dep.resolve()
                    if dep.is_relative_to(ROOT/'src') or dep.is_relative_to(BUILD/'src'):
                        project_dependencies.add(dep)
                inputs[str((BUILD/obj).resolve())] = sha(BUILD/obj)
                object_records.append({'object':obj,'source':str(source),'dependency_command':command,
                    'dependency_stdout_sha256':sha(raw)})
            project_dependencies |= sources
            sites = []
            for path in sorted(project_dependencies):
                inputs[str(path)] = sha(path)
                text = path.read_text()
                alloc, free = len(ALLOC.findall(text)), len(FREE.findall(text))
                if not alloc and not free:
                    continue
                if path not in sources or path.name not in required or (alloc,free) != (1,1):
                    raise ValueError('unexpected allocation/free call in linked project closure: '+str(path))
                if (text.count('AllocationLedger::instance().allocate(') != 1
                        or text.count('AllocationLedger::instance().release(') != 1):
                    raise ValueError('allocation/free hook coverage differs')
                sites.append({'source':str(path),'allocation_calls':alloc,'free_calls':free,
                              'allocate_hooks':1,'release_hooks':1,'pass':True})
            if {Path(s['source']).name for s in sites} != required:
                raise ValueError('required context allocation hooks absent from actual link')
            if any(Path(p).name in ('b002_vulkan.cpp','vk_context.cpp') for p in sources):
                raise ValueError('uninstrumented legacy context is linked')
            result['linked_targets'].append({'target':target,'binary_sha256':expected,
                'objects':object_records,'project_dependency_count':len(project_dependencies),
                'allocation_sites':sites,'external_link_inputs':link.split(' |',1)[1],
                'stale_unlinked_object_files_not_treated_as_active':True,'pass':True})
        for name in PILOTS:
            pilot = read(RESULTS/name,inputs)
            if not pilot['complete']:
                raise ValueError('partial retained pilot')
            for i,row in enumerate(pilot['rows']):
                identity = {'source_result':name,'row_index':i,'cell':row.get('cell',pilot.get('cell')),
                            'role':row.get('role','pixel-pt'), 'spp':row.get('spp')}
                if row.get('classification') == 'UNSUPPORTED_IN_CAPTURE_API':
                    result['unsupported_rows'].append({**identity,'classification':row['classification']})
                    continue
                command = row['command']
                directory = Path(command[command.index('--out')+1])
                if not directory.is_absolute():
                    directory = ROOT/directory
                ledger_path = directory/'allocation-ledger.json'
                raw = read(ledger_path,inputs)
                stored = row.get('memory',row.get('allocation_ledger'))
                if raw != stored or row['returncode'] or not replay(raw):
                    raise ValueError('retained ledger/return code/lifetime/peak gate failed')
                binary = next((BUILD/t for t in TARGETS if str(BUILD/t) in command),None)
                if binary is None or row['binary_sha256'] != sha(binary):
                    raise ValueError('retained pilot differs from frozen comparison executable')
                result['pilot_rows'].append({**identity,'binary_sha256':row['binary_sha256'],
                    'ledger_sha256':sha(ledger_path),'event_count':len(raw['events']),
                    'device_contexts':sorted({e['device_context'] for e in raw['events']}),
                    'true_peak_owned_bytes':raw['true_peak_owned_bytes'],'teardown_zero':True,'pass':True})
        if len(result['pilot_rows']) != 76 or len(result['unsupported_rows']) != 1:
            raise ValueError('declared retained pilot coverage differs')
        changed = [p for p,h in inputs.items() if sha(Path(p)) != h]
        if changed:
            raise ValueError('audit input changed: '+str(changed))
        result['all_pass'] = True
        result['inputs_unchanged_after_audit'] = True
    except (ValueError,OSError,KeyError,AssertionError,IndexError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'all_pass':result['all_pass'],'failure':result.get('failure'),
        'linked_targets':len(result['linked_targets']),'retained_pilot_rows':len(result['pilot_rows']),
        'unsupported_rows':len(result['unsupported_rows']),'input_count':len(inputs)}))
    raise SystemExit(0 if result['all_pass'] else 2)
