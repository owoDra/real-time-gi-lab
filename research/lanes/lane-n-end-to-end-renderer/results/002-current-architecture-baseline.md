# N002 — current architecture end-to-end baseline

Status: **Complete**

Issue: #27  
Parent: #26  
Evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Decision

N002 is complete. The accepted A–M architecture passed the full six-scenario Lane-N renderer boundary with correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and required memory-category validation.

This result remains a **descriptive baseline only**. It does not declare a performance winner or regression/improvement threshold. N003 must not start until the Lane-N complete-frame timing and quality interpretation contract is prospectively calibrated and frozen in #31.

## Target evidence

- target GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- driver: RADV / Mesa 26.1.2;
- validation summary: `status = pass`, `n002_complete = true`, `pending_scenarios = []`;
- clean evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`;
- validation-layer error lines: `0`;
- deterministic playback digest: `805c544bed5aaaf7c32dd942d5e8f9f460ff670601b336fc12a521fbd57398c5`;
- scene bundle digest: `d1590b8a8c58ff81dcab86121d5d6d12ca1532b1f0f5b9d472b1dfcd5c7b3649`;
- all six frozen frame pairs passed traversal/OOB/storage/lifetime correctness gates;
- all six references converged at 512 spp under the frozen two-seed rule;
- campaign-level renderer and reference HDR signal are both present.

## Frozen scenario coverage

| Frame | Scenario | complete GI GPU | complete renderer GPU |
| ---: | --- | ---: | ---: |
| 0 | static | 723.254 us | 743.573 us |
| 1 | camera-motion | 713.836 us | 730.869 us |
| 2 | light-motion | 1315.499 us | 1355.215 us |
| 3 | moving-rigid | 2924.557 us | 2958.581 us |
| 4 | stable-topology-deforming | 1841.819 us | 1869.191 us |
| 5 | topology-changing-high-churn | 2461.357 us | 2494.620 us |

These timings are informational only. No cross-scenario or architecture performance ranking is valid from this single baseline run.

## Topology/high-churn evidence

Frame 5 exercised the retained Lane-M object-local rebuild boundary:

- dynamic partition size: 796 primitives;
- replaced primitive identities: 398 (50% churn);
- topology mutations: 1;
- backend rebuilds: 1;
- static ownership/BLAS remained outside the replacement path;
- old/new dynamic-BLAS overlap: 252,928 bytes;
- true lifetime peak: 363,424,016 bytes (~346.59 MiB).

The handover sequence is replacement dynamic BLAS build -> TLAS switch -> old dynamic BLAS retirement. Whole-scene rebuild is not used.

## Image-quality observation

Raw HDR errors are retained for every frame and `affected_pixel_fraction` is zero for all six. That does **not** mean the renderer matches the reference perfectly: non-zero absolute and relative error metrics are present, while the current affected-pixel absolute threshold is above the observed error/radiance scale for this dim workload.

Therefore the current affected-pixel classification is not suitable for N003 interpretation. #31 must freeze a scale-appropriate quality interpretation rule prospectively before current-vs-vanilla comparison. Individual black reference frames remain valid observations and are not excluded.

## Next

Complete #31: Lane-N complete-frame timing calibration and quality interpretation freeze. Only then proceed to N003 vanilla Split Radiance Cascades under the same renderer boundary.
