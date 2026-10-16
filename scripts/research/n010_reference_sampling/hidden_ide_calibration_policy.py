"""Plan 052 reversible window policy and sampled accounting, not GPU utilization."""
import datetime
import json
from pathlib import Path
import signal
import subprocess
import threading
import time

import diagnose_ide_visibility_accounting as D

HERE, ROOT, RESULTS = D.HERE, D.ROOT, D.RESULTS
PLAN = RESULTS.parent/'experiments/052-prospective-hidden-ide-full-calibration.md'
REGISTERED = {
    'sizing':('177-hidden-ide-bulk-pfm-calibration-sizing.json', 'hidden-ide-bulk-pfm-sizing-v1'),
    'accepted':('178-hidden-ide-bulk-pfm-calibration-full-renderer.json', 'hidden-ide-bulk-pfm-accepted-v1')}
DIAGNOSTIC_SHA = 'c8c8a7a00662344f48de9a6f266ac976f789b9594d3e6bc336a3dacb1aa7ef8b'
HELPER_SHA = 'b405236c259648552d90ab1b4f0978d25961e7cafb5e8e33eb1265d00791fe7f'
STOP_SHA = 'cd0287f7fb5c2c4947ad42ec833c68f9b3f892518085fee11bb54520744fbbd4'


class VisibilityPolicy:
    def __init__(self):
        self.stop = threading.Event()
        self.thread = None
        self.original = self.focus = self.original_monitors = None
        self.movement_attempted = False
        self.failure = None
        self.previous = None
        self.count = 0
        self.lock = threading.Lock()
        self.handlers = {}
        self.record = {'schema':'n010-hidden-ide-calibration-policy/1',
            'complete':False, 'all_pass':False, 'restoration_verified':False,
            'snapshot_count':0, 'maximum_accounted_gfx_ns_per_elapsed_second':1000000,
            'requested_observer_interval_seconds':5, 'ipc_commands':[],
            'application_stopped':False, 'power_settings_changed':False,
            'limitations':'Sampled per-client cumulative accounting only; not physical GPU utilization, global quiescence, exact query overlap or proof of causation.'}

    def prerequisites(self, inputs):
        paths = [Path(__file__).resolve(), HERE/'hidden_ide_bulk_pfm_program.py',
                 HERE/'calibrate_hidden_ide_bulk_pfm.py', Path(D.__file__).resolve(), PLAN,
                 RESULTS/'174-ide-visibility-accounting-diagnostic.json',
                 RESULTS/'176-user-requested-post-stop-feasibility-stop.json']
        D.require(D.sha(Path(D.__file__))==HELPER_SHA, 'frozen diagnostic helper changed')
        D.require(D.sha(paths[-2])==DIAGNOSTIC_SHA and D.sha(paths[-1])==STOP_SHA,
                  'registered diagnostic or stop evidence changed')
        diagnostic, stopped = (json.loads(p.read_text()) for p in paths[-2:])
        prior_calibration = RESULTS/'169-bulk-pfm-calibration-full-renderer.json'
        build = RESULTS/'167-bulk-pfm-calibration-fixture-build.json'
        D.require(D.sha(prior_calibration)=='dddca3bfa7d2f0847e683352593519165829963d49fd173a29b698ba825d6add'
            and D.sha(build)=='71b94470b465f0d16afaec9bec60b42e63c39e6be8ed781f6d5b1802ca99b88a',
            'immutable prior full calibration or exact fixture build changed')
        paths.extend((prior_calibration,build))
        D.require(diagnostic['complete'] and diagnostic['all_pass'] and diagnostic['restoration_verified'],
                  'complete local suppression/restoration PASS required')
        raw = stopped['source_receipt']
        receipt = ROOT/raw['path']
        D.require(D.sha(receipt)==raw['sha256'] and json.loads(receipt.read_text())==raw['record'],
                  'exact user-stop receipt changed')
        D.require(raw['record']['all_targets_exited'] and all(
            not s['remaining_research_processes'] for s in raw['record']['post_stop_research_process_scans']),
            'actual user-stop completion absent')
        paths.append(receipt)
        for f in raw['record']['preserved_files']:
            p = ROOT/f['path']
            D.require(p.stat().st_size==f['size'] and D.sha(p)==f['sha256'], 'stopped partial changed')
            paths.append(p)
        for p in paths:
            inputs[str(p)] = D.sha(p)

    def bind(self, result, args, inputs, proof):
        expected_result, expected_work = REGISTERED[args.mode]
        D.require(args.output.resolve()==RESULTS/expected_result and
                  args.work.resolve()==ROOT/'out/research/n010-comparison-readiness'/expected_work,
                  'plan-052 registered fresh paths required')
        D.require(not args.work.exists() and not args.output.exists(), 'refuse existing acquisition')
        self.result, self.args, self.inputs = result, args, inputs
        self.sidecar = args.work/'visibility-policy.json'
        self.snapshots = args.work/'visibility-snapshots.jsonl'
        self.result['plan052_source_inverse_proof'] = proof
        self.result['visibility_policy'] = self.record
        self.result['visibility_policy_path'] = str(self.sidecar.resolve())
        self.result['visibility_snapshots_path'] = str(self.snapshots.resolve())

    def save(self):
        self.sidecar.write_text(json.dumps(self.record, indent=2, ensure_ascii=False)+'\n')

    def dispatch(self, name, argument):
        command = ['hyprctl','dispatch',name,argument]
        row = {'command':command, 'started_monotonic_ns':time.monotonic_ns()}
        self.record['ipc_commands'].append(row)
        self.save()
        proc = subprocess.run(command, capture_output=True, text=True, timeout=5)
        row.update(returncode=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
        self.save()
        D.require(proc.returncode==0 and proc.stdout.strip()=='ok', 'visibility dispatcher failed')

    def snapshot(self):
        # Serialize the background observer and synchronous native-boundary observations.
        with self.lock:
            value = D.counter()
            value['window'] = D.selected(self.original['address'])
            value['monitors'] = D.monitors()
            window = value['window']
            state_pass = (value['monitors']==self.original_monitors and
                window['workspace']['name']==D.SPECIAL and all(window[k]==self.original[k] for k in (
                    'pid','class','mapped','floating','fullscreen','fullscreenClient','pinned','grouped')))
            value['sampled_visibility_identity_pass'] = state_pass
            if self.previous:
                elapsed = value['scan_start_monotonic_ns']-self.previous['scan_start_monotonic_ns']
                delta = value['engine_ns']['gfx']-self.previous['engine_ns']['gfx']
                value['elapsed_ns'] = elapsed
                value['gfx_delta_ns'] = delta
            with self.snapshots.open('a') as f:
                f.write(json.dumps(value, ensure_ascii=False)+'\n')
            self.count += 1
            self.record['snapshot_count'] = self.count
            self.save()
            D.require(state_pass, 'sampled visibility, layout or identity changed')
            if self.previous:
                self.interval(self.previous,value)
            self.previous = value
            return value

    @staticmethod
    def interval(before, after):
        elapsed = after['scan_start_monotonic_ns']-before['scan_start_monotonic_ns']
        delta = after['engine_ns']['gfx']-before['engine_ns']['gfx']
        D.require(elapsed>0 and delta>=0 and delta*1000000000<=1000000*elapsed,
                  'registered hidden graphics-accounting interval failed')

    def observe(self):
        try:
            before = self.observer_previous
            while not self.stop.wait(5):
                after = self.snapshot()
                self.interval(before, after)
                before = after
                self.observer_previous = after
        except BaseException as error:
            self.failure = str(error)
            self.record['observer_failure'] = str(error)
            self.save()

    def check(self):
        D.require(self.failure is None, 'visibility observer failed: '+str(self.failure))
        self.snapshot()

    def wrap_execute(self, execute):
        def guarded(*args, **kwargs):
            from run_primary_direction_sequence import require_no_other_research_worker
            require_no_other_research_worker()
            self.check()
            evidence = execute(*args, **kwargs)
            require_no_other_research_worker()
            self.check()
            return evidence
        return guarded

    def restore(self):
        if not self.movement_attempted:
            self.record['restoration_required'] = False
            self.record['restoration_verified'] = True
            return
        self.record['restoration_required'] = True
        current = D.selected(self.original['address'])
        if current['workspace']!=self.original['workspace']:
            self.dispatch('movetoworkspacesilent', str(self.original['workspace']['id'])+',address:'+self.original['address'])
        if self.focus:
            D.process(self.focus['pid'], self.focus['start_ticks'])
            self.dispatch('focuswindow', 'address:'+self.focus['address'])
        time.sleep(2)
        D.require(D.selected(self.original['address'])==self.original and
                  D.monitors()==self.original_monitors, 'original layout not exactly restored')
        if self.focus:
            D.require(D.ipc_json('activewindow').get('address')==self.focus['address'], 'original focus not restored')
        self.record['restoration_verified'] = True

    def __enter__(self):
        from run_primary_direction_sequence import require_no_other_research_worker
        require_no_other_research_worker()
        self.args.work.mkdir(parents=True)
        self.save()
        def interrupted(signum, frame):
            raise InterruptedError('handled termination signal '+str(signum))
        for sig in (signal.SIGINT,signal.SIGTERM):
            self.handlers[sig] = signal.signal(sig, interrupted)
        try:
            version = D.ipc_json('version')
            D.require(version['commit']==D.VERSION, 'registered compositor implementation changed')
            self.record['desktop_version'] = version
            clients = D.windows()
            matches = [w for w in clients if w['pid']==D.PARENT_PID and w['class']=='orca' and w['mapped']]
            D.require(len(matches)==1, 'registered IDE window missing or ambiguous')
            D.counter()
            self.original = matches[0]
            D.require(not any(self.original[k] for k in (
                'hidden','floating','fullscreen','fullscreenClient','pinned','grouped')) and
                self.original['workspace']['id']>0, 'window outside registered scope')
            self.original_monitors = D.monitors()
            D.require(self.original['workspace']['id'] in {
                m['activeWorkspace']['id'] for m in self.original_monitors}, 'original workspace not displayed')
            D.require(not any(w['workspace']['name']==D.SPECIAL for w in clients) and
                not any(m['specialWorkspace']['name']==D.SPECIAL for m in self.original_monitors) and
                not any(w['name']==D.SPECIAL for w in D.ipc_json('workspaces')), 'special workspace already in use')
            active = D.ipc_json('activewindow')
            if active.get('address'):
                stat = (Path('/proc')/str(active['pid'])/'stat').read_text().rsplit(')',1)[1].split()
                self.focus = {'address':active['address'],'pid':active['pid'],'start_ticks':int(stat[19])}
            self.record.update(original_window=self.original, original_monitors=self.original_monitors,
                original_focus=self.focus, started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            self.movement_attempted = True
            self.dispatch('movetoworkspacesilent', D.SPECIAL+',address:'+self.original['address'])
            time.sleep(2)
            before = self.snapshot()
            for _ in range(3):
                time.sleep(5)
                after = self.snapshot()
                self.interval(before,after)
                before = after
            self.record['pre_gpu_hidden_intervals_pass'] = True
            self.observer_previous = before
            self.thread = threading.Thread(target=self.observe, name='visibility-accounting', daemon=True)
            self.thread.start()
            self.save()
            return self
        except BaseException as error:
            self.__exit__(type(error),error,error.__traceback__)
            raise

    def __exit__(self, kind, error, traceback):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=20)
            if self.thread.is_alive():
                self.failure = 'observer failed to terminate'
        if error:
            self.record['acquisition_failure'] = str(error)
        try:
            if self.thread and not self.thread.is_alive() and not self.failure:
                self.check()
                final = self.snapshot()
                self.interval(self.observer_previous,final)
        except BaseException as failure:
            self.failure = str(failure)
            self.record['observer_failure'] = str(failure)
        try:
            self.restore()
        except BaseException as failure:
            self.record['restoration_failure'] = str(failure)
            self.record['restoration_verified'] = False
        try:
            D.require(all(D.sha(Path(p))==h for p,h in self.inputs.items()), 'frozen input changed')
            self.record['input_identities_unchanged'] = True
        except BaseException as failure:
            self.record['input_failure'] = str(failure)
        self.record['all_pass'] = (error is None and self.failure is None and
            self.record.get('pre_gpu_hidden_intervals_pass',False) and
            self.record.get('restoration_verified',False) and
            self.record.get('input_identities_unchanged',False))
        self.record['complete'] = True
        self.result['numerical_all_pass'] = self.result['all_pass']
        self.result['all_pass'] = self.result['all_pass'] and self.record['all_pass']
        passed = ('COMPLETE_FULL_SIZING_PASS_NO_TIMING_ADMISSION' if self.args.mode=='sizing'
                  else 'COMPLETE_FULL_CALIBRATION_PASS')
        self.result['classification'] = (passed if self.result['complete'] and self.result['all_pass']
            else 'COMPLETE_ORIGINAL_SCIENTIFIC_GATES_FAIL' if self.result['complete'] and self.record['all_pass']
            else 'OPERATIONAL_GUARD_FAILED_PARTIALS_RETAINED_NOT_ACCEPTED')
        self.save()
        self.result['visibility_policy_sha256'] = D.sha(self.sidecar)
        if self.snapshots.exists():
            self.result['visibility_snapshots_sha256'] = D.sha(self.snapshots)
        self.args.output.write_text(json.dumps(self.result,indent=2,ensure_ascii=False)+'\n')
        for sig, handler in self.handlers.items():
            signal.signal(sig,handler)
        if error is None:
            D.require(self.record['all_pass'], 'environment/restoration policy failed; acquisition not accepted')
        return False
