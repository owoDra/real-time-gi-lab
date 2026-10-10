# N006 P1l-B1a — near-first software-primary matched A/B REJECT

Issue #42. **Frozen acceptance gate applied without change. Candidate REJECT (do not adopt).** User-uploaded `n006-p1l-b1a-summary(1).json`, SHA256 `4751a305e4dc9d450300a403ec2d4971330f7ee3de1eca412864de27f90c6464`. Experiment protocol `n006-p1l-b1a-primary-near-first-v1`, `mode=matched`, `status=complete`, `failures=[]`, `formal=false`, `results.decision=REJECT_OR_REFINE`, measured clean source HEAD `e13957cecd426a8939362ab433de20abaab48a25` on **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**; Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. Pre-registered acceptance at `../experiments/016-p1l-b1-primary-near-first-traversal.md`, **frozen before preflight and before any candidate GPU timing**.

## Measurement integrity / correctness

- **15/15 fresh processes**, five Lane-E-final-Software scenarios × three independent processes; each 32 source warmups + eight target-state current warmups, then **24 measured frames**, `011001100110011001100110` (six `0110` blocks). Exactly **360 measured frames / 180 adjacent AB or BA pairs**, **36 pairs per scene / 18 pairs per order**.
- All 360 frames had frozen, backend-specific accepted HDR **PFM SHA exact**, within-process N006 GPU `primary_hits` **byte exact** against original baseline first frame; fixed canonical P1j-A lean-copyback output counts/ray totals per scene, one N004 full CPU-vs-GPU hit oracle per process on first candidate measured frame index 1, shader/storage/hash correctness and GPU stage timestamp-closure gates. All `runs[].baseline_primary_bytes_equal_all_frames=true`, `failures=[]`; no new reference rendered. CPU oracle was **sampled 15 times**, not on every one of the 360 frames. Distinct prior five-scene B1a preflight `mode=preflight` remains a separate study.
- Observed large per-pair timestamp swings (hundreds of µs in both directions) even with ABBA balancing, so **no causal attribution** to node count, cache, compilation effects, wave occupancy, memory traffic or clock state without targeted instruments. The unsampled frame correctness is supported by image+primary hit parity, not a new CPU oracle.
- The Software-only optimization is not validated on a device where HWRT is unavailable; CPU/GPU driver/hardware generalization is outside scope.

## Frozen five-scene matched GPU result

Each row = 36 adjacent same-process paired candidate-minus-baseline GPU timestamps, **negative = faster**, all samples retained. “Primary” and “renderer” percent numbers are the **median of 36 paired percentage deltas**, **not** a percentage of global frame medians. The win count refers to primary-stage pairs only.

| Scenario | Primary paired median µs | Primary paired median % | Primary wins /36 | Primary per-process medians µs (three independent processes) | Full renderer paired median % | Renderer median regression ≤ +3%? |
| --- | ---: | ---: | ---: | --- | ---: | :---: |
| static | −21.841 | **−1.354%** | **18/36** | +62.198 / −194.469 / +191.905 | −3.907% | YES |
| camera-motion | **+61.757** | **+6.194%** | **15/36** | −17.493 / +209.077 / −33.223 | **+3.241%** | **NO** |
| light-motion | **+119.247** | **+12.600%** | **13/36** | +166.456 / +41.178 / +182.707 | **+4.010%** | **NO** |
| moving-rigid | **+67.548** | **+10.114%** | **14/36** | +84.901 / +67.548 / +118.886 | **+5.082%** | **NO** |
| deforming-control | **+178.439** | **+15.887%** | **12/36** | +78.249 / +143.793 / +270.494 | **+4.428%** | **NO** |

