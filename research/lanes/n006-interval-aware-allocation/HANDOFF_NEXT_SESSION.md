# 2026-10-11 NEWEST — P1m2b bounded camera/light independent-state screen IMPLEMENTED, GPU pending

Branch `research-n006-interval-aware-allocation`, Issue #42 OPEN. Previously accepted P1m2a [result 037](./results/037-p1m2a-fixed-tetra-octant-null-image.md): four cases PASS, tetra +4 hit 6/12 (vs P1a uniform 1/12) and High extra sum16=5, **but all three intervention PFMs exactly unchanged** due rounded mean 1→1. C3 calibration exhausted; no HDR gain, P1 predictor or P2 GO. Prior B1a/B1c GPU rejects and C0 static-only retained.

**Next pre-registered protocol [027](./experiments/027-p1m2b-independent-state-observable-image-gate.md) now has source code and command**. [Implementation record 038](./results/038-p1m2b-bounded-screen-implementation-handoff.md). Separate CLI `--p1m2b-independent-state` permits key interventions only in camera-motion / light-motion with accepted software lean-copyback, same 32+8 warmups, M0 frame correctness, reference skip and immutable shaders. In absence of new flag, original frozen static/C3 M1a/M2a token whitelist unchanged. For each scenario, two independent control frames must match accepted PFM and full M0 rows; then preselect one max-consumer and one zero-consumer key per cascade, lowest token ties, missing strata retained; at most 8 keys × 2 scenarios × 2 direction arms = 32 cells; only nonzero image delta gets a repeated isolated confirmation run. Exact frame/owner/N004/HDR checks throughout. Zero effect all cells ⇒ STOP +4/current-integer-quantization allocation family. Positive reproducible *influence* still requires independent HDR reference and sealed holdout before any quality/ROI decision. No known GPU P1m2b result yet.

**Single next user GPU command (source not yet built/tested on their NixOS):**
```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2b_independent_state.sh
```
Upload `out/research/n006-interval-aware-allocation/p1m2b-independent-state/<UTC>/n006-p1m2b-independent-state-summary.json` or build/test error. The script runs build and all N006 Python tests before GPU. Research lane NOT complete. No PR/GitHub Actions.

---

# 2026-10-11 LATEST — P1m2a GPU 4/4 PASS, +4-ray hit recovery but 3/3 exact zero PFM; next study P1m2b DESIGN ONLY

User uploaded correct `n006-p1m2a-tetra-octant-summary.json`, original bytes SHA256 `e0d458a1bf29af2f295d44a941b3e184e58b10fa4a7aa20de6c940012ce1ef08`, clean executed HEAD `fce39c4abeca222227f8a91842221f3179417d95`, AMD Radeon 8060S RADV. `status=direction-calibration-complete`, `failures=[]`, 4/4; target original Sponza static/C3 Zero / Low / High frozen tokens. 3008 canonical outputs, 24064 base rays, 24068 on treatment, 12 merged samples per selected output, zero N004 hit mismatches, M0 key-coverage SHA unchanged, **all control/intervention PFMs exact accepted control SHA `2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e`**. [Result 037](./results/037-p1m2a-fixed-tetra-octant-null-image.md).

P1m2a fixed [0,3,5,6] octant 0.125 jitter added-rays:
- Zero consumer=0: 1 extra hit/4, 1 dark, extra sum16=0; rounded mean 0→0.
- Low consumer=93: 3 extra hits/4, all 3 dark, extra sum16=0; rounded mean 0→0.
- High consumer=875: 2 extra hits/4, **2 positive samples, extra sum16=5**; base sum16=10, `floor((10+4)/8)=1`, merged `floor((10+5+6)/12)=1`; **need extra sum16 ≥8 for this output's 12-sample mean to reach 2**. This is not a quality gain threshold or image change guarantee.
- Across 3 keys **6/12 extra hits versus original uniform-direction M1c's 1/12**; two positive sample rays versus zero; 0 changed RGB pixels/channels for all. Selected-key frame output SHA unchanged. GPU single-thread full-key scan + finalize timestamp ~624.747–632.321us, not a viable P2 runtime or four-ray traversal cost estimate.

**Decision:** M2a *mechanism/GLSL/pass invariants GO*, **no causal image effect in any of 3 convenience calibration keys**, signed global RMS gain exactly 0 against *any common reference* for these 3. P1 predictive value still unknown and P2 scheduler NO GO. Stop tuning directions on same static/C3 triplet.

**NEXT [prospectively preregistered P1m2b 027](./experiments/027-p1m2b-independent-state-observable-image-gate.md)**: bounded independent camera-motion/light-motion state pilot, control-control stability, pre-secondary M0-selected max and zero consumer key per cascade (≤16 keys total), both original uniform and tetra direction arms, full float32 PFM effect/parity (≤32 cells) before independent converged HDR reference; stop this +4/current-quantization family if no replicated nonzero image change. **DESIGN ONLY; no implementation or user GPU command yet.** CLI currently only accepts 3 original static/C3 keys; extending it safely with an explicit different M2b pilot flag, independent case guard, frozen selection and full tests is the next source work. No prior results changed, no PR/Actions.

---

# Latest static audits received (2026-10-11)

Original historical B1c/C0 audit JSONs were received and reconciled in [result 036](./results/036-p1l-archived-static-audit-original-json-provenance.md). B1c remains REJECTED, C0 remains STATIC ONLY, and P1m2a GPU remains unmeasured. Next batch: `bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2a_tetra_octant.sh`. No PR or CI.

---

# 2026-10-11 newest: P1m2a shader/C++ build PASS; stale M1a source-placement test repaired (GPU pending)

User-local P1m2a build successfully generated `n006_p1m2a_tetra_octant_extra.spv`, compiled N006 C++ and linked `phos-n006-intervention`. **227 Python unit tests ran: 1 error**, `test_p1m1a_canonical_probe.TestCanonicalM1Mechanism.test_placement_parity_and_buffer_lifetime`; it looked for removed literal `state_->p1m1_extra_stage->record(`. Current N006 code correctly selects `(request.p1m2_tetra_octant_directions ? state_->p1m2_tetra_octant_stage.get() : state_->p1m1_extra_stage.get())->record(` at the same canonical-to-secondary boundary. Replaced the stale source string with a whitespace-tolerant regex asserting **both arms and their one shared pre-secondary `record`**. Checked regex against current runtime source before pushing. **Test-only fix; no runtime/GLSL behavior changed; unit test suite has not yet been rerun on user's system after fix.** `set -e` stopped before any M2a GPU case: *NO M2a causal/image results yet*.

Next single batch (unchanged):
```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2a_tetra_octant.sh
```
Upload `out/research/n006-interval-aware-allocation/p1m2a-tetra-octant-static-c3/<UTC>/n006-p1m2a-tetra-octant-summary.json`. Previous P1m1c GPU 4/4 pass and 11/12 extra-ray misses unchanged. No PR or Actions. P1 marginal quality and P2 NOT approved.

---

# 2026-10-11 LATEST — M1c GPU 4/4 PASS (11/12 extra misses), M2a fixed tetra-octant alternative pilot READY, NOT GPU tested

