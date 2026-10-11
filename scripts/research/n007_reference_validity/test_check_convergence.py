import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from check_convergence import SPP, SEEDS, assess
from test_inspect_hdr import make_pfm


class TestCampaign(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = {'schema_version': 1, 'source_commit': 'a'*40,
                         'scene_sha256': 'b'*64, 'frame_state_sha256': 'c'*64,
                         'levels': []}

    def tearDown(self):
        self.temp.cleanup()

    def add(self, spp, unstable=False):
        entries = []
        for k, seed in enumerate(SEEDS):
            path = self.root / f'{spp}-{seed}.pfm'
            make_pfm(path, lit={j: .01 + (k*(1e-4 if unstable else 1e-8)) for j in range(200)})
            entries.append({'seed': seed, 'path': path.name,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        self.manifest['levels'].append({'spp': spp, 'references': entries})

    def run_report(self):
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.manifest))
        return assess(path)

    def test_two_consecutive_levels(self):
        self.add(512)
        self.add(1024)
        self.assertEqual(self.run_report()['eligible_at_spp'], 1024)

    def test_non_convergence_complete(self):
        for spp in SPP:
            self.add(spp, unstable=True)
        self.assertEqual(self.run_report()['status'], 'statistical-screen-fail')

    def test_reject_unordered_spp(self):
        self.add(1024)
        with self.assertRaisesRegex(ValueError, 'ordered prefix'):
            self.run_report()

    def test_manifest_sha_guard(self):
        self.add(512)
        self.manifest['levels'][0]['references'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            self.run_report()

    def test_duplicate_seed(self):
        self.add(512)
        self.manifest['levels'][0]['references'][1]['seed'] = SEEDS[0]
        with self.assertRaisesRegex(ValueError, 'distinct seeds'):
            self.run_report()

    def test_no_extra_after_accepted(self):
        for spp in (512, 1024, 2048):
            self.add(spp)
        with self.assertRaisesRegex(ValueError, 'continued after'):
            self.run_report()


if __name__ == '__main__':
    unittest.main()
