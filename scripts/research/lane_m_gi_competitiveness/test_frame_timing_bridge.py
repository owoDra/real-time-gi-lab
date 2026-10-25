"""044 CPU contracts for pair statistics, calibration/candidate decisions and quality inputs."""
import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
import frame_timing_bridge as T


def write_process(root,comparisons,effects,noise=0.,rng=None):
    (root/'capture').mkdir(parents=True);rows=[]
    for pair in range(T.WARMUP+T.MEASURED):
        for j,name in enumerate(comparisons):
            e=effects[name]+(rng.normal()*noise if rng is not None else 0.);rows.append(dict(comparison=name,pair=pair,warmup=pair<T.WARMUP,order='AB' if (pair+j)%2==0 else 'BA',position=j,a_us=1000.,b_us=1000.*math.exp(e),log_b_over_a=e))
    (root/'capture/pairs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))


class Contracts(unittest.TestCase):
    def test_campaign_statistics_use_only_measured_pairs(self):
        with tempfile.TemporaryDirectory() as t:
            roots=[]
            for k in range(8):
                r=Path(t)/f'p{k}';write_process(r,['X'],{'X':.1+.001*k});roots.append(r)
            rows=[json.loads(l) for l in (roots[0]/'capture/pairs.jsonl').read_text().splitlines()]
            for x in rows[:T.WARMUP]:x['log_b_over_a']=9.
            (roots[0]/'capture/pairs.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
            s=T.campaign(roots,['X'])['X']
            self.assertAlmostEqual(s['effect'],np.median([.1+.001*k for k in range(8)]));self.assertAlmostEqual(s['span'],.007);self.assertEqual(s['pairs'],96);self.assertEqual(s['same_sign_pair_fraction'],1.)

    def test_calibration_requires_all_sizes_and_quiet_control(self):
        stats={}
        for size in T.SIZES:
            stats[f'{size}-plus0']=dict(process_medians=[.001,-.001]*4,span=.002,max_order_bias=.001,same_sign_pair_fraction=.5)
            for d in (5,10,20):stats[f'{size}-plus{d}']=dict(process_medians=[math.log(1+d/100)]*8,span=.001,max_order_bias=.001,same_sign_pair_fraction=1.)
        self.assertEqual(T.calibration_decision(stats)['minimum_detectable_effect'],.05)
        stats['multi-plus5']['span']=.2;self.assertEqual(T.calibration_decision(stats)['minimum_detectable_effect'],.1)
        stats['tiny-plus0']['process_medians']=[.03]*8;d=T.calibration_decision(stats);self.assertFalse(d['control_pass']);self.assertIsNone(d['minimum_detectable_effect'])

    def test_candidate_decision_thresholds_and_directions(self):
        base=dict(span=.01,max_order_bias=.01,same_sign_pair_fraction=.9)
        self.assertEqual(T.candidate_decision(dict(base,process_medians=[-1.]*8,effect=-1.),math.log(1.2)),'FASTER')
        self.assertEqual(T.candidate_decision(dict(base,process_medians=[.5]*8,effect=.5),math.log(1.2)),'SLOWER')
        self.assertEqual(T.candidate_decision(dict(base,process_medians=[-.1]*8,effect=-.1),math.log(1.2)),'INCONCLUSIVE')
        self.assertEqual(T.candidate_decision(dict(base,process_medians=[-1.]*7+[.1],effect=-1.),math.log(1.2)),'INCONCLUSIVE')
        self.assertEqual(T.candidate_decision(dict(base,process_medians=[-1.]*8,effect=-1.),None),'TIMING_INCONCLUSIVE')

    def test_registered_rungs_and_published_quality_inputs(self):
        self.assertEqual(T.RUNGS[('H01',2)],(256,16));self.assertEqual({v[0] for k,v in T.RUNGS.items() if k[1]==8},{1024})
        q=T.quality_inputs('H01',2);self.assertAlmostEqual(q['PT16R'],0.08459497891888781);self.assertTrue(0.12<q['RSR']<0.16);self.assertGreater(q['PT1R'],q['PT4R'])

    def test_sizes_are_exact_percent_deltas(self):
        for count,base in T.SIZES.values():
            self.assertEqual(base%100,0)
            for d in T.DELTAS:self.assertEqual(base*(100+d)//100*100,base*(100+d))


if __name__=='__main__':
    unittest.main()
