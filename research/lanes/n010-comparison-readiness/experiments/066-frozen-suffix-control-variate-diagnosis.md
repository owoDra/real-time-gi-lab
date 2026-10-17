# N010 prospective frozen full-suffix predictor diagnosis

Date: 2026-10-17 JST. Parent: `dc0550f`. Before compile/acquisition.

## Question and distinct construction

191 locates observed disagreement after the first indirect reflection. 202's
fixed next-hit-direct predictor fails; it predicts only one next contribution,
not the remaining finite-depth sum. 203's geometry-sorted array also fails.
Investigate a frozen, independently piloted predictor of the **whole remaining
suffix**, with an exactly integrable directional table. This is a distinct
method, not tuning the failed 202 grid/midpoint construction or 203 sort key.

The [Neural Control Variates author paper](https://arxiv.org/abs/2006.01524)
motivates integrand approximations with known integrals. This prototype uses
an elementary table, no neural network or claimed paper reproduction. Its
conditional-zero-mean argument below is specific to this construction and
still needs independent physical/numerical validation before reference use.

Exactly eight fixed non-tail pixels from 202, C1 T_B8, center samples, original
canonical geometry/BVH/offset/inset/direct/cosine path code, grey rho1,
nonemissive two-sided materials and grey point light only. Reject mismatches.
Train once, before scoring: 8192 original paths per fixed pixel, pilot seed
`0x50494c4f5431`, same pinned Sobol net. This is extra disclosed auxiliary
work, not one of the original four scored reference replicates. No scored
seeds, paths, pixels, targets or acceptance cutoffs define or tune the model.

For every training continuation after bounce j=1..6 retain current origin,
normal octant, original cosine-square cell (4x4), j, and sum of the original
later per-bounce luma contributions k=j+1..7. Under restricted rho1/grey, this
is the local remaining suffix contribution. Quantize origin into 8x8x8 voxels
of original full-scene bounds, clamped at edges; normal signs define octant.
Key includes j. For every key/cell keep sum/count, with fixed pseudocount32
toward the corresponding global j suffix mean. Unvisited keys have constant
coefficients and therefore zero correction. Freeze/dump every nonempty table
cell, global sums/counts and construction parameters before scored paths.

At each scored continuation j=1..6, look up all sixteen coefficients q_a of
that state and set H=sum(q_a)/16. Add throughput*(H-q_selected) to the separately
recorded corrected indirect estimate. Keep the original path contribution,
RNG coordinate map, ray, intersections and counters untouched. No additional
rays during scoring; no weights, sample rejection, clamping or model updates.
Cosine-square cells have equal uniform measure, so for a frozen model the
continuous conditional integral of H-q_selected is zero at each state.
This is an argument about integration, not an iid SE claim for fixed RQMC
replicates or a finite-hash independence proof. Scored/training domain and
all-state/prefix behavior remain to be validated before any new ladder.

## One bounded prototype, result209

Work `frozen-suffix-cv-diagnosis-v1`, result
`209-frozen-suffix-cv-diagnosis.json`. One compile, one native invocation,
one CPU nice15, 4GiB address space, 220CPU/300elapsed seconds per invocation.
Pilot 65536 paths total, scored8192 per pixel per original four N007 seeds.
Record pilot path count and model dump, all original/corrected moments and
resource/source/binary/payload hashes. Retain every record. No concurrent
scientific worker, GPU or default Renderer change; stop on operational error.

Original 32 means/second moments must reconstruct 193 bit-for-bit. Corrected
deterministic components must stay exact and all moments finite. Report any
negative corrected mean. Promising triage is the previous fixed diagnostic
standard: p99 ratio<=0.75 AND replicate-variance ratio<=0.75^2 with valid controls.
Negative stops this fixed model/grid/prior/pilot construction without tuning or
larger-level dispatch. Positive is only a small diagnostic; independent
physical/conditional/numerical and state/prefix, then whole-frame feasibility
are required before original eligibility ladders. No reference admission.

All original24 slots, four scored seeds, six levels/cap, consecutive qualifying
levels, active support/absolute/relative and quality/memory/timing gates remain.
16/24 references remain eligible, timing208 remains FAIL. Error1.0 direct
pixels stay UNRESOLVED / 未解決 and included. No new N-series lane, Actions,
N001–N009 result edits, app/display/clock/power changes or regression tests.
