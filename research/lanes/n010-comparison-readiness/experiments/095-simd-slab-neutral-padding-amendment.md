# N010 SIMD slab implementation amendment: neutral padding

Date:2026-10-17 JST. Parent:e9bd3e3. Before repaired candidate acquisition.
094/242 compile0; first paired native aborts after0.707784CPU seconds because
SIMD/scalar visited box booleans differ. Retain failure exactly. No cost or
physical inference. Static diagnosis: the fourth packed lane has lo=hi=origin=
inverse=0, so its interval is[0,0], not neutral; horizontal reduction wrongly
includes it. This violates094's intended ignored-padding rule.

Implementation amendment ONLY: OR the existing NaN/ignored-axis mask with
the fourth-lane all-ones mask, making that lane[-inf,+inf] before reduction.
All xyz arithmetic and every original query/node/output/cost check from094
remain exact. New include/driver/work/result identities; preserve sealed094
source and242. This is a changed implementation, not a retry of fixed242 or
threshold change. If any mismatch/error occurs stop and preserve partials.
Original source/proposal/count/physical/statistical/GPU gates unchanged.
OneCPU nice15/4GiB, each native220CPU/300elapsed, no GPU or long queue.
Tests NOT RUN. Full physical11/17,refs16/24,N010 NOT_READY.

Work:out/research/n010-comparison-readiness/simd-slab-neutral-padding-v1
Result:results/243-simd-slab-neutral-padding-prototype.json
Driver:scripts/research/n010_reference_sampling/diagnose_simd_slab_neutral_padding.py
Include:scripts/research/n010_reference_sampling/simd_slab_neutral_padding.inc
