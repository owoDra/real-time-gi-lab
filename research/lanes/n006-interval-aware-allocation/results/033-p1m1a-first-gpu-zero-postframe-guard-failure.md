# N006 P1m1a — first actual GPU run: control PASS, zero intervention diagnostic guarded out; exact prefix/tail validator repaired

2026-10-11. User-uploaded `n006-p1m1a-canonical-key-pilot-summary.json`, raw SHA256 `7b9fd8cca73a4764f796ebe8f086595c7086caf5c9cda1a6fb6dc7c7929cc9dd`, target **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**, git clean HEAD **`6f37f288821545082a93463620142f0575cda5d1`**, Sponza `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. Prospective M1a protocol [023](../experiments/023-p1m1a-single-canonical-key-extraray-preflight.md). `status=invalid-retained`, **one verified case** (control), **one failure** (zero); low/high NOT executed; no independent reference or quality labels.

- Control: 3008 canonical outputs, 24064 base rays, N004 GPU/CPU mismatches=0, `canonical_m1.executed=false`, original M0 key-row SHA `020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2` identical to M0 PASS, HDR PFM sha `2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e` EXACT accepted software control. Thus control **PASS**.
- Zero: source and target warmups completed; canonical target GPU render completed and HDR PFM was written; **N004 validator cross-check cpu_vs_candidate=0, gpu_validator_vs_candidate=0, cpu_vs_gpu_validator=0**. At subsequent independent M0 postframe coverage diagnostic `[P1m0-GPU] enter diagnostic`, rejected with `P1m0 requires finished Lane-E-final software canonical lean-hash frame`. No raw zero candidate evidence was serialized into run-summary; cannot assert Zero 8+4 radiance/changed-pixel/effect success. Low and High not entered.
- **Root cause in source**: at `n006_runtime.cpp` canonical base-prefix verifier, `bool valid = result.stats.work_items == result.stats.outputs * impl.settings.rays_per_probe;` assumed *total* rays always equals 8×outputs, even when P1m1a intentionally appends exactly four distinct rays. Hence `extra.base_prefix_correct=false` regardless of the actual first 8-ray prefix, and later `state_->last_canonical_frame=false`, causing the M0 diagnostic precondition to reject the frame. This is a stale **validation predicate**, not sufficient evidence of a shader or key-selection defect. The user's provided summary supports exact failure stage, but did not include zero frame detailed counters or the PFM, so no effect/gain measurement is available.
- **Fix**: preserve original per-output eight-ray identity, directions, unique-key and owner validations exactly, and require both `result.stats.work_items == outputs*8 + (m1 ? 4 : 0)`, `extra.base_traced_rays == outputs*8`, `extra.extra_work_items == (m1 ? 4 : 0)`. This removes only the self-contradiction in total ray count and adds exact 4-ray tail closure; existing separate extended-ray identity and integer 8+4 sum checks still mandatory. New static regression verifies control 3008×8=24064 and M1 expected 24068, including M0 guard dependency.
- No changes to shader, fixed calibration tokens, reference protocol, or historical accepted shaders. Correctness of the amended predicate inferred from source; **new branch HEAD is not yet locally unit/GPU validated**.

## Next

Run the unchanged N006 P1m1a four-case script against fast-forwarded branch; rerun entire **same prospective** control, zero, low and high set (no cherry-picking):

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1a_canonical_pilot.sh
```

Upload `out/research/n006-interval-aware-allocation/p1m1a-canonical-key-pilot/<UTC>/n006-p1m1a-canonical-key-pilot-summary.json`. If 4/4, proceed to signed independent reference quality protocol [024](../experiments/024-p1m1b-independent-reference-signed-gain-protocol.md); otherwise retain exact failures, fix cause without relaxing frozen quality/accuracy gates. **No P1 model or P2 scheduling GO.**
