#!/usr/bin/env python3
"""Plan 047: retain seven complete scenes, acquire ten, apply all original gates."""
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

from primary_direction_recovery_programs import (
    ROOT, HERE, RESULTS, sha, identities, require_paths, physical_program,
)

sys.path.insert(0, str(HERE.parent/'n010_comparison_readiness'))
from qualify_hybrid_references import check_files
from run_primary_direction_sequence import require_no_other_research_worker

RETAINED = ('A10', 'A2', 'A2b', 'A4a', 'A4b', 'A4c', 'A4d')
PARTIAL = RESULTS/'152-primary-direction-physical-controls.json'
STOP = RESULTS/'161-user-requested-directional-workflow-stop.json'
OLD_WORK = ROOT/'out/research/n010-comparison-readiness/primary-direction-physical-v1'


def prepare(inputs):
    frozen = {
        str(PARTIAL): 'a891a103476d2f8ac1e8840275f55b11303d79fec0042ac3d57e173ad67cc0c8',
        str(STOP): '08fb9b7821efebe5075afbb27d41e51e7977a6bd562819eea6747b517c4d22ff',
    }
    check_files(frozen, inputs)
    physical, stop = (json.loads(p.read_text()) for p in (PARTIAL, STOP))
    if (physical['complete'] or physical['all_pass']
        or stop['classification'] != 'USER_STOPPED_PARTIAL_PHYSICAL_CONTROLS_NO_REFERENCE_ADMISSION'
        or not stop['complete'] or stop['restarted'] or stop['thresholds_changed']
        or not stop['source_receipt']['record']['verified_no_remaining_research_workers']):
        raise ValueError('retained operational stop identity differs')
    check_files(physical['input_sha256'], inputs)
    check_files({str(ROOT/r['path']): r['sha256'] for r in stop['preserved_payloads_and_status']}, inputs)
    rows = {r['name']: r for r in physical['rows'] if r.get('pass') is True}
    if tuple(rows) != RETAINED or physical['rows'][-1]['name'] != 'A6a':
        raise ValueError('fixed retained scene set differs')
    expected = {f'{name}.s{i}.{kind}' for name in RETAINED for i in range(4)
                for kind in ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')}
    for name, row in rows.items():
        command = row['command']
        if row['returncode'] or Path(command[command.index('--out')+1]) != OLD_WORK/name:
            raise ValueError('retained native identity differs')
        payloads = row['payload_sha256']
        required = {p for p in expected if p.startswith(name+'.')} | {
            name+'.hits', name+'.stdout', name+'.stderr', name+'.meta.json'}
        if set(payloads) != required:
            raise ValueError('retained four-seed payload scope differs')
        check_files({str(OLD_WORK/p): digest for p, digest in payloads.items()}, inputs)
    return {'rows': rows, 'provenance': {
        'plan': '047', 'partial_sha256': sha(PARTIAL), 'stop_sha256': sha(STOP),
        'fixed_imported_scenes': list(RETAINED), 'new_native_scene_count': 10,
        'old_paths_written': False, 'interrupted_A6a_samples_imported': False,
        'scope': 'All seventeen original scenes and gates; seven exact-byte native export imports, not repeat executions',
    }}


def copy_import(name, row, prospective_command, work):
    actual = row['command']
    expected = list(prospective_command)
    expected[expected.index('--out')+1] = str(OLD_WORK/name)
    if actual != expected:
        raise ValueError('retained binary/scene/seed/spp/thread command differs')
    for payload, digest in row['payload_sha256'].items():
        if sha(OLD_WORK/payload) != digest or (work/payload).exists():
            raise ValueError('retained source changed or import target exists')
        shutil.copyfile(OLD_WORK/payload, work/payload)
        if sha(work/payload) != digest:
            raise ValueError('import byte identity differs')
    return actual


def import_process(work, name, row):
    return SimpleNamespace(returncode=row['returncode'],
        stdout=(work/(name+'.stdout')).read_text(), stderr=(work/(name+'.stderr')).read_text())


if __name__ == '__main__':
    original, source = physical_program()
    exec(compile(source, str(original)+'#plan047-recovery', 'exec'), {
        '__name__': '__main__', '__file__': __file__,
        '_prepare_recovery': prepare, '_copy_import': copy_import,
        '_import_process': import_process, '_program_inputs': identities(__file__, original),
        '_require_quiet': require_no_other_research_worker,
        '_require_paths': require_paths,
    })
