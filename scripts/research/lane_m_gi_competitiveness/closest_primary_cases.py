"""013 fixed observed-corpus cases and unchanged native capture arguments."""
from dataclasses import dataclass
import json
from pathlib import Path

from closest_primary import ROOT

TARGETS = tuple((cell, backend) for cell in ('C1', 'H01', 'H02', 'H03')
                for backend in ('hwrt', 'software'))
BASE = ROOT / 'out/research/lane-m-gi-competitiveness'
CONTRACT = ROOT / 'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract'


@dataclass(frozen=True)
class Case:
    cell: str
    backend: str

    def __post_init__(self):
        if (self.cell, self.backend) not in TARGETS:
            raise ValueError('Unregistered013case')

    @property
    def name(self):
        return self.cell.lower() + '-' + self.backend


def command(case, binary, output):
    if case.cell == 'C1':
        historical = ROOT / 'research/lanes/n010-comparison-readiness/results/011-rc-correctness-pilot.json'
        row = next(x for x in json.loads(historical.read_text())['rows']
                   if x['cell'] == 'C1' and x['backend'] == case.backend)
        result = list(row['command'])
        result[2] = str(binary)
        result[result.index('--out') + 1] = str(output)
        return result
    scene = BASE / f'm001-first-heldout-v1/assets/M001-{case.cell}.gltf'
    return ['bash', str(ROOT / 'scripts/run_with_vulkan.sh'), str(binary),
            '--scene', str(scene), '--scenario', 'static', '--backend', case.backend,
            '--direct-profile', 'ulp4', '--spp', '512', '--out', str(output)]
