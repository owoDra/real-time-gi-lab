#!/usr/bin/env python3
"""Plan 051: one reversible A/B/A desktop-visibility accounting diagnostic."""
import argparse
import datetime
import hashlib
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
PLAN = RESULTS.parent/'experiments/051-prospective-ide-visibility-accounting-diagnostic.md'
WORK = ROOT/'out/research/n010-comparison-readiness/ide-visibility-diagnostic-v1'
OUTPUT = RESULTS/'174-ide-visibility-accounting-diagnostic.json'
SPECIAL = 'special:n010-calibration-isolation'
GPU_PID, GPU_START, PARENT_PID, PARENT_START = 516315, 8673949, 516230, 8673902
CLIENT = ('amdgpu', '0000:c5:00.0', '2946')
VERSION = '39d7e209c79d451efab1b21151d5938289da838d'
WINDOW_KEYS = ('address', 'pid', 'class', 'mapped', 'hidden', 'workspace', 'monitor',
               'at', 'size', 'floating', 'fullscreen', 'fullscreenClient', 'pinned', 'grouped')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def process(pid, start):
    stat = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')', 1)[1].split()
    require(int(stat[19])==start and stat[0]!='Z', 'process launch identity changed')
    return {'pid':pid, 'start_ticks':int(stat[19]), 'ppid':int(stat[1])}


def ipc_json(kind):
    return json.loads(subprocess.check_output(['hyprctl', '-j', kind], text=True, timeout=5))


def windows():
    return [{k:w.get(k) for k in WINDOW_KEYS} for w in ipc_json('clients')]


def monitors():
    return sorted(({'id':m['id'], 'activeWorkspace':m['activeWorkspace'],
                    'specialWorkspace':m['specialWorkspace']} for m in ipc_json('monitors')),
                  key=lambda m:m['id'])


def selected(address):
    matches = [w for w in windows() if w['address']==address and w['pid']==PARENT_PID]
    require(len(matches)==1, 'original window identity is no longer unique')
    return matches[0]