User-uploaded `n006-p1m1c-ray-fate-summary.json` original SHA256 **`5c87c2b12b3983070e129cd163f7e2560d75f772c402fa719d302219262908ef`**, clean executed HEAD **`db32b403b3ed0e3ce1afab7bf29df97a4aaf55e7`**, AMD Radeon 8060S RADV. 4/4 `ray-fate-audit-complete`, failures=[], accepted exact original control static PFM and original M0 per-key coverage SHA; all three candidate images **pixel/byte identical**; no independent reference, no signed quality/predictor/P2.
- **Zero** (0 consumer pixels): 4/8 base hits, 0/4 extra hits, 4 misses, extra sum16=0.
- **Low** (93): 5/8 base hits; 1/4 extra hit **but zero radiance**, 3 misses, extra sum16=0.
- **High** (875): 5/8 base hits, 4 positive base16, 0/4 extra hits, 4 misses, extra sum16=0.
- Overall **14/24 base hits vs only 1/12 additional** P1a hashed sphere ray hits in these non-independent frozen keys. Mechanism failure mostly missed geometry, also one dark/rounded-zero hit. Original M1a mechanism PASS remains valid; signed gain mathematically 0 in these three same-image samples. M1c per-key GPU append stage 619–637 µs, serial scan overhead **not a P2 decision cost estimate**. [Result 035](./results/035-p1m1c-gpu-ray-fate-4of4.md).

**Prospectively frozen new calibration experiment P1m2a**, [026](./experiments/026-p1m2a-fixed-tetra-octant-jitter-pilot.md). *Different direction distribution from M1a*, original shader untouched. Fixed tetrahedral octant indices [0,3,5,6] (balanced x/y/z), deterministic `normalize(A001_octant_center + 0.125*hashed_jitter_xyz)`. Original 8 rays unchanged; exactly four rays added to one same token each; 3 fixed calibration tokens retained. New independent N006 shader `n006_p1m2a_tetra_octant_extra.comp.glsl`, opt-in `--p1m2-tetra-octant-directions`, CMake only N006 dependency, runtime selected stage, GPU hit/miss/energy diagnostic, PFM pixel delta comparison. Four separate processes control/Zero/Low/High. Test-only direction and isolation contracts added, but **no local build/GPU results yet**; do NOT make quality improvement claim. New exact batch:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2a_tetra_octant.sh
```

Expected user evidence `out/research/n006-interval-aware-allocation/p1m2a-tetra-octant-static-c3/<UTC>/n006-p1m2a-tetra-octant-summary.json`. Freeze hashes/keys/jitter; if effect nonzero, **do not claim positive quality** until independent converged HDR reference and paired RMS, noise calibrations, separate evaluation and holdout. If no effect, preserve all nulls and decide whether P1 marginal allocator has remaining feasible research paths; avoid unbounded cherry-picking. Issue #42 remains OPEN. No PR or GitHub Actions.

---

# 2026-10-11 NEWEST — P1m1a 4/4 mechanism PASS, three null HDR effects; M1c hit-fate GPU preflight READY

Uploaded `n006-p1m1a-canonical-key-pilot-summary(1).json` SHA256 **`ea8b9c928bd5f3470bcc85f33b1b6d98127a51da94961e5b27f1329e4d6d6f36`**, clean user-measured HEAD `dd5d8830ec008c527607a3eb29cf159f34ba7983`, AMD Radeon 8060S Graphics RADV. [Accepted result 034](./results/034-p1m1a-canonical-key-causal-null-4of4.md): `mechanism-preflight-complete`, 4/4, zero errors, 3008 canonical keys, 24064 accepted base rays, 24068 with any intervention; N004 hit mismatch=0, original M0 lookup key SHA all matched. **ALL 3 calibration C3 keys yielded 0 additional 16-bit radiance and zero changed RGB pixels/channels, exact same PFM SHA `2309b06c...` as control**. Zero(0 consumers): baseline/extra 0/0; Low(93 consumers): 0/0; High(875 consumers): 10/0 (integer per-output mean 1→1). For any common fixed reference `RMS(control,ref)-RMS(candidate,ref)=exact 0`. No signed quality improvement, predictor or P2 GO.

P1m1a serial single-invocation key search measured 619.016/633.604/627.753 µs respectively, **not deployable** and NOT an estimate of marginal traversal cost. The cause of 12/12 zero extra contributions remains undetermined: extra rays may miss or hit surfaces with dark/rounded-zero shading.

**Next phase P1m1c** source-frozen in [experiment 025](./experiments/025-p1m1c-ray-hit-vs-zero-energy-audit.md): N006-only postframe CPU readback from existing GPU hit buffer, classify per-ray hits/misses, base+extra positive contributions and hit-with-zero-radiance; no new shading/traversal shader, same 3 keys and immutable directions, same exact baseline/three null PFM image SHA mandatory, fail-closed. New result summary distinct from frozen M1a, 4 separately warmed cases; **GPU outcome pending**. One exact command:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1c_ray_fate.sh
```

Upload `out/research/n006-interval-aware-allocation/p1m1c-ray-fate-static-c3/<UTC>/n006-p1m1c-ray-fate-summary.json`. Then choose prospective sampling improvements on separate calibration/evaluation keys or halt if no causal quality signal. Reference-independent 0 signed RMS proof remains limited to the three current frozen identical images. No PR / GitHub Actions; Issue #42 OPEN.

---

# 2026-10-11 LATEST — M1a GPU 1/4 (control PASS), zero postframe diagnostic gate false (source fix pushed)

User-uploaded `n006-p1m1a-canonical-key-pilot-summary.json` raw SHA256 `7b9fd8cca73a4764f796ebe8f086595c7086caf5c9cda1a6fb6dc7c7929cc9dd`, GPU Radeon 8060S RADV, original branch HEAD `6f37f288821545082a93463620142f0575cda5d1`. M1a output `status=invalid-retained`, one verified case (control), one zero failure. Control exact accepted HDR SHA `2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e`, 3008 canonical outputs / 24064 rays, zero N004 mismatches, no extra rays. Zero intervention GPU render and CPU/GPU hit oracles completed (0/0/0) then independent postframe coverage `P1m0 requires finished Lane-E-final software canonical lean-hash frame` aborted; no Zero candidate evidence labels serialized. Low/High NOT run.

**Source root cause**: canonical prefix validation `result.stats.work_items == result.stats.outputs * rays_per_probe` did not allow the deliberately appended 4-ray tail. It made `extra.base_prefix_correct` false, `state_->last_canonical_frame` false and M0 postframe guard abort. **Corrected** to require exact base rays = `outputs*8`, overall work = `outputs*8+(m1?4:0)`, extra work = `m1?4:0`, keeping all per-work original identity/direction, uniqueness, owner and 8+4 contribution checks. Regression test added. See [result 033](./results/033-p1m1a-first-gpu-zero-postframe-guard-failure.md).

**Next exact same command; no need to rerun M0b/C0/B1:**
```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1a_canonical_pilot.sh
```

Four frozen isolated cases Control/Zero/Low/High, 32+8 warmups each; upload `out/research/n006-interval-aware-allocation/p1m1a-canonical-key-pilot/<UTC>/n006-p1m1a-canonical-key-pilot-summary.json`. **Fix not locally recompiled or rerun on user's GPU yet**. Do NOT claim even Zero causal frame passed, P1 quality improvement, or P2 scheduling. If 4/4 mechanism PASS, next independent converged reference and signed quality according to frozen [024](./experiments/024-p1m1b-independent-reference-signed-gain-protocol.md). No PR or GitHub Actions.

---

# 2026-10-11 newest: first M1a attempt stopped by obsolete M0b static source assertion (fixed)

