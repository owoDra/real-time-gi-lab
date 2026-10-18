# Original A6a failure: short-edge target rounding amplifies density error

2026-10-18 JST. POST-HOC diagnosis of failed261. This establishes the
numerical mechanism for one exact failed sample, not a repaired sampler,
reference admission, timing result or N010 readiness.

## Reproduction and retained failures

[436](436-original-sphere-one-pixel-reproduction-outcome.md) records434's
private diagnostic build and435's immutable-original reproduction. At
pixel(96,77), original seed81985529216486895, sample index3265, the exact
exception and all five original density/vertex witness lines match261.
The full original sample/RNG/cache sequence is preserved up to its failure;
the diagnostic stops there. Native time is0.315705 seconds rather than a
full-frame retry. No acceptance threshold or original header changes.

Recipe137/source committed `d54eee33` before preparation.
[437](437-original-sphere-density-source.json) stopped before payloads or
compilation because its short source selector included both legacy and
current functions. Preserve that failure. Recipe138/v2 committed `0c3a148f`
before [442](442-original-sphere-density-source.json), which verifies whole
header/caller inverse equality using the unique current-function marker.
Only context assignments and operand logging are added; original transport
arithmetic, check and query count remain unchanged. After source review,
[443](443-original-sphere-density-build.json) separately compiles the
private witness in2.608544CPU/2.668753elapsed seconds, no stderr.
After terminal build review, [444](444-original-sphere-density-witness.json)
separately reproduces the same sample/exception/five lines again, retaining
all12 generation/reconstruction operand rows. Native0.365911elapsed seconds.
All native receipts verify CPU31/nice15/120CPU/180elapsed/4GiB.

[445](445-original-sphere-density-arithmetic.json) independently decomposes
the retained operands with binary64 logs and80-digit Decimal arithmetic
from the exact recorded binary64 values. The first analysis-only invocation
at `a869e5ec` stopped without an output on0/0 at the isotropic light origin,
whose source normal is zero. Its failure is explicitly recorded in445.
Source correction `08c5f48c` handles the original constant1/(4*pi) density
separately. No native acquisition was repeated for this arithmetic fix and
no leg or sample was dropped. Actual final analysis0.058623CPU/
0.066905elapsed seconds on CPU31/nice15 within120CPU/180elapsed/4GiB.

## Mechanism for the exact observed failure

Generation and own-family reconstruction have bit-identical origins,
source normals/raw points, target raw points/normals and triangle IDs for
all four own legs. The discrepancy concentrates in light leg2, triangle
7720→7723. Independently reading the original scene confirms these faces
share two vertices, i.e. an edge. Generated hit distance is
1.0685624689140306e-8.

The original code stores raw target `origin + direction * hit_t` in three
binary64 coordinates, then reconstructs direction from stored target minus
origin. Decimal80 arithmetic shows the stored target differs from the
exact expression on the recorded inputs by8.886903743572472e-18 in length.
Normalizing that rounded target delta changes direction by8.307308134e-10.
The additional reconstructed-direction arithmetic error is only9.322909e-17;
the target coordinate storage is the dominant source of this direction
perturbation. The source cosine is small:0.0007645399472185505. Its PDF is
therefore sensitive to this perturbation.

| Short-leg term, reconstructed minus generated | Binary64 log contribution |
| --- | ---: |
| Source directional PDF | +1.0852406600037057e-6 |
| Target area cosine | −7.486312547655416e-8 |
| Subtracted distance squared | −7.898393050709274e-11 |
| Short-leg net | +1.0102985505966444e-6 |

The other three legs contribute about−2.08e-15 combined. Sum of all four
leg contributions is1.0102985485149915e-6, matching the actual cumulative
difference1.0102985470439307e-6 to an accumulation residual−1.471061e-15.
The unchanged bound is1e-6, so the original seed remains **FAIL**.

Decimal80 further attributes+1.085240689419e-6 of the short-leg PDF log
change to raw-target coordinate rounding; reconstructed direction arithmetic
and PDF dot/division rounding contribute about−1.28507e-14 and−1.72391e-14.
Thus the observed failure is explained by target-coordinate precision loss
on a short, grazing, adjacent-face path. This is stronger than observing a
short segment alone. It neither proves an error bound for every path nor
identifies a safe global repair. No statistical/environment-stability test
is involved in this failure, and TIMING_INCONCLUSIVE cannot waive it.

## Required next work

Prospectively register a private candidate retaining additional geometric
precision for raw targets, then evaluate it on this exact reproduction
under the original1e-6 check. Do not copy the sampled density into its
reconstruction, cache the chosen proposal to force equality, drop this
path/seed, change offsets or relax the threshold. Independently verify
geometry/density arithmetic and preserve proposal/physical semantics.
Any broader reference admission still requires the existing full physical,
state, prefix, count, eligibility and bias obligations; one repaired witness
cannot establish those. Do not start another full seed before diagnosis
and a justified candidate qualification. Recipe135's431 PASS261 guard is
still unmet;431 and original seed3 remain NOT RUN.

Inventory remains16/24 eligible references,14/17 original physical artifacts
including one diagnostic-only item, two of four A6a original seeds complete,
seed2 FAIL. The selected execution inventory remains2/28. Bounded history
known-work428–430 is source/archived-proof only. Final timing intake and
missing physical/reference/static/dynamic evidence remain. Reuse415/423's
quality evidence. Sponza direct maximum relative-error1.0 pixels remain
**UNRESOLVED / 未解決**, included. N010 NOT_READY then distinct Lane M;
no N011, architecture promotion or general superiority claim.

No full-seed retry, GPU execution, unit/regression/default-build tests or
GPU/runtime smoke checks. Diagnostic builds434/443 and CPU scientific
diagnoses435/444/445 ran; these are not default Renderer validation.
No N001–N009 results, Actions, CUDA or power/clock/display/driver/app settings
changed. There is no automatic next task or research queue.

Publication metadata:8 configured indexes/346 declared result links resolve;
all221 declared input/payload hash entries across434/435/437/442–445 match
42 unique files. `git diff --check` is clean. Relative to `d254d5f9`, default
CMake/config/workflows and N001–N009 lane trees have no changes. These are
metadata/source checks, not runtime regression validation.