Frozen threshold required primary median **at least 5% lower** and **≥24/36 faster pairs** with ≥2/3 negative per-process medians **in ≥3/5 scenes**, and **no scene renderer median >+3% regression**. **Actual: 0/5 scenes satisfy the scene primary gate; 4/5 violate full-renderer non-regression. REJECT immediately.** Static's slightly negative primary delta is well under 5% and is only 18/36 pairs, with 2/3 *positive* process medians. Never extrapolate the **4/5 seemingly faster single AB pairs in preflight** into validated performance; the frozen repeated ABBA data contradicts them. Moving-rigid was +42.13% primary in preflight and is +10.11% over 36 matched pairs, with **3/3 independent primary process medians positive**.

### Order-effect diagnostics (descriptive only, 18 pairs per order)

| Scenario | Primary median candidate-baseline µs in AB `01` | In BA `10` |
| --- | ---: | ---: |
| static | −74.0 | +87.8 |
| camera-motion | +35.4 | +76.2 |
| light-motion | +62.7 | +182.7 |
| moving-rigid | +33.5 | +188.0 |
| deforming-control | +102.3 | +227.7 |

Every scene has a *more positive / less beneficial* candidate-minus-baseline difference in `10` than in `01`. Both orders appear **18 times per scene**, so this is **not a systematic imbalance in how many AB/BA pairs were collected**, but it does warn of temporal interference, thermal/clock drift, pipeline-cache dependence or measurement-order effects **that were not controlled or directly measured**. Also note large negative-control secondary traversal and producer fluctuations in some individual pairs, despite only changing the primary shader, consistent with run-level GPU variability. Do not assert “near-first changes cache” or “near-first reduces nodes” without counterfactual work counts.

## What the result does and does not show

- **Correctness hypothesis PASS:** the approximate child-center push-order change produced byte-exact accepted whole-frame images and primary hit results for all repeated frames.
- **Performance hypothesis FAIL:** no replicated primary/complete-frame improvement under the previously declared gate, and all tested dynamic/lighting regimes except static showed net renderer median regression.
- **Source-level possible causes, NOT evidenced causal roots:** extra two child BVH node loads per internal node, more coherent or less coherent traversal wavefronts, poor center-projection proxy for true ray-AABB entry, changes to branch paths / memory locality, GPU timing interference. The five-scene B0 previously counted baseline primary BVH visits and E003 secondary 26 child-AABB tests/ray, but **B1a did not count candidate-vs-original primary nodes**. Thus whether B1a visits fewer nodes at all is unknown.

## Decision, next research gate

**REJECT B1a as a runtime/production default**. Preserve the N006 opt-in candidate and all failed data for reproducibility, but do NOT enable by default, do NOT merge into accepted N003 shader, and do NOT selectively adopt the seemingly faster static/light preflight cases.

Next **bounded diagnosis-only B1b** before another expensive 15-process run: clone current N006 B0 *instrumented primary* shader for each traversal arm, retaining the one-work-item-per-pixel counters (node pops, triangle tests, hit, stack overflow) and accepted hit bytes. Run the same five supported software scenarios with one warm target per arm and require exact PFM/primary-hit byte parity. Compare **per-pixel primary BVH visit distributions and branch work** between original and B1a on equal rays; report sums/mean/p50/p90/p99/max. Collect shader SPIR-V instruction and register/occupancy **if available** without treating count shaders as timing sources. **Do not time instrumentation as candidate performance**. If node visits do not drop, reject approximate center scheduling as a pruning strategy; if visits drop yet GPU times regress, investigate child memory reads, instruction pressure and lane divergence before trying a cheaper ordering implementation. This is **prospective planning only**; B1b code/GPU evidence not yet available.

The independent E003 secondary work (~25.5–26.3 eight-way child AABB tests per actual ray and only ~3.4 spatial hash probes) remains a plausible future alternative optimization track. N003 shadow query regimes (light 9,797 queries vs static/deforming 251 vs moving/camera 0) remain separate. Avoid re-running B1a or primary shader random variants without bounded work-count evidence. Original N004/N005, accepted older renderers and GitHub Actions remain unchanged, as does issue #42's gated predictive marginal-value allocation P1/P2.