User pasted **successful M1a SPIR-V/C++ build/link**, `222` N006 unit tests with **one failure** at `test_p1m0_consumer_coverage.py:133`: assertion still searched for the old literal `request.p1m0_pretrace_coverage ? 22U`; M1a deliberately changed it to a two-arm query-count guard with `|| request.p1m1_canonical_key_intervention`. Updated test to verify *both* arms by whitespace-tolerant regex; no production shader/runtime changed in this fix. Shell `set -e` stopped **before M1a GPU execution**. [Result 032](./results/032-p1m1a-first-build-and-static-test-regression.md). Original P1m0b accepted 5/5 remains valid. Next exactly same command:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1a_canonical_pilot.sh
```

Still awaiting **4/4** M1a causal mechanism GPU samples, no signed quality labels, no P1 ranking or P2 scheduler decision. No PR / GitHub Actions.

---

# LATEST 2026-10-11 — P1m0b 5/5 PASS; P1m1a canonical key+4 ray PRE-FLIGHT CODE READY (not GPU-proven)

Immutable user-upload M0b `n006-p1m0-consumer-coverage-summary(2).json`, SHA256 `d7774a3e4fee8c9a103a7529979d7303ad865d05878143e4522232b8ef14affd`, clean executed HEAD `359e6b87fe38919349b994136005251187137b4b`, AMD Radeon 8060S RADV: five of five full-slot/stats GPU parities and matched exact M0 per-key hashes. Pre-secondary GPU pass cost static/camera/light/moving/deforming **21.280/14.387/14.868/22.683/20.439 µs**, only **0.82–1.37%** measured instrumented GI on these five scenes, all below prospectively frozen caps; scratch **131104 B**. [Result 031](./results/031-p1m0b-presecondary-gpu-cost-pass.md). **P1m0b PASS only for feasibility**; no signed marginal gain or P2 scheduler GO.

**Next study P1m1a**, source frozen in [023](./experiments/023-p1m1a-single-canonical-key-extraray-preflight.md) before GPU:
- control original canonical 8-ray stream + separate P1m0 postframe coverage diagnostics, correct SHA HDR and N004 primary oracle.
- three *single-key* independent 32+8-warmed SW/static/C3 interventions on M0 calibration keys, zero token `3221225474` (0 consumer pixels, 3 producer owners), low `3223322625` (93 pixels, 3 owners), high `3223324678` (875 pixels, 125 owners).
- N006-only shader `n006_p1m1_canonical_key_extra.comp.glsl` scans canonical compact output prefix (correctness preflight, not efficient P2 scheduler), appends deterministic **P1a-identical +4 direction** work items at ray indices 8–11 to *one* canonical output. Original first 8×canonical rays untouched, counter work +4, output count unchanged; finalize updates indirect dispatch; merge accumulates 8+4 contributions, accepted storage update rounds 12, N006 canonical weight shader restores owner count.
- New runtime sampled GPU stats, verifies canonical output/key, exact canonical base prefix, 4 extra IDs/directions/target metadata, integer 8+4 accumulated values and mean, owner-weight restore; CLI whitelist only three fixed static/C3 keys, rejects pretrace overlap. Runner compares PFM control accepted SHA, all 4 target hit/oracle/owner counts, M0 per-key hashes unchanged, per-case PFM changed pixel/channel values (UNSIGNED influence, **NOT** HDR quality), retains 0-difference outcomes. New static unit tests added, CMake builds separate shader only for N006. **GPU compilation and correctness not yet independently verified**. No accepted N001/N003/E003 shader changes.
- One batch after checkout fast-forward:
```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1a_canonical_pilot.sh
```
- Expected summary `out/research/n006-interval-aware-allocation/p1m1a-canonical-key-pilot/<UTC>/n006-p1m1a-canonical-key-pilot-summary.json`. If build fails, fix at offending file; if GPU fails, retain stdout/stderr and report. If preflight 4/4 PASS, only then M1b independent converged HDR reference, calibrated variance and prospective signed marginal gain test; DO NOT treat changed pixel count as benefit or attempt P2. Issue #42 stays OPEN, no PR, no GitHub Actions.

**Post-P1m1a signed-quality methodology is already frozen** in [experiment 024](./experiments/024-p1m1b-independent-reference-signed-gain-protocol.md): same independently converged control HDR reference for all calibration interventions, signed global RGB RMS with repeat/reference uncertainty, later truly distinct evaluation/holdout trajectories. Do not tune quality thresholds or claim gain from unsiged PFM pixel diffs.

---

## 2026-10-11 P1m0b target GPU PASS (newest)

User uploaded `n006-p1m0-consumer-coverage-summary(2).json`, SHA256 `d7774a3e4fee8c9a103a7529979d7303ad865d05878143e4522232b8ef14affd`, clean HEAD `359e6b87fe38919349b994136005251187137b4b`. Five frozen software scenes COMPLETE, zero failures. In-frame before-secondary count and independent postframe GPU count matched **every slot of 32768 values and all 8 counters**, all old M0 per-key SHA fingerprints matched, accepted HDR PFM and N004 gate intact. GPU timestamp pretrace clear+dispatch+barriers **21.280/14.387/14.868/22.683/20.439 µs** for static/camera/light/moving/deforming, respectively, **0.82–1.37%** of instrumented GI, 131104-byte scratch. All five passed predeclared cost cap `min(10% of instrumented complete GI, 50% of traversal)`. C0 source provenance still MATCHED. [Result 031](./results/031-p1m0b-presecondary-gpu-cost-pass.md).

**P1m0b GO (feasibility only)**. This does NOT establish signed HDR gain or predictive ranking. Canonical-key +4-ray intervention P1m1 is next. Keep one-key contrast, frozen M0 calibration strata and independent reference; no P2 scheduler claim. Need user GPU evidence for next phase; do not rerun B1/C0/M0/M0b; no PR or GitHub Actions.


---

# 2026-10-11 LATEST — M0 5/5 accepted; P1m0b pretrace cost proof implementation added (awaiting real GPU)

**User uploaded** `n006-p1m0-consumer-coverage-summary(1).json`, raw upload SHA `f355b7202e52127b044120ac8406e5dba4626dd88f4cf29a78f16abbc2c66cec`, clean executed HEAD `8a5cb251384ba14deb6c158057583fcd8214e335`, AMD Radeon 8060S RADV, exact Sponza SHA. Protocol `n006-p1m0-consumer-coverage-five-scenes-v1`, `status=complete`, **5/5 cases PASS**, failures none. M0 is DIAGNOSTIC ONLY and ran GPU consumer counting *after* the normal frame; accepted image and hit byte parity, N004 hit sampled, owner/cardinality count closure, exact per-cascade zero/positive stats, no invalid/overflow. Frozen [research result 030](./results/030-p1m0-five-scene-coverage-pass.md).

| scene | canonical keys | matched/consumed keys | matched pixel-cascade lookups | cascade-3 matches |
|---|---:|---:|---:|---:|
| static | 3008 | 100 | 11400 | 9626 |
| camera-motion | 3220 | 42 | 12437 | 11354 |
| light-motion | 3008 | 100 | 11400 | 9626 |
| moving-rigid | 3104 | 38 | 11032 | 10353 |
| deforming-control | 3029 | 100 | 11403 | 9628 |

**Interpretation:** only 1.22–3.32% of canonical key set is referenced by valid screen-pixel composite in one frame; 84.4–93.8% of *successful lookup attempts* are cascade-3. **Not** proof of image error/extra-ray utility, storage success, global/temporal key usefulness or a throughput speedup. Prospective M1 calibration-only manifest complete **60 keys** = 5×4×(zero,min-positive,max-positive), no missing strata; no signed gain labels.

**Next independently required feasibility test P1m0b**: pretrace cost/placement and frame parity. Prospective protocol [022](./experiments/022-p1m0b-presecondary-coverage-cost.md) locks opt-in same M0 GLSL after *primary visibility + canonical hash/compact*, before secondary ray conversion/tracing. New request/CLI `--p1m0-pretrace-coverage`, constructor-only scratch allocation, full GPU slot byte/stat comparison against independent after-frame M0 pass, +131104 requested scratch bytes, disjoint existing Vulkan query indices20/21 for clear+count+barriers (pool24 queries), original 0..19 retained. In-renderer measured `ray_prepare_gpu`/`complete_gi_gpu` now INCLUDES diagnostic and must not be called prior uninstrumented baseline. Cost preregistered pass iff `C <= min(0.1*instrumented complete_gi,0.5*instrumented traversal)` **for all five**; failed cost persists without post-hoc relaxation. Frozen M0 per-key SHA/matched count checked per scene. No extra rays/quality labels.

**Ready one-batch user command** (do NOT need to rerun B1a/B1c/C0 or original postframe M0):

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m0b_pretrace.sh
```

