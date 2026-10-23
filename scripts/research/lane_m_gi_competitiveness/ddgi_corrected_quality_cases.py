"""012 immutable corrected-quality inputs and CPU contracts; no GPU launcher.

H01 reuses the matching actual011 native contracts. H02/H03 execute their new
CPU-only branch once with an unusable ICD. Neither permits quality acquisition
before the separately recorded twenty-control requalification gate.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess

import ddgi_border_cases as B
from audit_quality_step import validate_inventory

R = B.R
ROOT = B.BASE / 'm001-ddgi-border-quality-v1'
CPU = B.BASE / 'm001-ddgi-border-quality-cpu-v1'
PROTOCOL = R.ROOT / 'research/lanes/lane-m-gi-competitiveness/experiments/012-ddgi-corrected-quality-continuation.md'
TARGETS = tuple((cell, depth) for cell in ('H01', 'H02', 'H03') for depth in (2, 8))
BUDGETS = ((8, 128), (16, 256), (24, 512))


@dataclass(frozen=True)
class Case:
    cell: str
    depth: int
    rung: int

    def __post_init__(self):
        R.require((self.cell, self.depth) in TARGETS and type(self.depth) is int
                  and type(self.rung) is int and 0 <= self.rung < 3, 'Unregistered012 case')

    @property
    def name(self):
        return f'{self.cell.lower()}-b{self.depth}-q{self.rung}'

    @property
    def budget(self):
        return BUDGETS[self.rung]

    @property
    def state(self):
        return R.LANE / f'capture/M001-{self.cell}-hwrt'

    @property
    def scope(self):
        side, rays = self.budget
        return dict(cell=self.cell, vertices=self.depth, rung=self.rung, grid_side=side, rays=rays)

    @property
    def work(self):
        return ROOT / self.name

    @property
    def plan(self):
        return R.ROOT / f'out/m001-ddgi-border-quality-{self.name}-plan.json'

    @property
    def archive(self):
        return R.ROOT / f'out/m001-ddgi-border-quality-{self.name}.tar'


def command(case, output=None, cpu=False):
    side, rays = case.budget
    cmd = ['bash', str(R.ROOT / 'scripts/run_with_vulkan.sh'), str(B.BUILD / 'm001-ddgi-border-transition'),
           '--state', str(case.state), '--out', str(output or case.work / 'capture'),
           '--sdk-shaders', str(B.SHADERS), '--reduction-shaders', str(B.S.REDUCTION),
           '--adapter-shaders', str(B.S.ADAPTER), '--grid-side', str(side), '--rays', str(rays),
           '--vertices', str(case.depth), '--mode', 'scene']
    return cmd + (['--cpu-check'] if cpu else [])


def expected_contract(case):
    side, rays = case.budget
    return dict(gpu_initialized=False, stage_count=case.depth - 1,
                tile_count_per_stage=side**3 * rays // 4096, total_rays_per_stage=side**3 * rays,
                frame_bytes=128, triangle_stride=64, push_bytes=16)


def cpu_contract(case):
    """Reuse six exact H01 contracts; run twelve different-state CPU checks once."""
    if case.cell == 'H01':
        original = B.get_case(f'integrity-h01-q{case.rung}-b{case.depth}')
        # This routine only rehashes the already completed011contract; never rerun.
        receipt = B.CPU / original.name / 'result.json'
        R.require(receipt.is_file(), 'Existing matching011 H01 CPU receipt required')
        report = B.cpu_contract(original)
        output = B.CPU / original.name / 'capture'
        R.require(report['command'] == command(case, output, cpu=True)
                  and report['contract'] == expected_contract(case), '012 H01 full native contract identity differs')
        return dict(path=str(receipt), sha256=R.sha(receipt), contract=report['contract'],
                    reused_011=True, gpu_executed=False)

    root = CPU / case.name
    cmd = command(case, root / 'capture', cpu=True)
    paths = [B.BUILD / 'm001-ddgi-border-transition', Path(__file__).resolve(),
             case.state / 'geometry-state.bin', case.state / 'frame-state.bin', PROTOCOL]
    inputs = {str(p): R.sha(p) for p in paths}
    if root.exists():
        report = R.read(root / 'result.json')
        R.require(report['all_pass'] and report['gpu_executed'] is False and report['unusable_icd'] is True
                  and report['command'] == cmd and report['input_sha256'] == inputs,
                  'Existing failed/drifted012 CPU contract; retain, never retry')
        validate_inventory(root, report['payload_sha256'])
    else:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip()
        for p in (Path(__file__).resolve(), PROTOCOL):
            R.require(subprocess.check_output(['git', 'show', commit + ':' + str(p.relative_to(R.ROOT))], cwd=R.ROOT)
                      == p.read_bytes(), 'Commit012 cases/protocol before native CPU contracts')
        root.mkdir(parents=True)
        R.write_new(root / 'started.json', dict(command=cmd, input_sha256=inputs, source_commit=commit, gpu_executed=False))
        report = dict(command=cmd, input_sha256=inputs, source_commit=commit, gpu_executed=False,
                      unusable_icd=True, all_pass=False)
        env = dict(os.environ, VK_DRIVER_FILES='/nonexistent/m001-no-icd.json', VK_ICD_FILENAMES='/nonexistent/m001-no-icd.json')
        try:
            p = subprocess.run(cmd, cwd=R.ROOT, env=env, capture_output=True, text=True, timeout=30)
            (root / 'stdout.txt').write_text(p.stdout)
            (root / 'stderr.txt').write_text(p.stderr)
            report['returncode'] = p.returncode
            if p.returncode == 0:
                report['contract'] = R.read(root / 'capture/cpu-contract.json')
                report['all_pass'] = report['contract'] == expected_contract(case)
        except Exception as error:
            report['error'] = repr(error)
            if isinstance(error, subprocess.TimeoutExpired):
                for kind, raw in (('stdout', error.stdout), ('stderr', error.stderr)):
                    (root / (kind + '.txt')).write_bytes(raw if isinstance(raw, bytes) else (raw or '').encode())
        report['payload_sha256'] = {str(p.relative_to(root)): R.sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
        R.write_new(root / 'result.json', report)
    R.require(report['all_pass'] and report['contract'] == expected_contract(case), '012 native CPU check failed; retain and stop')
    return dict(path=str(root / 'result.json'), sha256=R.sha(root / 'result.json'),
                contract=report['contract'], reused_011=False, gpu_executed=False)
