# N006 P1i — cross-backend canonical correctness: 10/10 PASS

Issue #42. This document records the **second**, successful, immutable P1i campaign. The earlier `07f1bae` campaign stopped at software-static during inherited HWRT-only renderer initialization and remains documented separately in `014-p1i-cross-backend-partial-hwrt-pass-software-blocked.md`; its failure is not erased.

## Provenance and fixed experiment

Uploaded user GPU report `n006-p1i-cross-backend-summary(1).json`; protocol `n006-p1i-cross-backend-correctness-v1`, `status=complete`, `all_cases_byte_identical=true`, `failures=[]`, `formal=false`. Clean `research-n006-interval-aware-allocation` branch at **`85d0b295e5fed0575e984f8e7e9b3993ba347a6e`**, AMD Radeon 8060S Graphics (RADV STRIX_HALO), accepted Sponza SHA-256 `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. No independent reference rendered.

Each of 10 independent processes ran the frozen baseline current and canonical compact GPU ray tracing in sequence, after source warmup. Five supported Lane-E-final scenes per backend, with exact PFM-byte SHA equality **within each** original/canonical case and the frozen GPU cardinality/hash/owner-weight/error contracts checked by the runner.

| Scenario | Backend | Owners | Original rays | Canonical rays | Saved GPU rays | Canonical-build GPU µs | Original/canonical PFM |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| static | HWRT | 4167 | 133344 | **24064** | 81.9534% | 63.040 | identical |
| camera-motion | HWRT | 4231 | 135392 | **25760** | 80.9738% | 62.839 | identical |
| light-motion | HWRT | 4167 | 133344 | **24064** | 81.9534% | 63.400 | identical |
| moving-rigid | HWRT | 4213 | 134816 | **24832** | 81.5808% | 56.067 | identical |
| deforming-control | HWRT | 4172 | 133504 | **24232** | 81.8492% | 60.074 | identical |
| static | Software | 4167 | 133344 | **24064** | 81.9534% | 62.519 | identical |
| camera-motion | Software | 4231 | 135392 | **25760** | 80.9738% | 63.561 | identical |
| light-motion | Software | 4167 | 133344 | **24064** | 81.9534% | 61.998 | identical |
| moving-rigid | Software | 4213 | 134816 | **24832** | 81.5808% | 55.505 | identical |
| deforming-control | Software | 4172 | 133504 | **24232** | 81.8492% | 55.746 | identical |

- Each case reconstructed the original integer owner multiplicity before composite; hash invalid-key / insert / capacity errors and storage/hit validation errors passed the runner's zero-error gates.
- Exact per-scenario visible owners and unique probe keys agree between the HWRT and software cases: key counts 3008 static/light, 3220 camera, 3104 moving rigid and 3029 deforming.
- Source report's **additional scratch = 8,421,464 bytes (~8.03 MiB)** for each canonical candidate; this is *extra* N006 GPU scratch, not a measured new total residency peak. Shader dispatch/copy and owner restoration GPU cost are already included in the actual candidate work.
- All five scenarios' final PFM SHA hashes match across the HWRT and software runs too in this report. This is observational equivalence on the **same HWRT-capable RADV GPU**, not certification of hardware without the ray-tracing extension.

## Supported conclusion

**P1i correctness/portability matrix PASS.** The true canonical GPU work-list and per-probe owner-weight restoration preserve byte-exact end-to-end rendering in 10/10 frozen cases, including a genuinely selected `LaneEFinalSoftware` traversal backend with N003-derived software primary/shadows instead of an HWRT-backed primary renderer. For these frozen workloads, actual dispatched secondary ray work items are 80.97–81.95% fewer.

**Cannot yet conclude**: a net performance gain for software traversal; the P1i paired frames were sequential cold-state and therefore have dynamic-maintenance/primary-visibility differences. Those reported complete-GI times must **not** be used as an A/B speedup claim. Likewise, this does not demonstrate operation on a GPU incapable of VK_KHR_ray_query / acceleration structures, does not test topology-changing/high-churn geometry, different GPUs or worst-case sparse probe distributions, and does not settle memory fragmentation or peak residency for deployment.

Prior P1h did establish **18/18 net post-producer GPU-work wins** with median −82.577 µs for *one matched HWRT/deforming scenario only*; it does not automatically transfer to software.

## Decision and next pre-registered work

**GO P1j for implementation efficiency**, not GO generic production integration or predictive/adaptive N006 allocation. First reduce the currently over-provisioned 524,288-slot GPU hash+owner-count tables without global sorting and with explicit collision/capacity guards. Current 8,421,464 B scratch consists primarily of two ~2 MiB hash/multiplicity arrays and a 4 MiB compact work staging buffer; count the actual Vulkan allocations in the new experiment. Keep the P1j lean-hash path opt-in so the accepted P1g/P1h/P1i results are reproducible. The correctness and net-GI timing gates must include **both HWRT and software** with balanced target-state A/B and all expected image/counter checks.

A later phase could bind the compact GPU work stream directly instead of copying it back, then fuse key discovery into owner production only after separate correctness/performance proof. An aggressive one-shot producer/compaction rewrite is not justified by P1i correctness alone.

Keep previous raw evidence immutable; no N004/N005 source behavior or GitHub Actions.