Outputs `out/research/n006-interval-aware-allocation/p1m0b-pretrace-coverage-five-scenes/<UTC>/n006-p1m0-consumer-coverage-summary.json`. This runs build, full N006 tests, then 5 SW scene pretrace GPU passes with independent postframe parity/accepted HDR SHA/oracle. **No local build or GPU verification yet** of new code. If failure, inspect streamed last `[P1m0-stage]`/`[P1m0-GPU]` log. If five valid and cost gate PASS, proceed to new N006-only *canonical key +4 rays* causal intervention without reusing old owner-target stage, independent converged HDR reference, signed global RGB RMS gains, holdout; **do not declare P1 or P2 achieved**. If cost gate failed, label P1m0b rejection, design a prospectively lower-cost way to obtain the signal before attempting scheduler P2. No PR, no GitHub Actions, original accepted N001/N003/E003 untouched.

---

# 2026-10-11 latest second rerun — M0 static GPU 600s timeout; root candidate repaired, trace streamed

User-uploaded `n006-p1m0-consumer-coverage-summary.json` from clean HEAD `bd4aae067cb51a6729d06ee885c884bf63c46ba5`:

- Runner `status=invalid-retained`, **0/5 cases**, first `static` child `P1m0 static exceeded 600s`; 32 source/8 target warmups, AMD Radeon 8060S. Actual full child stdout/stderr not supplied. Source [029 result](./results/029-p1m0-first-gpu-timeout-and-diagnostic-repair.md); no successful P1m0 GPU coverage data.
- Prior C0 static source→runtime SPV `MATCHED`, 210 original N006 unit tests `OK`, float32 rounding risk as previous; **do not treat repeated identical outputs as new independent GPU performance data**.
- Important **new source root-cause candidate**: P1m0's `p1l_sampled_hit` was false, so **eight target warmup frames each ran the expensive N004 CPU primary hit oracle**, whereas earlier accepted B0 used sampled-fast once on the target. Fixed by opt-in `|| p1m0_coverage` to existing sampled-fast gate. Retains `frame_core_correct` and strict frame count/stability on all warmups plus **full N004 CPU hit oracle for the single measured target**. The **precise stall location remains unproven without child stderr**; other causes possible.
- To make a further long stall diagnosable, C++ main now flushes `[P1m0-stage]` around runtime construction, source warmups, target warmups, target render, target hit-oracle, PFM and diagnostic; C++ GPU method flushes `[P1m0-GPU]` around pre/post readbacks, scratch upload, pipeline, GPU submission/fence wait and GPU counter audit. Python runner streams child stdout/stderr live into timestamped files instead of delaying writing until child exits; timeout/exit error includes absolute path + stderr/stdout tail, stored in `n006-p1m0-consumer-coverage-summary.json`. Existing 600s cap preserved; **never increase it without discovering the stage**.
- Tests added for sampled-fast M0 behavior, stage probes and log retention. E003 C0 success log no longer says `(blocked evidence retained)` when exit=0. **These changes are pushed, but neither compilation nor GPU outcome verified by user's next run.**

Next single batch same as before:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_next_verified.sh
```

If it fails again, last `[P1m0-stage]` or `[P1m0-GPU]` line from newly streamed stderr/error text identifies the stopped stage and permits targeted fix. If all 5 pass, inspect exact key/owner/consumer conservation, 60-key frozen M1 calibration manifest, independent costs and quality intervention prereqs. **No predictor claim, no P2 GO, no Actions, no PR.**

---

# 2026-10-11 latest — 210 N006 tests PASS, E003 C0 static MATCHED, M0 static GPU exit 1 FIXED IN SOURCE (needs rerun)

User supplied stdout from one local `run_n006_next_verified.sh` execution:
- `Ran 210 tests in 0.417s OK`: unit tests at prior HEAD passed.
- B1c rejected variants' static compiler histogram: B1a +1136 SPV bytes/+61 instructions/+18 OpLoad/+1 conditional branch; B1c +1100 bytes/+74 instructions/+16 OpLoad/+3 branches, versus original. **No candidate GPU speedup.**
- CPU float32 direct-division/reciprocal numerical risk: 51,445/200,000 different f32 entries, constructed boundary difference. Synthetic only.
- E003 C0 `status=ready_static_only`, `provenance=MATCHED`; both original E003 static rebuild and active runtime-named binary SHA matched. Original **36,072 SPV bytes / 7 static OpFDiv**, B0 instrumentation **38,404 bytes / 7 OpFDiv**. C0 active binary provenance blocker CLOSED for this local environment; **GPU hotpath gain unproven**, no E003 C1 intervention warranted yet. Record: [028](./results/028-p1l-c0-static-spv-provenance-pass.md).
- P1m0 first case `[P1m0] static (1/5)` renderer **exit 1**, user couldn't locate `stderr.log`. Existing runner had actually saved it under `out/research/n006-interval-aware-allocation/p1m0-consumer-coverage-five-scenes/<UTC>/static/stderr.log`, but printed just basename and no child output. No GPU M0 result can be accepted from this failed run.
- Deterministic C++ source bug identified: P1m0 was admitted in CLI gate but **target warmup had the P1h deforming-only 4172-owner hardcoded condition**, whereas static has accepted 4167 owners. C++ fixed both dynamic count and stabilization checks by `const bool scenario_counted_target = p1l_stage_any || p1m0_coverage;`. This preserves original P1h fallback and uses existing P1l per-scene dynamic contract for M0. New Python static regression test added. Runner now prints absolute timestamped evidence root/stdout/stderr paths and last 6,000 characters of subprocess error inline, persists failure summary with absolute paths. **Rerun pending; precise prior fault location not proven without stderr.**

Already prepared parent lane P1m1: deterministic zero/min-positive/max-positive key selection per cascade×5 scenes (60 expected) in M0 JSON, **calibration only**; no signed reference-quality predictions or P2 scheduler yet.

Single user rerun; no manual file edits, do not repeat already-rejected GPU campaigns:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_next_verified.sh
```

