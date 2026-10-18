# N010 intended-batch hybrid FAIL; CPU continuation

2026-10-18 JST. Plan115/driver committedfc044642 before371/372. Post-hoc
CPU-localization plan116/source committed99aa5005 before375/376. No rerun,
sample omission, relaxed counter/quality threshold or new GPU layout.

## Registered115 outcome: FAIL, stop scaling this hybrid

Independent original254 CPU [371](371-batched-full-frame-cpu.json) completes
the original C1_T_B8 full320x180/seed305419896/16spp, with an8spp checkpoint,
all full-frame finite HDR means/moments/PFM conversions and original primary
hits. CPU native exits0:53.512358elapsed/53.289984CPU seconds, CPU31/nice15/
4GiB within300CPU/420elapsed. Checkpoint8 includes HDR means/moments only;
there is no invented independent8spp counter/audit record or restore proof.

Unchanged360 full-mode [372](372-batched-full-frame-gpu.json), batch16/tile512,
also native exits0:44.752254elapsed/26.457416CPU seconds. Every921600 scored
path/113 tile/791 depth finishes, max depth submit/wait37.124507ms. This
native passes numerical means/moments but **fails the unchanged independent
scored-count check**. Overall qualification stays FAIL despite ratio0.836298.
Successful373 summary is intentionally absent;115 requires BOTH parts PASS.

| Frozen full-frame count | Independent CPU371 | Hybrid372 | Outcome |
| --- | ---: | ---: | --- |
| Primary hits |921600|921600| Match |
| Shadow tests |2722260|2722259| **FAIL** |
| Shadow blocked |516068|516068| Match |
| Backface absorbed |0|0| Match |
| Proposal BVH queries |53595139|53595137| **Mismatch**, post-hoc check after first failure |
| Proposal attempts |6451200|6451200| Match |
| Proposal nulls |1055259|1055259| Match |
| Own checks |5395941|5395941| Match |

The shorter native wall is a single-run operational observation. It does
not satisfy115's conjunction, admit this backend, or establish a calibrated
GPU/CPU or GI superiority claim. Do not bypass the failure because the
counter difference is small. No alternative tile/guard/seed is retried.

## Explicitly post-hoc review, no reclassification

Retained full-image data gives max absolute mean/second-moment discrepancy
4.475586568020162e-16 and indirect RGB NRMSE1.6915142874247148e-15, below
the unchanged1e-10/1e-8 cuts. This numerical success cannot resolve the
counter/transport-decision discrepancy. All20011 original1spp and319945
current16spp fallback samples remain included, not masked. Current reason
counts overlap:310242 intersection,14573 reconstructed-target/plane,25 own,
1946 tiny cosine/pdf,25 potential coincidence and25 other routes.

Owned allocation replay separately passes, peak91,022,480bytes and zero
teardown. This remains standalone-backend owned Vulkan memory, excluding
CPU/driver-private memory; not Renderer/comparator true peak. No timing gate
failure erases this scoped memory observation. CPU/wall/telemetry are not
new algorithm-quality acceptance criteria. No environment-stability tuning.

CPU-only [375 build](375-posthoc-batched-counter-build.json) copies the exact
original254 CPU header without physical edits and compiles an isolated scan.
[376](376-posthoc-batched-counter-scan.json) then replays ALL57,600 pixels/
16spp with original CPU transport/RNG. Every24-double CPU mean/moment record
matches371 bit for bit; global scored/proposal counts reproduce371 exactly.
The GPU per-pixel counters have exactly one differing pixel:

| Pixel / coordinates | CPU primary, shadow, blocked, backface | GPU |
| --- | --- | --- |
|43665 / (145,136)|[16,53,4,0]|[16,52,4,0] |

Keep the16 original CPU sample components, scored counters and query/null/
own counts for that pixel in scan.json. All pixels were scanned, not just
this subsequently selected diagnostic pixel. Scan native exits0,
52.513054elapsed/52.242238CPU seconds, CPU31/nice15/4GiB/120CPU/180elapsed.
Diagnostic_valid=true means the replay/localization is valid; all_pass=false
preserves GPU qualification failure. It is not a repaired backend result.

372 full mode has no per-path GPU stream. The sample/depth/ray cause is
**UNRESOLVED / 未解決**. Do not attribute the two missing global proposal
queries to this pixel without additional evidence. A floating geometric
branch difference is a hypothesis, not an established diagnosis. The earlier
1spp whole-frame PASS and selected8192/four-seed PASS retain their own scope;
they never qualified all image/sample combinations.

## Continuation toward the original goal

Stop new scaling/restore/GPU campaigns for this variant. Continue original106
physical qualification with the validated wide8 CPU exporter, one explicitly
invoked low-priority seed at a time. The immediate next part is original A6a
seed1 (260); do not restart terminal seed0/259 or queue the following seed.
Original full inventory stays14/17 including one diagnostic-only item;
references16/24. Remaining sphere/range parts, IID/independent density/bias,
all24 states/exact prefixes, full reference convergence, quality/dynamics/
Renderer memory/budgets/selected timing calibration/final intake are required.
No N011, Lane M accepted campaign, or widened success definition.

Sponza direct max-relative-error1.0 pixels remain **UNRESOLVED / 未解決** and
scored. This newly localized hybrid counter failure is a distinct unresolved
issue; do not conflate it with those original direct-light pixels. N010
**NOT_READY**. Keep static-C7 calibration255/256 PASS and all older FAILs.

Publication verified824 unique result/input/payload SHA identities exactly,
and all four new compiler/native receipt identities exit0/terminal. This
terminal statement applies to371/372/375/376; any subsequently started CPU
control is recorded in current status separately. No power/clock/display/
driver/application setting, Renderer/default build, Actions or N001--N009
result changes. Build/unit/regression tests NOT RUN; isolated compilation
and registered scientific/post-hoc CPU checks above were executed.

Immutable result SHA-256:

- 371: `225b9e381492bc29c75938de3d4f3603da10e5747f1fb97b15d071467bf63635`.
- 372: `088a828350fb163868691636707afc98eeb8d7fa7064d9e5ef7660422c7e07c1`.
- 375: `e8f64322242672e53394e98b1f3a3d6dfdfb26534e7e224b5b6942e9a002419e`.
- 376: `b57bb16d93ea44ac15fd0ac215b3b7819f589460445079c40e1ef8717223ed4b`.
