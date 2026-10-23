"""013 raw intake integration on immutable retained data, never new acquisition."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np

import closest_primary_step as F
import closest_primary_audit as A


class ImageIntake(unittest.TestCase):
    def test_valid_scalar_f32_composite_and_all_pixel_shapes(self):
        d = np.full((180,320,3), np.float32(.1), dtype=np.float64)
        i = np.full_like(d, np.float32(.2))
        t = (d+i).astype(np.float32).astype(np.float64)
        with patch.object(A.R.Q.L, 'read_pfm', side_effect=[d,i,t]):
            images = A.validate_images(Path('/unused'))
        self.assertEqual(set(images), {'direct','indirect','total'})

    def test_nonfinite_negative_wrong_shape_or_channel_difference_rejected(self):
        d = np.zeros((180,320,3), dtype=np.float64)
        for value in [np.nan, -1.0]:
            changed = d.copy();changed[0,0,:] = value
            with patch.object(A.R.Q.L, 'read_pfm', return_value=changed):
                with self.assertRaisesRegex(ValueError, 'physical PFM'):
                    A.validate_images(Path('/unused'))
        with patch.object(A.R.Q.L, 'read_pfm', return_value=d[:-1]):
            with self.assertRaisesRegex(ValueError, 'shape'):
                A.validate_images(Path('/unused'))
        changed = d.copy();changed[0,0,0] = 1
        with patch.object(A.R.Q.L, 'read_pfm', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'scalar channels'):
                A.validate_images(Path('/unused'))

    def test_mismatched_native_total_is_rejected(self):
        d = np.zeros((180,320,3), dtype=np.float64)
        with patch.object(A.R.Q.L, 'read_pfm', side_effect=[d,d,np.ones_like(d)]):
            with self.assertRaisesRegex(ValueError, 'F32 direct'):
                A.validate_images(Path('/unused'))


class RetainedReadOnlyIntegration(unittest.TestCase):
    """Old observations are test fixtures, never corrected-variant evidence."""
    @classmethod
    def setUpClass(cls):
        cls.c1 = F.K.Case('C1','hwrt')
        old = F.R.read(F.C.ROOT/'research/lanes/n010-comparison-readiness/results/011-rc-correctness-pilot.json')
        row = next(x for x in old['rows'] if (x['cell'],x['backend']) == ('C1','hwrt'))
        source_capture = Path(row['command'][row['command'].index('--out')+1])
        # The historical directory also contains four later quality reports.
        # Copy only the thirteen originally recorded native payloads to a new
        # retained CPU fixture; never weaken the new acquisition inventory rule.
        fixture = F.K.BASE/'m001-closest-primary-retained-fixtures-v1'
        cls.c1_capture = fixture/'c1-hwrt'
        if not fixture.exists():
            fixture.mkdir(parents=True)
            cls.c1_capture.mkdir()
            for name,digest in row['payload_sha256'].items():
                source = source_capture/name
                if F.C.sha(source)!=digest:
                    raise ValueError('Historical C1 native fixture source drift')
                target = cls.c1_capture/name
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as handle:handle.write(source.read_bytes())
            F.R.write_new(fixture/'manifest.json',dict(source_capture=str(source_capture),
                          source_report='research/lanes/n010-comparison-readiness/results/011-rc-correctness-pilot.json',
                          native_payload_sha256=row['payload_sha256'],gpu_executed=False,
                          scope='Exact native-only CPU fixture copy; four later score reports excluded; original untouched'))
        manifest = F.R.read(fixture/'manifest.json')
        if manifest['native_payload_sha256']!=row['payload_sha256']:
            raise ValueError('Retained CPU fixture manifest changed')
        for name,digest in row['payload_sha256'].items():
            if F.C.sha(source_capture/name)!=digest or F.C.sha(cls.c1_capture/name)!=digest:
                raise ValueError('Retained CPU fixture is not an exact native copy')
        cls.c1_inputs = {}
        cls.c1_refs = F.reference_inputs(cls.c1, cls.c1_inputs)
        cls.h01 = F.K.Case('H01','software')
        plan = F.R.read(F.C.ROOT/'out/m001-h01-fixed-software-plan.json')
        cls.h01_capture = Path(plan['command'][plan['command'].index('--out')+1])
        cls.h01_inputs = {}
        cls.h01_refs = F.reference_inputs(cls.h01, cls.h01_inputs)

    def test_retained_c1_full_intake_keeps_known_wrong_surface_failure(self):
        report, arrays = A.score_capture(self.c1,self.c1_capture,self.c1_refs)
        self.assertTrue(report['correctness_evidence_valid'])
        self.assertEqual(report['classification'],'CORRECTNESS_FAIL')
        self.assertFalse(report['rows']['2']['named_pixels_pass'])
        self.assertEqual([r['gpu_primitive'] for r in report['rows']['2']['named_pixels']], [49893,172940])
        self.assertTrue(all(a.shape==(180,320) and a.dtype==np.float64 for n,a in arrays.items() if n.endswith('.npy')))
        self.assertEqual(arrays['primary-b2.npz']['gpu_hit'].shape,(57600,))
        self.assertFalse(report['rows']['2']['primary']['exact_gpu_positions_exported'])
        F.rehash(self.c1_inputs)

    def test_retained_software_full_intake_reads_actual_gpu_geometry_and_both_references(self):
        report, arrays = A.score_capture(self.h01,self.h01_capture,self.h01_refs)
        self.assertTrue(report['correctness_evidence_valid'])
        self.assertEqual(set(report['rows']),{'2','8'})
        self.assertEqual(len(arrays),8)
        self.assertTrue(all(x['primary']['pixels']==57600 and x['primary']['scoring_exclusions']==0 for x in report['rows'].values()))
        self.assertTrue(all(x['quality_classification']=='QUALITY_FAIL' for x in report['rows'].values()))
        F.rehash(self.h01_inputs)

    def test_incomplete_native_payload_and_corrupt_software_geometry_are_rejected(self):
        original = Path.stat
        def changed_stat(path,*args,**kwargs):
            result = original(path,*args,**kwargs)
            if path.name=='probe-work.bin':
                fields = list(result)
                fields[6] -= 1
                return os.stat_result(fields)
            return result
        with patch.object(Path,'stat',changed_stat):
            with self.assertRaisesRegex(ValueError,'buffer byte count'):
                A.validate_capture(self.h01,self.h01_capture,self.h01_refs)
        original_read = Path.read_bytes
        def changed_geometry(path):
            raw = original_read(path)
            if path.name=='primary-geometry.bin':
                data = bytearray(raw)
                data[0] ^= 1
                return bytes(data)
            return raw
        with patch.object(Path,'read_bytes',changed_geometry):
            with self.assertRaisesRegex(ValueError,'GPU geometry differs'):
                A.validate_capture(self.h01,self.h01_capture,self.h01_refs)


if __name__ == '__main__':
    unittest.main()