If still failed, new script prints exact `stderr` location and renderer's terminal error directly. If 5/5 succeeds, upload `.../p1m0-consumer-coverage-five-scenes/*/n006-p1m0-consumer-coverage-summary.json` (contains calibration-only selector, PFM SHA and provenance). Reuse C0/B1c results; no repeated post-hoc optimization. Next research conditional: cost the pre-secondary consumer pass and test canonical-key +4 marginal quality versus independent reference before P2. The child failure is *not* N006 closure. GitHub only branch direct push, no PR/Actions.

---

# 2026-10-11 follow-up — local build PASS, test harness repair + prospective M1 calibration strata

**Read before older handoff notes.** User-provided N006 full batch log stopped after compilation: C++ link PASS, 206 Python unit tests ran with exactly **3 failures**, all in `test_p1m0_consumer_coverage.py`. Failing assertions:
- `compact()` had `re.sub(r"\\\\s+", ...)` (searched for a literal backslash sequence rather than actual whitespace); corrected to `re.sub(r"\\s+", ...)`. The *actual* N001, N003 SOFTWARE and M0 shader view-direction/position/key formulas were rechecked with whitespace normalization and source expressions match.
- CLI gate assertion expected three `!p1m0_coverage` occurrences, but actual three gates are **two negated guards plus one positive allowlist**. Test now verifies both negative guards and positive gate explicitly instead of the wrong count.

Fix was pushed in `070a720695c13f8e2cb37dfef25abf0f261d3350`. **No user 206-test rerun or GPU result has been supplied yet**. Do not mark test PASS from source review alone. C++ warning about anonymous-namespace field linkage and unused helper was pre-existing, not the test failure.

**While awaiting real GPU evidence, continued prospectively with M1 calibration selection:** `experiments/021` now freezes exactly one sorted-smallest token for each 5 scenes ×4 cascades ×3 coverage classes: `zero` count, lowest **positive** count, highest **positive** count. All ties smallest canonical token. Missing zero/positive or collapsed low/high coverage classes => `incomplete_strata_no_intervention`, not silently substituted and no quality scheduler GO. New pure `p1m1_calibration_selection.py` and `test_p1m1_calibration_selection.py` added; `run_p1m0_consumer_coverage.py` now adds selections + per-case provenance and an aggregate `m1_calibration_only_key_status` + count (60 expected) to **the same M0 summary**, eliminating need to upload every raw per-key file to choose calibration keys. This is *not* P1 prediction, not a marginal quality measurement and does not authorize M1 GPU interventions before M0 correctness/cost proof.

**User command unchanged (one batch; no manual edits):**

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_next_verified.sh
```

The first `git pull --ff-only` fetches test repair and the frozen M1 selection. This command runs build, all N006 tests, B1c static shader audit, synthetic float32 risk audit, E003-C0 active-binary provenance audit and independent five-scene M0 GPU coverage. If E003 C0 blocked, M0 still runs; final shell exits nonzero to preserve provenance gate. Need user output: `n006-p1m0-consumer-coverage-summary.json`, `p1l-c0-e003-static-audit.json`, `b1c-spv-audit.json` or first failure. On M0 5/5 PASS, evaluate per-cascade coverage conservation and selection; then continue to pretrace cost, causal key +4 ray and independent reference studies. **Do not stop merely to report progress if another non-GPU prep stage can be completed.** No PR / Actions / historical shader edits.

---

# 2026-10-11 latest — N006 E003-C0 static gate + P1m0 five-scene diagnostic prepared, NOT GPU-verified

**Read this first.** Previous handoffs below are historical. Private repo `owoDra/phos-gi-lab`, branch `research-n006-interval-aware-allocation`, Issue #42 OPEN. **Continue GitHub work without confirmations; push directly; never PR/Actions.** Actual AMD Radeon 8060S (RADV STRIX_HALO) hardware must run local GPU experiments. Previous supplied P1l-B1c GPU summary was accepted as REJECT, not a research-lane close; B1a GPU REJECT, B1b GPU work counts reduced with no speed gain proved. Result [025](./results/025-p1l-b1c-packed-axis-performance-reject.md).

## Evidence/work completed THIS session (no new AMD GPU test)

1. E003 quantized secondary software traversal source/layout [result 026](./results/026-p1l-c0a-e003-source-layout-audit.md): B003GpuQuantNode 176 bytes with eight 16-byte child records and 48-byte header; up to 8 children/node, 64-stack, slab-division source and preexisting direction sorting. B0 primary work previously ~25.5–26.3 AABB tests/secondary ray; do **not** equate counts to GPU execution. **C0** [protocol 019](./experiments/019-p1l-c0-e003-wide-child-cost-audit.md) builds untouched E003 source into N006-specific `n006_p1l_c0_e003_source_rebuild.spv` then compares SHA to active `e003_instance_quantized.spv`, which current CMake did NOT explicitly declare. Missing/mismatch is `blocked` JSON + nonzero status; NO E003 C1 or arithmetic rewrite on that evidence.
2. E003 numerical [result 027](./results/027-p1l-c0b-f32-slab-rounding-risk.md): deterministic synthetic CPU IEEE float32 `f32((mn-o)/d)` vs `f32((mn-o)*f32(1/d))` disagreed on 51,445/200,000 samples and a constructed ray/AABB slab accept/reject boundary. **NOT** GPU compiler output, performance or sampled real workload. Script `audit_p1l_c0_division_rounding.py` and tests. Rejected algebraic exactness assumption, not the entire E003 research.
3. New prospective original-lane [experiment 020](./experiments/020-p1m0-probe-consumer-coverage.md) (P1m0 M0) is a GPU probe-lookup consumer coverage diagnostic. Original N003 software composite computes `probe=floor((primary-hit-world-position-scene_origin)/cascade_spacing)` on every valid pixel × cascade then probes storage key `(probe,cascade)`. N006 canonical hash already indexes unique producer `(probe,cascade)`. Thus potential pre-secondary feature is **count of valid primary pixel lookups of each canonical key**, including zero-consumer keys. This is **not marginal quality gain, nor necessarily a successful storage read**. Previous P1a owner-local interventions did not make measurable global quality (11/12 exact 0, one tiny gain), P1b shared-key storage dilution; P1c 81.85% base ray duplication, later canonical dedup GPU benefit.
4. New source: `shaders/research/n006_interval_aware_allocation/n006_p1m0_consumer_coverage.comp.glsl` with private 32768 uint32 counters, 8 stats, readonly primary-hit/canonical-key SSBO, source-exact N003/N001 composite key expression and bounded hash lookup. `N006Runtime::p1m0_consumer_coverage()` in N006 runtime cpp/hpp allocates isolated buffers, dispatches **AFTER completed accepted frame timestamps**, saves original primary hit/image bytes then verifies unchanged afterward, captures per-key sorted token/consumer/producer-multiplicity and fail-closes count conservation. N006 CLI `--p1m0-consumer-coverage` requires exactly one lean-copyback SOFTWARE canonical target frame with 32+8 warmups and current zero-extra mode; returns per-key JSON. Python runner `run_p1m0_consumer_coverage.py` checks 5 accepted image SHA, hash/owner/secondary stage invariants (reuses `run_p1l_a1b_sampled_hit.validate_frame`), counted valid pixels×4 match/absent/invalid, sorted full key set, multiplicity sum, by-cascade counts; 600s/process. Tests `test_p1m0_consumer_coverage.py` and `test_run_p1m0_consumer_coverage.py`. All actual GPU/compiler/C++ builds **UNEXECUTED here**; don't claim PASS until upload.
5. [Experiment 021](./experiments/021-p1m1-canonical-probe-marginal-value-design.md) conditionally defines next P1m1: only after M0 correctness and pre-secondary cost proof, inject canonical output +4 deterministic rays and measure **signed reference-image quality gains** by coverage classes, including zero and negative labels, distinct trajectories/calibration/holdout and variable ray normalization; **no P2 scheduler until prospective P1 predictive gate**. Original N006 Issue #42 research objective remains unresolved.

## Next exact physical experiment (one batch)

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_next_verified.sh
```

