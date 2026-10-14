# N010 residual direct pixels — post-hoc CPU diagnosis

Status: diagnostic evidence, **not a verified GPU repair**. The two C1 direct
pixels with maximum relative error 1.0 remain **UNRESOLVED / 未解決**, included
in all image scores. N009's final classifications and unresolved-pixel record
are unchanged. No shader, Renderer binary, quality threshold or scoring mask
is changed by this investigation.

## Observations on the retained new C1 captures

[052](052-residual-direct-cpu-diagnostic.json) independently reads both HWRT
and software captures from result 011. Both zero/reference-positive pixels
have different primary primitives from the eligible C1 CPU reference:

| Pixel (x,y) | GPU primitive | Reference triangle/primitive | GPU direct | Reference direct |
| --- | ---: | ---: | ---: | ---: |
| (107,109) | 49893 | 51389 | 0 | 0.00018129397474519365 |
| (261,161) | 172940 | 172941 | 0 | 0.0004036940386722419 |

The primitive numbering equals the triangle index in this static C1 state.
Both backends give the same observations. These are not matched-primary
visibility cases; a shadow-offset-only explanation would be incomplete.

The initial diagnostic reconstructs the float GPU view ray from the frame
state and captured hit distance. It is not an exported GPU ray or an exact
GPU intersection emulator. Its canonical camera approximation and double
point-projection counterfactual are retained in 052. The follow-up
[054](054-primary-tie-cpu-diagnostic.json) parses the actual canonical oracle
scene camera, verifies all original capture payload hashes and all reference
payload hashes, and records the consumed f64 identities.

## Primary tie-rule mechanism supported by CPU geometry

Both Renderer primary shaders use
`max(2e-4, abs(best_t) * 2e-5)` as the tie interval and prefer the lower
primitive ID within that interval. That can select a physically farther
surface. The independent oracle uses strictly closest watertight double
intersection; native pixel PT accepts closest hardware intersection.

For both relevant triangles, the double watertight evaluator gives:

| Pixel | Canonical-ray farther-minus-nearer distance | Legacy tie interval at nearer surface | Pair rule prefers captured farther primitive |
| --- | ---: | ---: | --- |
| (107,109) | 0.020716020570262117 | 0.023960412484563966 | Yes, for either pair visitation order |
| (261,161) | 0.003834397170919601 | 0.009613202325280573 | Yes, for either pair visitation order |

Both triangles also intersect the reconstructed float ray, and the same pair
preference holds there. This is a **post-hoc supported mechanism**, not an
attestation of the GPU's entire candidate sequence or a counterfactual GPU
rerender. Current primary-shader source hashes are recorded in 054.

At (107,109), a shadow ray from the reconstructed captured surface is blocked
by reference triangle 51389, while the oracle-surface shadow ray is clear.
At (261,161), the reconstructed captured-surface cosine is −0.5246545 and the
oracle-surface cosine is +0.5324600. The captured-surface direct term is
therefore zero even without a shadow blocker. The CPU model reproduces both
zero/positive outcomes with the respective primary surfaces. The observed
normal/position differences must not be recast as a proven shadow-only repair.

## Consequence for comparison and next action

Disclose the incumbent's legacy primary tie policy as a measured correctness
weakness. Retain every pixel and all current RC quality losses; no same-quality
speed claim is available for the quality-failing roles. This small direct
discrepancy does not explain the incumbent's 88.8399% indirect NRMSE on C1.

A prospective closest-primary variant would need an actual GPU rerender,
all-pixel primary/direct validation on the declared corpus, new binary/shader
identities and calibration of that variant before any promotion. This
diagnostic does not silently replace the incumbent or invalidate the already
executed all-pixel comparisons. The existing original reference jobs and
continuous comparison/calibration driver continue unchanged.

Only CPU build and diagnosis were run here. No new GPU check or runtime
regression validation was performed for this diagnostic, no default Renderer
promotion occurred, and no N001–N009 result was rewritten.