def counter():
    process(PARENT_PID, PARENT_START)
    require(process(GPU_PID, GPU_START)['ppid']==PARENT_PID, 'GPU parent changed')
    start = time.monotonic_ns()
    for fd in sorted((Path('/proc')/str(GPU_PID)/'fdinfo').iterdir(), key=lambda p:int(p.name)):
        try:
            fields = dict(line.split(':', 1) for line in fd.read_text().splitlines() if ':' in line)
        except OSError:
            continue
        if tuple(fields.get(k, '').strip() for k in ('drm-driver', 'drm-pdev', 'drm-client-id'))!=CLIENT:
            continue
        engines = {}
        for k, value in fields.items():
            if k.startswith('drm-engine-') and value.strip().endswith(' ns'):
                engines[k.removeprefix('drm-engine-')] = int(value.split()[0])
        require('gfx' in engines, 'registered client has no graphics counter')
        return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scan_start_monotonic_ns':start, 'scan_end_monotonic_ns':time.monotonic_ns(),
                'client':CLIENT, 'pid':GPU_PID, 'start_ticks':GPU_START,
                'first_matching_fd':int(fd.name), 'engine_ns':engines}
    raise ValueError('registered DRM client disappeared')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.work.resolve()==WORK and args.output.resolve()==OUTPUT, 'registered paths required')
    require(not WORK.exists() and not OUTPUT.exists(), 'refuse existing diagnostic; no retry')
    sys.path.insert(0, str(HERE))
    from run_primary_direction_sequence import require_no_other_research_worker
    require_no_other_research_worker()
    calibration_path = RESULTS/'169-bulk-pfm-calibration-full-renderer.json'
    sizing_path = RESULTS/'168-bulk-pfm-calibration-quiet-sizing.json'
    lock_path = RESULTS/'026-dynamic-execution-state-lock.json'
    calibration = json.loads(calibration_path.read_text())
    expected = [f'{cell}-{role}' for cell in ('C1', 'C7', 'C6', 'C12')
                for role in (('hwrt', 'pt-B2', 'pt-B8') if cell in ('C6', 'C12')
                             else ('hwrt', 'software', 'pt-B2', 'pt-B8', 'dense-rc'))]
    require(calibration['schema']=='n010-bulk-pfm-renderer-calibration/1'
            and calibration['mode']=='accepted' and calibration['lock_sha256']==sha(lock_path)
            and calibration['plan_sha256']==sha(sizing_path)
            and calibration['complete'] and [r['boundary']['id'] for r in calibration['rows']]==expected
            and all(len(r['blocks'])==8 and 'analysis' in r for r in calibration['rows'])
            and all(b['returncode']==0 and len(b['samples'])==64
                    for r in calibration['rows'] for b in r['blocks']),
            'complete actual sixteen-boundary calibration required; FAILs remain FAIL')
    diagnosis = RESULTS/'173-posthoc-concurrent-drm-client-diagnosis.json'
    require(sha(diagnosis)=='ca43cfb2b6b7391ebdeffff28eb4f5177cc9c81a5814e6fa301faff2d4ab4470',
            'immutable observation 173 changed')
    old = json.loads(diagnosis.read_text())
    raw = ROOT/old['source_observation']['path']
    require(sha(raw)==old['source_observation']['sha256'], 'retained raw observation changed')
    inputs = {str(p):sha(p) for p in (Path(__file__).resolve(), PLAN, diagnosis, raw,
              calibration_path, sizing_path, lock_path,
              HERE/'run_primary_direction_sequence.py')}
    WORK.mkdir(parents=True)
    result = {'schema':'n010-ide-visibility-accounting-diagnostic/1', 'complete':False,
        'all_pass':False, 'gpu_run':False, 'renderer_gpu_work_submitted':False,
        'desktop_visibility_intervention':False, 'classification':'PREREQUISITES_UNCHECKED',
        'source_commit':subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'input_sha256':inputs, 'phases':[], 'ipc_commands':[],
        'power_settings_changed':False, 'application_stopped':False,
        'calibration_modified':False, 'original_timing_gates_changed':False,
        'accepted_timing':False, 'reference_admission':False,
        'thresholds':{'minimum_each_visible_accounted_ns_per_second':10000000,
                      'maximum_hidden_accounted_ns_per_second':1000000,
                      'maximum_hidden_to_smaller_visible_rate':0.05},
        'direct_max_relative_error_1_0':'UNRESOLVED / 未解決; included',
        'tests':'NOT_RUN; operational diagnostic, no Renderer regression claim'}
    original, initial_focus, initial_monitors, movement_attempted = None, None, None, False

    def save():
        OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')

    def dispatch(name, argument):
        command = ['hyprctl', 'dispatch', name, argument]
        row = {'command':command, 'started_monotonic_ns':time.monotonic_ns()}
        result['ipc_commands'].append(row)
        save()
        proc = subprocess.run(command, capture_output=True, text=True, timeout=5)
        row.update(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
        save()
        require(proc.returncode==0 and proc.stdout.strip()=='ok', 'desktop dispatcher failed')

    def restore():
        if not movement_attempted:
            result['restoration_required'] = False
            return
        result['restoration_required'] = True
        current = selected(original['address'])
        if current['workspace']!=original['workspace']:
            dispatch('movetoworkspacesilent', str(original['workspace']['id'])+',address:'+original['address'])
        if initial_focus:
            process(initial_focus['pid'], initial_focus['start_ticks'])
            dispatch('focuswindow', 'address:'+initial_focus['address'])
        # Allow the compositor's workspace animation to finish before comparing
        # exact window geometry; this delay is outside every accounting phase.
        time.sleep(2)
        current = selected(original['address'])
        require(current==original and monitors()==initial_monitors, 'original window/layout not fully restored')
        if initial_focus:
            require(ipc_json('activewindow').get('address')==initial_focus['address'], 'original focus not restored')
        result['restoration_verified'] = True
        save()

    def phase(name, workspace):
        time.sleep(2)
        row = {'name':name, 'snapshots':[], 'intervals':[]}
        result['phases'].append(row)
        save()
        for index in range(4):
            if index:
                time.sleep(5)
            require_no_other_research_worker()
            window = selected(original['address'])
            require(monitors()==initial_monitors and window['workspace']['name']==workspace,
                    'phase visibility or displayed workspaces changed')
            require(all(window[k]==original[k] for k in (
                'pid', 'class', 'mapped', 'floating', 'fullscreen', 'fullscreenClient', 'pinned', 'grouped')),
                'window mapping or layout state changed during diagnostic')
            value = counter()
            value['window'] = window
            row['snapshots'].append(value)
            save()
        for before, after in zip(row['snapshots'], row['snapshots'][1:]):
            elapsed = after['scan_start_monotonic_ns']-before['scan_start_monotonic_ns']
            delta = after['engine_ns']['gfx']-before['engine_ns']['gfx']
            require(elapsed>0 and delta>=0, 'invalid cumulative accounting interval')
            row['intervals'].append({'elapsed_ns':elapsed, 'graphics_accounted_ns_delta':delta})
        row['accounted_ns_per_elapsed_second'] = (
            sum(r['graphics_accounted_ns_delta'] for r in row['intervals'])*1e9
            /sum(r['elapsed_ns'] for r in row['intervals']))
        row['complete'] = True
        save()
        print(name, 'complete', flush=True)

    def interrupted(signum, frame):
        raise InterruptedError('handled termination signal '+str(signum))

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, interrupted)
    save()
    try:
        version = ipc_json('version')
        require(version['commit']==VERSION, 'unregistered compositor implementation')
        result['desktop_version'] = version
        require(process(GPU_PID, GPU_START)['ppid']==PARENT_PID, 'GPU parent mismatch')
        result['process_identities'] = {'gpu':process(GPU_PID, GPU_START),
                                       'ide_parent':process(PARENT_PID, PARENT_START)}
        clients = windows()
        matches = [w for w in clients if w['pid']==PARENT_PID and w['class']=='orca' and w['mapped']]
        require(len(matches)==1, 'registered IDE window is missing or ambiguous')
        original = matches[0]
        require(not any(original[k] for k in ('hidden', 'floating', 'fullscreen', 'fullscreenClient', 'pinned', 'grouped'))
                and original['workspace']['id']>0, 'window is outside registered intervention scope')
        initial_monitors = monitors()
        require(original['workspace']['id'] in {m['activeWorkspace']['id'] for m in initial_monitors},
                'original window must be on a displayed workspace')
        require(not any(w['workspace']['name']==SPECIAL for w in clients)
                and not any(m['specialWorkspace']['name']==SPECIAL for m in initial_monitors)
                and not any(w['name']==SPECIAL for w in ipc_json('workspaces')),
                'registered special workspace is already in use')
        result['registered_special_workspace_absent'] = True
        active = ipc_json('activewindow')
        if active.get('address'):
            stat = (Path('/proc')/str(active['pid'])/'stat').read_text().rsplit(')', 1)[1].split()
            initial_focus = {'address':active['address'], 'pid':active['pid'], 'start_ticks':int(stat[19])}
        result.update(original_window=original, original_monitors=initial_monitors,
                      original_focus=initial_focus, classification='ACQUIRING_OPERATIONAL_DIAGNOSTIC')
        save()
        phase('visible-before', original['workspace']['name'])
        movement_attempted = True
        result['desktop_visibility_intervention'] = True
        dispatch('movetoworkspacesilent', SPECIAL+',address:'+original['address'])
        phase('hidden', SPECIAL)
        restore()
        phase('visible-after', original['workspace']['name'])
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        result['failure'] = str(error)
    finally:
        try:
            restore()
        except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
            result['restoration_failure'] = str(error)
            result['restoration_verified'] = False
        try:
            require(all(sha(Path(p))==h for p,h in inputs.items()), 'frozen diagnostic input changed')
            result['input_identities_unchanged'] = True
        except (ValueError, OSError) as error:
            result['failure'] = str(error)
        if len(result['phases'])==3 and all(p.get('complete') for p in result['phases']):
            a, b, c = (p['accounted_ns_per_elapsed_second'] for p in result['phases'])
            result['local_suppression_gates'] = {
                'both_visible_rates_sufficient':min(a,c)>=10000000,
                'hidden_rate_below_absolute_cutoff':b<=1000000,
                'hidden_rate_below_relative_cutoff':b<=0.05*min(a,c)}
            result['all_pass'] = (all(result['local_suppression_gates'].values())
                and result.get('restoration_verified', False) and result.get('input_identities_unchanged', False)
                and not result.get('failure') and not result.get('restoration_failure'))
        result.update(complete=True, classification=(
            'LOCAL_GRAPHICS_ACCOUNTING_SUPPRESSION_ONLY_NO_TIMING_ADMISSION' if result['all_pass']
            else 'REGISTERED_SUPPRESSION_NOT_ESTABLISHED_PARTIALS_RETAINED_NO_RETRY'))
        result['limitations'] = ('Per-client cumulative accounting, not instantaneous utilization, '
            'per-query overlap or causal proof for earlier failures. No calibration or reference gate is passed.')
        save()
    return 0 if result['all_pass'] else 2


if __name__=='__main__':
    raise SystemExit(main())