Script will check clean branch, `git pull --ff-only`, `mise run build`, full N006 Python tests, **static-only** B1c SPIR-V report (no rejected GPU rerun), the CPU float32 risk audit, C0 E003 compiled-source binary gate, **then independent** P1m0 five-scene one-frame GPU consumer diagnostic. It intentionally continues to M0 even if C0 is `blocked`; those are scientifically independent but C0 gate remains closed and final shell exits nonzero to mark unresolved E003 provenance. Outputs:
- `out/research/n006-interval-aware-allocation/p1m0-consumer-coverage-five-scenes/<UTC>/n006-p1m0-consumer-coverage-summary.json`
- `out/research/n006-interval-aware-allocation/p1l-c0-e003-static-audit.json`
- `out/research/n006-interval-aware-allocation/b1c-spv-audit.json`
- `out/research/n006-interval-aware-allocation/p1l-c0-floating-divide-risk.json`

Upon new uploaded evidence: **continue autonomously** auditing five cases and if M0 PASS launch P1m1 implementation gates (prospectively freeze *numeric* thresholds/reference split before results) while separately deciding C0 E003 candidate only if compiled SPIR-V and active shader provenance match. If GPU fails, fix branch issues via GitHub without telling user to manually edit code; only ask a new single GPU command when needed. No PR/GitHub Actions. End of lane requires P1/P2 predictive decision or explicit justified STOP, **not** ancillary BVH optimization alone.

---

# 2026-10-11 latest — B1c GPU REJECT; E003 C0 source/SPIR-V provenance audit prepared

**Read this update first.** Previous B1c pre-run handoff below is historical, **not an instruction to rerun B1c**.

- B1c actual GPU matched results: uploaded `n006-p1l-b1c-summary.json` SHA256 `49b561e6e1daffeb611d1571daa8236a76a0f5328902ed0d1b656e8af59fe11e`, clean measured `11eaabfa7666c41cdda84a679caae62d9a031711`, AMD Radeon 8060S RADV, `complete`, `matched`, `formal=false`, `failures=[]`; **15/15 processes, 360 byte/image-equal target frames, 180/180 paired samples**. User supplied summary with embedded pairs, not all raw per-process PFM/JSON files. The run reports sampled CPU oracle on candidate frame 1 of each process, no independent reference.
- Frozen threshold [experiment 018](./experiments/018-p1l-b1c-packed-axis-proxy.md): **B1c REJECT**; only static 1/5 primary wins, need ≥3; light-motion complete renderer regresses +5.237% > allowed +3%. Other scenes do not pass primary ≥5%/≥24 of 36 pairs/≥2 of 3 process medians. [Result 025](./results/025-p1l-b1c-packed-axis-performance-reject.md) has all scene-level evidence including CPU metadata packing time and AB/BA order effects. B1a also REJECT and B1b work-count result PASS-only remain immutable.
- **Do not run B1c again** or add more N003 primary child-order heuristics without new grounded evidence. Do not adopt B1c into accepted shaders. B1c's static `b1c-spv-audit.json` was **not supplied**, so any compiler/memory traffic causal claim remains unsupported.
- Source-only independent **E003 secondary quantized wide-child audit C0** now active. Prospective [experiment 019](./experiments/019-p1l-c0-e003-wide-child-cost-audit.md), script `scripts/research/n006_interval_aware_allocation/audit_p1l_c0_e003_spirv.py`, test `test_audit_p1l_c0_e003_spirv.py`. Counts inherited from validated B0 result 021: 25.53–26.30 child AABB tests/actual ray, 6.72–7.00 wide nodes, ~3.4 hash probes/ray. The accepted E003 shader has quantized child unpack and 3-axis `ray_aabb_bounds` division per valid child in source. Static operation counts alone are **not** proof of dynamic GPU cost.
- **New reproducibility finding:** no CMake rule generates `e003_instance_quantized.spv` even though accepted runtime opens it. N006 C0 now rebuilds **unchanged** E003 source to isolated `n006_p1l_c0_e003_source_rebuild.spv` and checks against actual in-use binary SHA. If missing/different, C0 fails and must resolve provenance before analysis or new GPU performance runs. No original E003/N003 shader sources were changed.
- C0 needs configured shader compiler artifacts from NixOS for authoritative compiler/version/disassembly; no C0 report or new GPU result yet. Do not request repeat B0/B1b/B1c. Once C0 is validated, select **one** E003 low-overhead falsifiable hypothesis or document C0 NO-GO, prospectively freeze C1 correctness/timing protocol before implementation. GPU runs only after this. No CI/Actions, no PR; commit directly to `research-n006-interval-aware-allocation`. Parent Issue #42 predictive marginal-value P1/P2 **unresolved**.

---

# 2026-10-11 continuation — P1l-B1c prepared for first GPU evidence

**This section supersedes the old pre-B1c next-action description below.** Repo `owoDra/phos-gi-lab`, branch `research-n006-interval-aware-allocation`, Issue #42. The original Oct 10 B1b five-scene result remains the **latest accepted scientific GPU evidence** (B1b 5/5 work-count PASS; B1a 15-process GPU performance REJECT). This session continued the work: no repeat of the previous measurements.

- Frozen **before implementation**: `experiments/018-p1l-b1c-packed-axis-proxy.md` (commit `f19b36b`).
- Opt-in B1c implementation: `e01ae744f51edd8881695192fb1ea42278d06be4`. It uses existing `GpuBvhNode.data[2]` internal-node metadata (48B unchanged) for precomputed child center separation axis/sign; shader decides order from ray direction without B1a's additional two child-node loads. Leaves and accepted shader sources unchanged. This is not B1a's full 3D near-first, nor guaranteed faster.
- New N006 files: `src/research/n006_interval_aware_allocation/n006_primary_axis_proxy.hpp`, `shaders/research/n006_interval_aware_allocation/n006_p1l_b1c_primary_axis_proxy.comp.glsl`, `scripts/research/n006_interval_aware_allocation/audit_p1l_b1c_spirv.py`, `test_n006_axis_pack.py`, `test_run_p1l_b1c_axis_proxy.py`, `test_audit_p1l_b1c_spirv.py`, `run_p1l_b1c_verified.sh`. C++ runtime/CLI/CMake and B1a runner opt-in extended without changing N003/E003/N004/N005 accepted shaders.
- Independent C++20 CPU helper smoke **PASS** in the assistant sandbox, source SHA matched remote blob `6e9e0dfb`. Not a full project build. No actual B1c SPIR-V binary comparison, whole-project unit suite, target GPU timing, reference-quality comparison or HWRT-unavailable GPU evidence yet. **No speedup claim**. CPU metadata packing is separately counted; do not mistake GPU stage time for CPU+GPU frame time.
- **Only remaining necessary external action for this experiment:** On the NixOS AMD RADV machine, `git switch research-n006-interval-aware-allocation && bash scripts/research/n006_interval_aware_allocation/run_p1l_b1c_verified.sh`. The script builds, unit-tests, emits offline SPIR-V audit, runs frozen 5-scene GPU correctness preflight, and runs matched 15-process GPU performance **only if preflight passed**. If it fails, report first failure without forcing further runs.
- Collect `out/research/n006-interval-aware-allocation/b1c-spv-audit.json` and the latest `p1l-b1c-matched/.../n006-p1l-b1c-summary.json` (or preflight / build error). Apply fixed ≥5% primary/24-of-36-pairs/2-of-3-processes in ≥3 scenes; full renderer ≤+3% each scene, plus CPU packing/memory/build update and correctness. If failed, record REJECT, pivot to E003 quantized secondary child AABB; no repeat or cherry-pick.
- **N006 P1/P2 predictive ray allocation remains unvalidated**. Do not close Issue #42. Direct research commits (no PR), no CI/GitHub Actions. Read the old handoff below as immutable historical detail only.

