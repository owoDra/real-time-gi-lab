# A6a full physical control and retained C7/C12 quality outcomes

2026-10-19 JST. **N010 NOT_READY.** Original145 thresholds are unchanged.
166 is explicitly **POST-HOC** quality replay of immutable captures, without
GPU recapture. Tests **NOT RUN**; scientific acquisitions/replays and retained
source/payload/resource identity checks only. No architecture promotion.

## A6a: four-seed analytical physical PASS

[492](492-compensated-full-a6a-seed3.json) is terminal native0, complete,
all_pass/seed_integrity_pass/terminal_identity_verified, and
**full_four_seed_physical_pass=true**. Together489–492 complete the original
four seeds,128x96/8192spp/81920 triangles. All1498 input/payload SHA256 entries
in492 were independently rechecked after terminal. Source commit
9c42fca0b019243d8bd0d7ddc43ee55a0727a30e; nativePID644484/start_ticks8104711/
session34570 is terminal. CPU5296.736632/elapsed5315.885398008992 seconds are
diagnostic; CPU31/nice15/one thread/7200CPU/10800elapsed/4GiB guards held.

| Pooled original analytical check | Actual | Unchanged rule |
| --- | ---: | --- |
| Direct geometric allowance |0 violations|No violation |
| Indirect relative error, each channel |7.509581196457717e-05|≤.002 |
| Indirect NRMSE |7.900647379218418e-05|≤.01 |

Fourth-seed audit:704643072 attempts/own checks,0 nulls;
max own-log error2.163602630389505e-12≤1e-6;
conditioned fraction.00850193671142973≤1;
unconditioned fraction513.569656513694 remains diagnostic.
8455688783 proposal queries and12288 auxiliary primary primes are retained.
Deterministic primary/component mean and second-moment bits match original
full evidence. No sample/pixel/seed/count changes or exclusions.

The compensated candidate now has **14/17 full physical artifacts**. Original
historical14/17, including its diagnostic-only item, is a separate inventory.
Earlier489–491 retain their original per-seed false pooled-verdict fields;
492 is the four-seed aggregate. Original261's failed numerical guard and its
partials remain unchanged. This scoped analytical PASS supports the repair;
it does not prove global density/support/Jacobian/radiance-bias correctness
or admit a reference. See [451](451-compensated-raw-target-candidate-outcome.md)
and the partial post-hoc [614 assessment](614-compensated-density-support-source-assessment.md).

## POST-HOC full quality: twelve further target FAILs

[714](714-posthoc-static-C7-software-full-quality-replay.json) replays original517;
[715](715-posthoc-dynamic-C12-hwrt-full-quality-replay.json) replays original519.
Both complete with valid execution and quality evidence, unchanged source
capture SHA256, accepted_timing=false/TIMING_INCONCLUSIVE and no reference
admission. All1774/1942 input/payload hashes respectively were independently
rechecked. Source commitdbcbdab3c17b962db9ba0a6db97eb88af3c568cf.

166 uses160's full native/raw/state/geometry/owned-memory intake,159's exact
documented RC-counter correction and unchanged eligible reference chains/
full-pixel scorer. Original517/519 bytes and their historical pending fields
remain unchanged; separate714/715 resolve current replay progress. All57600
pixels per scored component are included, with zero exclusions. Quality
evidence validity does **not** mean the quality target passed.

| Capture / frame | Transport | Indirect NRMSE | Signed sum bias | Quality target |
| --- | --- | ---: | ---: | --- |
| C7 software /0 |B2|.980718901229428|−.9102566473913816|FAIL |
| C7 software /0 |B8|.9744653672399431|−.9378170429051992|FAIL |
| C12 HWRT /0, source C7 |B2|.980718901229428|−.9102566473913816|FAIL |
| C12 HWRT /0, source C7 |B8|.9744653672399431|−.9378170429051992|FAIL |
| C12 HWRT /each of1–4, target/recovery C12 |B2|.9807189013246865|−.9102566119964941|FAIL |
| C12 HWRT /each of1–4, target/recovery C12 |B8|.974465279213193|−.9378169756519718|FAIL |

The last two rows represent eight scores; all **12 actual scores FAIL**.
C7 software's two indirect metrics equal retained C7 HWRT616. These are
scoped quality losses, without a comparative speed claim.

| Preserved execution evidence |714 C7 software|715 C12 HWRT |
| --- | ---: | ---: |
| Raw queries / fences |27/27|65/65 |
| Owned true peak bytes |266694400|266937920 |
| Owned persistent source/target phase-end bytes |262086400|262329920 |
| Owned teardown zero |true|true |
| Replay CPU / elapsed seconds, diagnostic |4.184287253/4.208224813002744|14.341719116999998/14.401948521001032 |

Both CPU-only replays ran serially, CPU31/nice15/BLAS1 with120CPU/180elapsed/
2GiB guards after145 ended. No GPU/native/compiler ran during replay.
Owned accounting is Vulkan allocation scope; CPU and driver-private memory
are excluded as declared. Neither result supplies accepted timing precision
or completes missing full-handoff accounting.

## Current completion and next step

- References remain **16/24**. A6b/IID, A10, separate level5 diagnostic529,
  density/support/Jacobian/numerical-bias assessment, full state/prefix,
  whole-frame feasibility, qualification/admission and final619 remain unfinished.
- Selected PT raw **2/28**, non-PT raw **8/8**, descriptive union10/36 remain.
  Non-PT quality replay is now **4/8**:509 dense C7,616 HWRT C7,714 software
  C7,715 dynamic HWRT C12. Four remain:513/514/515 static C1 and518 dynamic C6;
  their required missing references must become eligible before scoring.
- Sponza direct-relative-error1.0 pixels remain **UNRESOLVED / 未解決**,
  included in all relevant scores. No masked acceptance.
- Next separately invoke original145 A6b seed0 **once**, after publication and
  terminal inspection. Retained planning projects5536.614656CPU/
  5566.634649599902elapsed seconds, within original6000/9000 dispatch margins;
  this is planning, not an ETA. Keep native7200/10800/4GiB/one-core guards and
  no queue/retry. Independent A6b IID uses the retained original009 full IID
  payload under original rules; it does not launch an additional native job.

The optional CPU preference remains unanswered; keep one core. N010 then
separate Lane M, no N011. No N001–N009/default-build/Actions/host-setting changes.

