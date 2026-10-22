"""Negative evidence-intake and frozen HDR-gate tests; no GPU acquisition."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import audit_first_pt_quality as A


class FirstPTAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def archive(self, rows):
        path = self.root / 'proof.tar'
        with tarfile.open(path, 'w') as tar:
            for name, kind in rows:
                info = tarfile.TarInfo(name)
                if kind == 'link':
                    info.type = tarfile.SYMTYPE
                    info.linkname = '/etc/passwd'
                    tar.addfile(info)
                else:
                    data = b'{}'
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
        return path

    def test_regular_compact_archive(self):
        p = self.archive([('plan.json', 'file'), ('result.json', 'file')])
        self.assertEqual(A.archive_members(p), {'plan.json': b'{}', 'result.json': b'{}'})

    def test_duplicate_proof_rejected(self):
        p = self.archive([('plan.json', 'file'), ('plan.json', 'file')])
        with self.assertRaises(ValueError):
            A.archive_members(p)

    def test_path_escape_proof_rejected(self):
        p = self.archive([('../plan.json', 'file'), ('result.json', 'file')])
        with self.assertRaises(ValueError):
            A.archive_members(p)

    def test_link_proof_rejected(self):
        p = self.archive([('plan.json', 'link'), ('result.json', 'file')])
        with self.assertRaises(ValueError):
            A.archive_members(p)

    def test_inventory_tamper_rejected(self):
        p = self.root / 'image.pfm'
        p.write_bytes(b'original')
        inventory = {p.name: A.R.sha(p)}
        A.validate_inventory(self.root, inventory)
        p.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'payload changed'):
            A.validate_inventory(self.root, inventory)

    def test_unlisted_payload_rejected(self):
        p = self.root / 'known.pfm'
        p.write_bytes(b'original')
        (self.root / 'unlisted.pfm').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'unrecorded'):
            A.validate_inventory(self.root, {p.name: A.R.sha(p)})

    def test_inventory_cannot_read_outside_root(self):
        root = self.root / 'capture'
        root.mkdir()
        other = self.root / 'outside.pfm'
        other.write_bytes(b'outside')
        (root / 'linked.pfm').symlink_to(other)
        for name in ('../outside.pfm', str(other), 'linked.pfm'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                A.validate_inventory(root, {name: A.R.sha(other)})

    def test_missing_native_evidence_is_not_pass(self):
        with patch.object(A.F, 'WORK', self.root / 'absent'), \
             patch.object(A.R, 'preflight') as preflight:
            with self.assertRaisesRegex(ValueError, 'absent/incomplete'):
                A.audit()
            preflight.assert_not_called()

    def test_frozen_quality_thresholds_include_boundary(self):
        c = {'total': {'nrmse': .05}, 'indirect': {'nrmse': .10, 'signed_sum_bias': -.05}}
        self.assertTrue(A.quality_pass(c))
        c['indirect']['signed_sum_bias'] = .050000001
        self.assertFalse(A.quality_pass(c))
        c['indirect']['signed_sum_bias'] = 0.
        c['total']['nrmse'] = .050000001
        self.assertFalse(A.quality_pass(c))
        c['total']['nrmse'] = 0.
        c['indirect']['nrmse'] = .100000001
        self.assertFalse(A.quality_pass(c))

    def test_missing_signal_metrics_cannot_pass(self):
        c = {'total': {'nrmse': 0.}, 'indirect': {'nrmse': None, 'signed_sum_bias': None}}
        self.assertFalse(A.quality_pass(c))


if __name__ == '__main__':
    unittest.main()