---

# N006 GPU GI research — Next-session handoff (2026-10-10, after P1l-B1b)

> **Read this first in the next session.** This handoff is a durable GitHub file, not a running automation. The user explicitly wants the **next research to be done next session**, not now. Do not ask stage-by-stage permission after continuing: finish all repository-side investigation/code/tests you can, then request the **minimum** hardware-only NixOS GPU execution, with one end-to-end command where possible.

## 1. Repository, branch, collaboration contract

- GitHub repository: **`owoDra/phos-gi-lab`**, Issue **[#42](https://github.com/owoDra/phos-gi-lab/issues/42)**, working branch **`research-n006-interval-aware-allocation`**. Read the latest remote branch/Issue on resumption; its HEAD will differ from the measured B1b HEAD after writing this results/handoff document. **Do not assume an earlier SHA is the current HEAD**.
- B1b measurement was made from clean **`b4f0a8bffc78612f69b78f7ca5ec2be0c8560659`**. Its analysis is now recorded at **`research/lanes/n006-interval-aware-allocation/results/024-p1l-b1b-five-scene-near-first-work-reduction.md`**. This file is the latest accepted scientific result, **not** a new performance optimization.
- N006 research commits go **directly to this research branch, no PR required**. Do **not** add GitHub Actions or CI (the user expressly forbids them). Do not mutate N004/N005 and earlier accepted production/baseline shaders or rewrite historical result files. Keep tests, experiment protocol, docs/README and Issue #42 in sync with commits.
- Target GPU: **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**, NixOS 26.05, Vulkan, Sponza `assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf`. Scene SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. `mise run build` and `mise exec -- python ...` are the existing entry points.
- Research target is **HWRT-free software dynamic GI that approaches or beats hardware ray tracing without brute-force increasing ray count/memory/compute**. GPU timestamp is the primary performance source; wall time diagnostic only. N006 Issue #42's predictive interval-aware marginal-value allocation P1/P2 **still has not been validated** and must not be conflated with this software BVH study.
- GitHub connector can inspect/edit/commit repository files. **It cannot access the user's local AMD GPU to execute Vulkan**; honestly distinguish coding/source audit from actual GPU evidence. Never invent GPU timings or pretend to have executed the target hardware.

## 2. Exact current status — B1b **COMPLETE, 5/5 PASS**

The user uploaded **`n006-p1l-b1b-counts-summary.json`**; file SHA-256 **`9c6bb80ee45d09de028228b9ba0a6e0a05dfab9b8292d4dbe2e22ba217284662`**. Protocol `n006-p1l-b1b-paired-primary-counts-v1`, `mode=five-scenes`, `status=complete`, `failures=[]`, `formal=false`, `instrumented_timing_valid=false`. Independent **5/5 Lane-E-final SOFTWARE scenario processes** passed: light-motion, camera-motion, static, moving-rigid, deforming-control. Each case started from 32 source +8 target-state warmups, one original canonical lean-copyback target frame, one sampled N004 CPU ray-hit check.

All five original HDR images matched accepted backend-specific PFM SHA; both N006 primary count-only shader variants (fixed original order vs approximate near-first) wrote *separate* GPU primary hit buffers, and **each matched the original uninstrumented hit buffer byte-for-byte**; hit flags matched and **stack overflow 0**. No independently generated reference in this B1b, no test on hardware lacking HWRT. B1b is **mechanism/work-count analysis only; no candidate GPU time measured**.

### N003 software PRIMARY BVH — real measured traversal work

| Scene | Original node pops → near-first | Node count change | Original triangle tests → near-first | Triangle change |
|---|---:|---:|---:|---:|
| Static | 1,579,216 → 1,535,062 | **−2.80%** | 215,471 → 165,809 | **−23.05%** |
| Camera | 1,569,726 → 1,477,012 | **−5.91%** | 214,179 → 146,878 | **−31.42%** |
| Light | 1,579,216 → 1,535,062 | **−2.80%** | 215,471 → 165,809 | **−23.05%** |
| Moving rigid | 2,482,542 → 2,399,032 | **−3.36%** | 308,280 → 288,188 | **−6.52%** |
| Deforming | 1,617,954 → 1,581,890 | **−2.23%** | 222,507 → 172,811 | **−22.33%** |

**Critical interpretation:** B1a's ray-projected center child sort genuinely reduced both node visits and triangle intersections **in every tested scene**. This disproves the alternative hypothesis “B1a slows GPU because it failed to prune any work.” Yet node counts drop only ~2–6%, and **94–96% of screen pixels have unchanged node pops**; p99 node visits can *increase* (static/light 255→259, moving 301→307). No simple “less visits → faster GPU” correspondence.

### Previous B1a GPU performance study — irrevocably REJECTED

Prospectively frozen result `results/023-p1l-b1a-matched-near-first-reject.md`: **15/15 independent processes, 360/360 PFM and primary-hit byte-exact frames, 180/180 same-process ABBA pairs**. B1a candidate had this paired **primary GPU median % candidate−baseline**:

| Static | Camera | Light | Moving rigid | Deforming |
|---:|---:|---:|---:|---:|
| **−1.35%** | **+6.19%** | **+12.60%** | **+10.11%** | **+15.89%** |

**0/5 scenarios** passed the prospectively frozen ≥5% primary gain +≥24/36 faster pairs +≥2/3 winning process medians. **4/5 scenarios** regressed the complete renderer median by >+3%. Some time-dependent order interference/noise was present even with balanced AB/BA samples; it did not rescue the failed criteria. **B1a stays REJECTED. Never enable as default or merge the near-first code into the accepted N003 shader.** B1b does NOT reopen the performance decision.

## 3. Why work decreased yet GPU got slower — OPEN, NOT ALREADY PROVEN

Original N003 software-primary GLSL's binary node has `vec4 bounds_min; vec4 bounds_max; uvec4 data;` and LIFO stack order fixed as `push child x`, then `push child y`. Rejected B1a clone `shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl` reads **both child node bounds** at every internal node, computes two `center = (min+max)/2` and ray projections `dot(center − origin,direction)`, branches and pushes estimated far then near. B1b clone adds separate counters with the same traversal order.

Likely mechanisms worth *testing*, **not established causal facts**:
- **Extra child-node SSBO loads / cache or bandwidth pressure** and the additional dot, comparison and branch instructions are more expensive than the reduced triangle tests. Counts do **not** measure physical memory transactions, latency, register pressure or GPU occupancy.
- **SIMT wave divergence / instruction and register pressure**: node-pops p50 per screen pixel is 1; a small subset of expensive rays carries most visit reduction while p99 can worsen. The fastest raster/SIMT behavior may differ from aggregate scalar BVH work.
- **Measurement/clock and order interference**: B1a full study had substantially different AB vs BA primary paired distributions. Do not assume all slowdowns reflect shader instruction mix until independently isolated with controlled counters/repeats.
- **Approximate center-projection sorting is not exact near-entry sorting**, so pruning gains are workload-specific, modest and can trade against extra node fetches.

Neither B1b JSON nor earlier B1a timestamps alone can identify what share of the GPU slowdown is due to any of the above.

## 4. Next session research plan — continue autonomously

**Priority A — P1l-B1c: *bounded, measurement-first* cost attribution; do NOT immediately write another full experimental renderer variant.**

1. **Refresh branch HEAD, Issue #42, accepted evidence**: this handoff, `results/024`, `results/023`, `experiments/016` and `experiments/017`, and source files listed below. Verify latest state and clean research branch before changes. User has already provided B1b result; **do not ask them to rerun B1b**.
2. **Reproducible offline shader audit**: inspect how N003 and B1a compile into SPIR-V on the actual Nix toolchain: shader compiler version/options, exact SPIR-V lengths, `OpLoad`/branch/vector arithmetic instruction family counts and differences, and inspect binary node layout / existing GPU data generation. The assistant can implement scripts/tests/stat validators and push without waiting for user confirmation. SPIR-V instruction counts are STATIC compiler artifacts, **not per-ray executed instructions, GPU cache misses, occupancy or measured runtime**. If Vulkan physical profiler counters aren't accessible, explicitly mark them *unmeasured*.
3. **Choose a *single* falsifiable low-overhead candidate or a STOP for near-first** after the audit: e.g. a conservative precomputed node-order proxy/packed split axis if node format, geometry update and memory budget allow it; or a better caching/coalescing strategy that avoids **two additional child-node reads at every internal node**. Before any implementation, account for **BVH construction/rebuild/update cost** on rigid, deforming and topology churn and ensure no per-frame extra global sort. A source-level “cheaper near-first” is a hypothesis, not an accepted implementation. No extra shader-specific per-frame allocations and no hardware ray-query reliance.
4. **Freeze new B1c protocol before GPU results**: exact five-scene accepted HDR image SHA and GPU primary-hit byte parity, no overflow and same canonical ray/owner/hash/stage closure; smoke **light-motion + moving-rigid** (moving-rigid is mandatory because prior B1a strongly regressed), capped per-process runtime. If correct, balanced same-process repeated GPU-primary+whole-renderer timings and full memory/build/update accounting. Compare candidate and accepted ORIGINAL shader, **not** against rejected B1a as if it were baseline. Keep a strict renderer non-regression gate and predeclared primary improvement criterion. Don't cherry-pick one scene.
5. **If offline evidence says child-sort overhead cannot be reduced credibly**, document B1c `NO-GO` without burning another 15-process campaign. Shift to **E003 SOFTWARE secondary quantized wide-BVH traversal**: prior B0 found ~**25.5–26.3 child AABB tests per actual ray**, ~6.7–7 wide node pops, only ~3.4 spatial-hash probes and ~2.6 DDA cells. The E003 path is independent of N003 primary/any-hit shadow. Or investigate N003 conditional shadow-ray regimes (light 9,797 actual rays; static/deforming 251 but long >60 nodes/ray; camera/moving 0) with separate controls. Freeze a new experiment protocol before changing algorithms.
6. **Continue updating docs, results, Issue #42 and push research commits directly** as work proceeds; minimize redundant interactive handoffs and stop only at necessary actual user GPU execution, scientific final acceptance/rejection or actual unsupported access.

**Priority B — eventual larger research objective:** once HWRT-free Software is materially improved, reassess N006 predictive marginal-value allocation P1/P2. Existing sparse-hash+GPU visibility RC and HWRT acceleration remain accepted baselines; don't claim “HWRT obsolete” on single GPU or without hardware-absent test and dynamic/churn validation. Research as a whole **is NOT complete**.

## 5. Source map / reproducible paths

- Protocol: `research/lanes/n006-interval-aware-allocation/experiments/016-p1l-b1-primary-near-first-traversal.md` (frozen B1a performance), `experiments/017-p1l-b1b-near-first-pruning-attribution.md` (frozen B1b diagnostic).
- Accepted results: `results/019-p1l-a1b-hwrt-software-stage-isolation.md` (primary/secondary/composite GPU stage gaps), `results/020-p1l-b0-two-case-software-count-smoke.md`, `results/021-p1l-b0-five-scene-software-work-counts.md`, `results/022-p1l-b1a-five-scene-preflight.md`, `results/023-p1l-b1a-matched-near-first-reject.md`, **`results/024-p1l-b1b-five-scene-near-first-work-reduction.md`**.
- Source: `src/research/n006_interval_aware_allocation/n006_runtime.cpp`, `n006_runtime.hpp`, `n006_intervention_main.cpp`; `src/research/lane_n_end_to_end_renderer/n001_runtime.cpp` / `CMakeLists.txt`.
- Original baseline shader: `shaders/research/lane_n_end_to_end_renderer/n003_primary_software.comp.glsl`; rejected candidate shader: `shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl`.
- Accepted count-only probes: `shaders/research/n006_interval_aware_allocation/n006_p1l_primary_count.comp.glsl`, `n006_p1l_b1b_primary_near_first_count.comp.glsl`; runtime `N006Runtime::p1l_b1b_work_counts()`; one-step local runner `scripts/research/n006_interval_aware_allocation/run_p1l_b1b_verified.sh` (a successful B1b GPU result was uploaded; the exact invocation route is not known).
- Separate E003 software traversal: `shaders/research/lane_n_end_to_end_renderer/imported/lane_e_dynamic_geometry/e003_instance_quantized.comp.glsl`. **Do not confuse E003 secondary with N003 primary/shadow, or generic I001 binary BVH**.
- GitHub issue: [#42](https://github.com/owoDra/phos-gi-lab/issues/42). Prior exact measurement source `n006-p1l-b1b-counts-summary.json` attached in this ChatGPT session; report SHA above; re-upload only if raw per-pixel data beyond the committed summary is truly needed.

## 6. Copy into a new ChatGPT session

> [$github] `owoDra/phos-gi-lab` の `research-n006-interval-aware-allocation` を最新取得して、`research/lanes/n006-interval-aware-allocation/HANDOFF_NEXT_SESSION.md` を最初に読み、Issue #42、results/023 と results/024 を確認してください。B1b は全5シーンPASSで、近距離優先によりBVHノード訪問は2.2–5.9%、三角形判定は6.5–31.4%減った一方、180組のGPU比較でB1aはREJECTのままです。原因を未確定として、まずB1cの命令/追加子ノード読込の静的分析から始め、実験プロトコルを固定して継続してください。可能なGitHub作業は途中でいちいち止めず、PR・GitHub Actionsを作らず研究ブランチへ直接pushしてください。実機GPUが必要な時だけ一括実行コマンドを提示してください。
