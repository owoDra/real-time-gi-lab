#!/usr/bin/env python3
"""CPU-only synthetic source/geometry grouping tests; no GPU evidence claim."""
import math
import struct
import unittest
from replay_probe_image import (
    WORK,HIT,CONTRIBUTION,MAGIC,aggregate_probes,compare_images,
    load_state,read_arrays,replay_image
)

def frame():
    vecs=[
        (0,0,0,.01),(1,0,0,0),(0,1,0,0),(0,0,1,10),
        (0,0,0,1),(0,0,0,1)]
    raw=MAGIC+struct.pack('<II',1,1)
    for a in vecs:
        raw+=struct.pack('<4f',*a)
    raw+=struct.pack('<8I',1,1,1,1,8,1,1,1)
    return load_state(raw)

class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.state=frame()
        # One output (eight-direction count reduced to two) and one sample key.
        self.work=[
            (0,0,2,0,i,4,3,0,0,10,0,0,1,0,0,0)
            for i in (0,1)]
        self.contrib=[(4,65535),(4,0)]
        self.hit=[(0,0,1,2,7,2,3,1)]
    def test_binary_input_and_frame_layout(self):
        self.assertEqual(len(MAGIC),12)
        self.assertEqual(WORK.size,64)
        self.assertEqual(HIT.size,32)
        self.assertEqual(CONTRIBUTION.size,8)
        work=b''.join(WORK.pack(*w) for w in self.work)
        hits=HIT.pack(*self.hit[0])
        fixed=b''.join(CONTRIBUTION.pack(*v) for v in self.contrib)
        self.assertEqual(read_arrays(work,fixed,hits),(self.work,self.contrib,self.hit))
        self.assertEqual(self.state['counts'][1:3],(1,1))
    def test_original_gpu_aggregation_matches_expected_fixed_average(self):
        groups,count=aggregate_probes(self.work,self.contrib)
        self.assertEqual(count,1)
        self.assertEqual(groups[(0,0,2,0)],[32768,1,32768])
        image=replay_image(self.state,self.hit,groups)
        self.assertAlmostEqual(image[0],32768/65535)
        self.assertEqual(compare_images(image,image)['max_abs_error'],0)
    def test_blocked_per_ray_counterfactual(self):
        groups,count=aggregate_probes(self.work,self.contrib,b'\x01\x00')
        self.assertEqual(count,1)
        self.assertEqual(groups[(0,0,2,0)],[32768,1,0])
        self.assertGreater(replay_image(self.state,self.hit,groups)[0],0)
        self.assertEqual(replay_image(self.state,self.hit,groups,True),[0])
    def test_invalid_contribution_rejected(self):
        with self.assertRaisesRegex(ValueError,'identity'):
            aggregate_probes(self.work,[(999,1),self.contrib[1]])
    def test_incomplete_group_rejected(self):
        with self.assertRaisesRegex(ValueError,'one-to-one'):
            aggregate_probes(self.work[1:],self.contrib[1:])
    def test_incorrect_shadow_flags_rejected(self):
        with self.assertRaisesRegex(ValueError,'length'):
            aggregate_probes(self.work,self.contrib,b'\x01')
        with self.assertRaisesRegex(ValueError,'shadow label'):
            aggregate_probes(self.work,self.contrib,b'\x04\x00')
    def test_unmatched_image_fails_positive_support(self):
        self.assertEqual(compare_images([0],[.001])['positivity_disagreement_pixels'],1)

if __name__=='__main__':
    unittest.main()
