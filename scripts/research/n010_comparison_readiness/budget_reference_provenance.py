"""Unchanged sampling proofs plus explicit completed-prefix/resource receipts."""
import json
import os
from pathlib import Path
import resource

import point_guided_replayed_provenance as base
from point_guided_replayed_provenance import BINARY, KEYS, SELECTED, VARIANT
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

PLAN = RESULTS.parent/'experiments/039-operational-cpu-budget-continuation.md'
TRANSITION = RESULTS/'138-operational-cpu-budget-boundary-transition.json'
CAPABILITY = RESULTS/'141-operational-budget-capability-and-program-assembly.json'
WORK = ROOT/'out/research/n010-comparison-readiness/point-guided-replayed-reference-ladders-v1'
CPU_SECONDS = 691200
AS_BYTES = 4*1024**3


def transition(inputs):
    capability = read(CAPABILITY, inputs)
    if not capability.get('complete') or not capability.get('all_pass'):
        raise ValueError('actual operational capability/program assembly proof required')
    check_files(capability['inputs'], inputs)
    value = read(TRANSITION, inputs)
    if not value.get('complete') or not value.get('all_pass') or value.get('failure'):
        raise ValueError('completed operational boundary PASS required')
    if value['work'] != str(WORK) or not value['original_processes_terminal']:
        raise ValueError('operational boundary/root identity differs')
    check_files(value['input_sha256'], inputs)
    return value


def prerequisites(inputs):
    proofs = base.prerequisites(inputs)
    for path in (Path(__file__), PLAN):
        inputs[str(path.resolve())] = sha(path)
    transition(inputs)
    return proofs


def imported(inputs):
    value = transition(inputs)
    rows = {}
    for row in value['imported_prefixes']:
        raw = read(Path(row['archive']), inputs)
        if sha(Path(row['archive'])) != row['sha256']:
            raise ValueError('imported qualification archive differs')
        rows[row['name']] = raw
    return rows


def set_limits(prefix, spp, previous):
    """Called in a fresh subprocess immediately before exec; no running-process change."""
    resource.setrlimit(resource.RLIMIT_AS, (AS_BYTES, AS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    pid = os.getpid()
    stat = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
    qualifier = Path(__file__).with_name('qualify_budget_references.py')
    value = {'schema': 'n010-native-operational-resource-receipt/1', 'pid': pid,
        'start_ticks': stat[19], 'ppid': os.getppid(), 'uid': os.getuid(),
        'spp': spp, 'sample_interval': [previous['spp'] if previous else 0, spp],
        'cpu_seconds': list(resource.getrlimit(resource.RLIMIT_CPU)),
        'address_space_bytes': list(resource.getrlimit(resource.RLIMIT_AS)),
        'elapsed_guard_seconds': 43200, 'threads': 16,
        'policy_sha256': sha(PLAN), 'implementation_sha256': sha(Path(__file__)),
        'qualifier_sha256': sha(qualifier)}
    target = prefix.parent/f'n{spp}.resource-limits.json'
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        data = (json.dumps(value, indent=2)+'\n').encode()
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
    except BaseException:
        raise


def verify_reference(directory, cell, vertices, spec, inputs, require_eligible=True):
    directory = directory.resolve()
    result = base.verify_reference(directory, cell, vertices, spec, inputs, require_eligible)
    q = read(directory/'qualification.json', inputs)
    if q.get('computational_variant') != VARIANT:
        return result
    if directory != WORK/f'{cell}_T_B{vertices}':
        raise ValueError('budget continuation changed the selected reference root')
    boundary = transition(inputs)
    old = imported(inputs).get(f'{cell}_T_B{vertices}')
    old_levels = old['levels'] if old else []
    if q['levels'][:len(old_levels)] != old_levels:
        raise ValueError('imported complete levels changed')
    for level in q['levels'][len(old_levels):]:
        spp = level['spp']
        path = directory/f'n{spp}.resource-limits.json'
        receipt = read(path, inputs)
        meta = read(directory/f'n{spp}.meta.json', inputs)
        attempt = read(directory/f'n{spp}.attempt.json', inputs)
        if (receipt['cpu_seconds'] != [CPU_SECONDS, CPU_SECONDS]
                or receipt['address_space_bytes'] != [AS_BYTES, AS_BYTES]
                or receipt['spp'] != spp or receipt['sample_interval'] != meta['sample_interval']
                or receipt['elapsed_guard_seconds'] != 43200 or receipt['threads'] != 16
                or receipt['policy_sha256'] != sha(PLAN)
                or receipt['implementation_sha256'] != sha(Path(__file__))
                or receipt['qualifier_sha256'] != sha(Path(__file__).with_name('qualify_budget_references.py'))
                or not isinstance(receipt['pid'], int) or receipt['pid'] <= 0
                or receipt['uid'] != boundary['original_processes'][0]['uid']
                or not isinstance(receipt['ppid'], int) or receipt['ppid'] <= 0
                or not receipt['start_ticks'].isdigit()
                or meta['resource_limits_sha256'] != sha(path)
                or attempt['resource_limits_sha256'] != sha(path)):
            raise ValueError('actual operational resource receipt differs')
    result['operational_provenance'] = {'transition_sha256': sha(TRANSITION),
        'imported_levels': [level['spp'] for level in old_levels],
        'new_levels_with_resource_receipts': [level['spp'] for level in q['levels'][len(old_levels):]]}
    check_files(inputs, {})
    return result
