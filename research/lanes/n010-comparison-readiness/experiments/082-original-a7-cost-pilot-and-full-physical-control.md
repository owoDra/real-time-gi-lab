# N010 prospective original A7 sizing and full analytic/iid physical control

Date:2026-10-17 JST. Parent:761ab55. Before new acquisition. 225/226 complete
9/17 original deterministic full control scenes with byte-exact payloads.
Use unchanged224 exporter. No physical/source/sampler/quality rule changes.

227 is a CPU COST-ONLY pilot: exact original A7 scene,128x96,4 originalseeds,
64 scored samples, one native invocation. Keep every output but make NO
physical/control/convergence decision from this smaller count. Actual child
user+system CPU and elapsed are measured. Estimate full8192 by multiplying
both by128, including pilot setup/output (conservative). Only if estimated
CPU<=160sec AND elapsed<=220sec dispatch228. These operational margins guard
220CPU/300elapsed ceilings, not scientific acceptance. If cost gate fails,
228 remains NOT RUN; do not retry/loosen the gate or substitute pilot results.
Pilot must also be finite with original scene/geometry/seeds/count, direct/
emission/primary bytes exact and all own/conditioned audits passing.

228, only after actual227 PASS, runs EXACT original A7 8192 samples,whole
128x96,4 seeds, one native invocation. Preserve every f64/PFM/hit image.
Validate all original analytic A7 checks via unchanged control_a7 and N010
analytic_gate (original geometric margin, quadrature doubling<=1e-8,
relative region mean<=0.002,NRMSE<=0.01). Do not change its analytic-only mask;
all image data remain retained. Direct/emission means AND second moments and
primary hits must equal original payload bytes at every pixel. Compare full
indirect image to retained independent ORIGINAL iid16384 proof009, same
original <=0.002 per-channel region/global mean and <=0.01 full NRMSE gates.
RQMC uncertainty is replicate means, not per-sample iid SE. Exact scene/count/
seed/geometry and own-density<=1e-6,conditioned error/B<=1 required. Shadow
work counters are descriptive across different samplers, as in081.

Each native oneCPU nice15,4GiB/220CPU/300elapsed. No retry/concurrent research
worker/GPU; stop first failure and retain partial bytes. CPU-only analytic
replay oneCPU/4GiB/220CPU with BLAS/OMP1. Passing228 would be one additional
original full scene,not all17,all-state/prefix/full-frame qualification or
numerical-bias bound for Sponza. References16/24,timing208FAIL,direct1.0 pixels
UNRESOLVED/未解決 included. No settings/buildgraph/N011/Actions/history change.
Unit/regression tests NOT RUN; independent scientific acquisition/control only.
