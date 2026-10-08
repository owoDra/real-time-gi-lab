# N005 P3 formal comparison result

Status: **complete**

Formal evidence commit: `de0fef81fb584d4b8a992047f54e5e11c83f8ab4`

Decision: **refine**

## Formal validity

The frozen P3 campaign completed under `n005-p3-formal-comparison-v1`.

All formal gates passed:

- clean `research-n005-adaptive-tracing` evidence commit;
- target GPU matched AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- one canonical converged reference set per case shared across all modes/repetitions;
- five fresh-process repetitions per case/mode with frozen rotating mode order;
- all raw samples retained;
- no sample exclusion;
- no post-hoc threshold or budget change;
- no GPU profile change;
- current / uniform / adaptive correctness passed;
- base prefix and appended extra-work validation passed;
- zero substantive traversal mismatches;
- zero overflow/storage failures;
- uniform/adaptive active work remained exactly 9,216 extra rays;
- inactive/control frames performed zero extra work.

Controls (static, changing illumination, world-dense) produced identical quality across all three modes because the frozen state gate issued no extra work.

## Formal result

The frozen adaptive candidate was:

- `depth-discontinuity >= 0.01`;
- camera/dynamic state-change gate;
- 576 owner regions;
- 4 cascades;
- 4 extra rays per selected probe;
- 9,216 actual extra rays per active frame.

### Camera abrupt reveal

RGB RMS improvement versus current:

- uniform: **2.28%**
- adaptive: **3.99%**

Adaptive improved RGB RMS by another ~1.74% relative to uniform, but its median complete-GI cost was ~217.7 us higher than uniform. Uniform's incremental cost versus current was negative under the frozen median measurement, so its GPU-cost efficiency is formally measurement-limited.

This is a quality win for adaptive, not a demonstrated cost-efficiency win.

### Camera gradual motion

Across the eight active frames:

- median RGB RMS improvement versus current:
  - uniform: **3.21%**
  - adaptive: **3.64%**
- median complete-GI incremental cost:
  - uniform: **147.5 us**
  - adaptive: **338.4 us**

Adaptive had lower RGB RMS than uniform on 5/8 frames and worse RGB RMS on 3/8 frames. Its median quality improvement was slightly larger, but its median incremental complete-GI cost was substantially larger. Timing also retained noticeable run-to-run variance.

This is mixed evidence, not a repeatable quality-vs-cost win.

### Stable-topology deforming

This is the strongest adaptive result.

RGB RMS improvement versus current:

- uniform: **3.53%**
- adaptive: **4.51%**

Median incremental complete-GI cost:

- uniform: **+371.5 us**
- adaptive: **+241.2 us**

Adaptive was both higher quality and ~130.3 us cheaper than uniform at the same 9,216-ray budget. p99 absolute/relative error also improved more. Uniform slightly worsened the scale-aware affected-pixel fraction while adaptive preserved it.

This regime supports the central targeting hypothesis.

### Topology-changing high churn

RGB RMS improvement versus current:

- uniform: **3.558%**
- adaptive: **3.523%**

Median incremental complete-GI cost:

- uniform: **+635.4 us**
- adaptive: **+703.9 us**

Adaptive was very slightly worse in RGB RMS and ~68.5 us more expensive than uniform. p99 absolute/relative error also favored uniform slightly.

This is a direct counterexample to adopting the frozen depth-discontinuity candidate as a universal adaptive policy.

## Cross-regime interpretation

Across the 11 active formal frames:

- adaptive had lower RGB RMS than uniform on **7/11** frames;
- adaptive had lower complete-GI median time than uniform on only **3/11** frames;
- clear Pareto wins (better RGB RMS and lower cost) were limited;
- some frames were tradeoffs and several were Pareto losses;
- the frozen scale-aware affected-pixel blocker was not materially reduced by adaptive tracing.

Therefore:

1. **Targeted extra tracing is causally useful.** The equal-ray experiments show that ray placement matters, particularly for stable deformation.
2. **The single depth-discontinuity heuristic is insufficient as a general policy.** It does not identify the most valuable work consistently across camera and topology-changing regimes.
3. **The N004 quality blocker is not solved.** Improvements are modest and the affected-pixel classification remains essentially unchanged.
4. **Do not adopt the frozen N005 candidate into the architecture as-is.**

## Decision — refine

N005 does not reject adaptive tracing. It rejects adopting this specific single-signal policy as the final architecture.

The evidence supports refining the direction toward an RC-native confidence/update policy rather than simply adding more uniform rays or introducing a ReSTIR-style temporal reservoir.

A follow-up should investigate confidence at the actual Radiance Cascades work unit (probe / cascade / radiance interval), combining only prospectively justified signals such as:

- geometry/ownership/state change;
- depth/visibility discontinuity;
- interval age/validity;
- cascade scale;
- radiance/sample disagreement or variance where it can be measured cheaply.

The next experiment should first determine whether cascade/interval-aware confidence can predict where extra work produces the largest error reduction. It should not tune a new heuristic on the retained P3 formal set and then claim that same set as formal evidence.

## Final N005 answer

**Adaptive allocation is worth pursuing, but `depth-discontinuity >= 0.01` alone is not sufficient for adoption.**

N005 therefore closes with **REFINE**.
