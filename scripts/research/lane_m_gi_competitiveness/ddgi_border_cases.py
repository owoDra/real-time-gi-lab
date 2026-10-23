"""011 exact qualification inventory and native CPU contracts. No GPU launcher."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess

import ddgi_control_step as S
import ddgi_dynamic_inputs as D

R = S.R
BASE = S.BUILD.parent
BUILD = BASE / 'm001-ddgi-border-host-build-v1'
SHADERS = BASE / 'm001-ddgi-border-shaders-v2'
CPU = BASE / 'm001-ddgi-border-native-cpu-v1'
WORK = BASE / 'm001-ddgi-border-controls-v1'
PROTOCOL = R.ROOT / 'research/lanes/lane-m-gi-competitiveness/experiments/011-ddgi-separated-border-requalification.md'
SOURCE = R.LANE / 'capture/M001-H01-hwrt'


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    depth: int
    side: int = 4
    rays: int = 128
    mode: str = 'scene'
    kind: str = ''
    transition: bool = False

    @property
    def state(self):
        return D.WORK / self.kind if self.kind and not self.transition else SOURCE

    @property
    def work(self):
        return WORK / self.name

    @property
    def plan(self):
        return R.ROOT / f'out/m001-ddgi-border-{self.name}-plan.json'

    @property
    def archive(self):
        return R.ROOT / f'out/m001-ddgi-border-{self.name}.tar'


CASES = (
    Case('static-direct', 'static', 1, mode='direct'),
    Case('static-black', 'static', 2, mode='constant0'),
    Case('static-unit', 'static', 2, mode='constant1'),
    Case('static-hdr', 'static', 2, mode='constant8'),
    Case('static-scene-one', 'static', 2), Case('static-scene-seven', 'static', 8),
) + tuple(Case(f'dynamic-{kind}-{mode}-b{depth}', 'dynamic', depth, kind=kind, transition=mode == 'transition')
          for kind in ('light', 'geometry') for mode in ('fresh', 'transition') for depth in (2, 8)) + tuple(
    Case(f'integrity-h01-q{rung}-b{depth}', 'integrity', depth, side=side, rays=rays)
    for rung, (side, rays) in enumerate(((8, 128), (16, 256), (24, 512))) for depth in (2, 8))


def get_case(name):
    found = [c for c in CASES if c.name == name]
    if len(found) != 1:
        raise ValueError('Unregistered011 qualification case')
    return found[0]


def expected_schedule(kind, depth):
    if kind not in ('light', 'geometry') or depth not in (2, 8):
        raise ValueError('Unregistered011 transition schedule')
    n = 1224 if kind == 'geometry' else 0
    return [dict(index=k, state_index=s, moved_primitives=m, reset_both_atlases=True, finite_stages=depth - 1)
            for k, (s, m) in enumerate(zip((0, 1, 1, 0), (0, n, 0, n)))]


def command(case, output=None, cpu=False):
    if get_case(case.name) != case:
        raise ValueError('Modified011 case')
    cmd = ['bash', str(R.ROOT / 'scripts/run_with_vulkan.sh'), str(BUILD / 'm001-ddgi-border-transition'),
           '--state', str(case.state), '--out', str(output or case.work / 'capture'), '--sdk-shaders', str(SHADERS),
           '--reduction-shaders', str(S.REDUCTION), '--adapter-shaders', str(S.ADAPTER), '--grid-side', str(case.side),
           '--rays', str(case.rays), '--vertices', str(case.depth), '--mode', case.mode]
    if case.transition:
        cmd += ['--target-state', str(D.WORK / case.kind), '--history-policy', 'reset-all']
    return cmd + (['--cpu-check'] if cpu else [])


def cpu_contract(case):
    """One actual new native CPU contract; thereafter rehash without rerun."""
    from audit_quality_step import validate_inventory
    root = CPU / case.name
    cmd = command(case, root / 'capture', cpu=True)
    paths = [BUILD / 'm001-ddgi-border-transition', Path(__file__).resolve(), case.state / 'geometry-state.bin', case.state / 'frame-state.bin']
    if case.transition:
        paths += [D.WORK / case.kind / 'geometry-state.bin', D.WORK / case.kind / 'frame-state.bin']
    inputs = {str(p): R.sha(p) for p in paths}
    if root.exists():
        report = R.read(root / 'result.json')
        R.require(report['all_pass'] and report['command'] == cmd and report['input_sha256'] == inputs, 'Existing failed/drifted CPU contract; no retry')
        validate_inventory(root, report['payload_sha256'])
        return report
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip()
    R.require(subprocess.check_output(['git', 'show', commit + ':' + str(Path(__file__).resolve().relative_to(R.ROOT))], cwd=R.ROOT) == Path(__file__).read_bytes(), 'Commit011 cases before native CPU contracts')
    root.mkdir(parents=True)
    R.write_new(root / 'started.json', dict(command=cmd, input_sha256=inputs, source_commit=commit, gpu_executed=False))
    env = dict(os.environ, VK_DRIVER_FILES='/nonexistent/m001-no-icd.json', VK_ICD_FILENAMES='/nonexistent/m001-no-icd.json')
    report = dict(command=cmd, input_sha256=inputs, source_commit=commit, gpu_executed=False, unusable_icd=True, all_pass=False)
    try:
        p = subprocess.run(cmd, cwd=R.ROOT, env=env, capture_output=True, text=True, timeout=30)
        (root / 'stdout.txt').write_text(p.stdout)
        (root / 'stderr.txt').write_text(p.stderr)
        report['returncode'] = p.returncode
        if p.returncode == 0:
            if case.transition:
                contract = R.read(root / 'capture/transition-contract.json')
                schedule = expected_schedule(case.kind, case.depth)
                report['all_pass'] = contract == dict(schema='m001-ddgi-reset-schedule/1', history_policy='reset-all', cpu_checked=True, frames=schedule)
            else:
                contract = R.read(root / 'capture/cpu-contract.json')
                report['all_pass'] = contract == dict(gpu_initialized=False, stage_count=case.depth - 1,
                    tile_count_per_stage=case.side**3 * case.rays // 4096, total_rays_per_stage=case.side**3 * case.rays,
                    frame_bytes=128, triangle_stride=64, push_bytes=16)
            report['contract'] = contract
    except subprocess.TimeoutExpired as error:
        report['error'] = str(error)
        for kind, raw in [('stdout', error.stdout), ('stderr', error.stderr)]:
            (root / (kind + '.txt')).write_bytes(raw if isinstance(raw, bytes) else (raw or '').encode())
    report['payload_sha256'] = {str(p.relative_to(root)): R.sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
    R.write_new(root / 'result.json', report)
    R.require(report['all_pass'], '011 native CPU contract failed; retain, no retry')
    return report
