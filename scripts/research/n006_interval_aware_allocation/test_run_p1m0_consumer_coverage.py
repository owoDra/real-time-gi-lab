from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_p1m0_consumer_coverage as m0

class TestP1m0CoverageAudit(unittest.TestCase):
    def make_case(self):
        owners, cascades = m0.SCENE_EXPECTATIONS["static"]
        rows = []
        for cascade, count in enumerate(cascades):
            for idx in range(count):
                token = 1 + cascade * (1 << 30) + idx
                rows.append({
                    "token": token,
                    "consumer_pixels": 1 if idx == 0 else 0,
                    "producer_owner_outputs": 1,
                })
        extra_owners = owners*4 - len(rows)
        rows[0]["producer_owner_outputs"] += extra_owners
        coverage = {
            "diagnostic_only": True, "hash_capacity": m0.HASH_SLOTS,
            "valid_primary_pixels": 12770, "lookup_attempts": 12770 * 4,
            "matched_lookups": 4, "absent_keys": 12770 * 4 - 4,
            "invalid_keys": 0, "probe_exhaustions": 0,
            "uint32_overflows": 0, "invalid_launch": 0,
            "canonical_keys": len(rows), "keys_with_consumers": 4,
            "max_consumer_pixels": 1,
            "consumer_lookups_by_cascade": [1,1,1,1],
            "keys_with_consumers_by_cascade": [1,1,1,1],
            "key_rows": rows,
        }
        return coverage

    def test_conservation_and_zero_coverage_keys(self):
        out = m0.audit_coverage(self.make_case(), "static")
        self.assertEqual(out["matched_lookups"], 4)
        self.assertEqual(out["unconsumed_key_count"],
                         sum(m0.SCENE_EXPECTATIONS["static"][1])-4)
        self.assertEqual(out["producer_owner_outputs"],
                         m0.SCENE_EXPECTATIONS["static"][0]*4)

    def test_corrupted_counts_fail_closed(self):
        for key, value in (
            ("invalid_launch",1), ("uint32_overflows",1),
            ("probe_exhaustions",1), ("matched_lookups",5),
            ("canonical_keys",0), ("valid_primary_pixels",0),
        ):
            with self.subTest(key=key):
                case = self.make_case()
                case[key] = value
                with self.assertRaises(ValueError):
                    m0.audit_coverage(case,"static")

    def test_per_key_multiplicity_and_sorting_fail_closed(self):
        a = self.make_case()
        a["key_rows"][0]["producer_owner_outputs"] += 1
        with self.assertRaises(ValueError):
            m0.audit_coverage(a,"static")
        a = self.make_case()
        a["key_rows"][1]["token"] = a["key_rows"][0]["token"]
        with self.assertRaises(ValueError):
            m0.audit_coverage(a,"static")

    def test_negative_and_boolean_counters_rejected(self):
        for bad in (-1,True,1.5,None):
            with self.subTest(bad=bad):
                a = self.make_case()
                a["absent_keys"] = bad
                with self.assertRaises(ValueError):
                    m0.audit_coverage(a,"static")

    def test_wrong_device_frame_rejected_before_pfm_read(self):
        data = {
            "protocol_version": "n006-p1-intervention-v1",
            "variant":m0.VARIANT,
            "scenario":"static",
            "mode":"current",
            "p1m0_consumer_coverage":True,
            "device":{"name":"not-the-accepted-gpu"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                m0.audit_case(data,Path(tmp),"AMD Radeon 8060S Graphics (RADV STRIX_HALO)","static")

    def test_raw_key_hash_does_not_override_accepted_pfm_gate(self):
        a = self.make_case()
        out = m0.audit_coverage(a,"static")
        self.assertEqual(len(out["key_rows_sha256"]),64)

if __name__ == "__main__":
    unittest.main()
