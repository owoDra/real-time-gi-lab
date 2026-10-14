# N010 interim comparison findings — 2026-10-14

N010 remains active and **NOT_READY**. It is the final preparation study before
Lane M GI competitiveness; no N011 is planned. These are actual quality
comparisons, with eligible references and every pixel scored. They do not
establish a calibrated speed ranking or general superiority.

## What the executed comparisons show

| State / transport | Role | Indirect NRMSE | Indirect sum bias | Quality |
| --- | --- | ---: | ---: | --- |
| Sponza static C1 / T_B2 | Incumbent HWRT or software | 88.8399% | +35.8544% | FAIL |
| Sponza static C1 / T_B2 | Independent dense repository RC control | 88.8184% | +36.2442% | FAIL |
| Sponza static C1 / T_B2 | GPU pixel PT, 256 spp | 8.5080% | +0.0058% | PASS |
| Sponza static C1 / T_B2 | GPU pixel PT, 1024 spp | 4.2466% | −0.0143% | PASS |
| Controlled C7 / T_B2 | Incumbent | 98.0719% | −91.0257% | FAIL |
| Controlled C7 / T_B2 | GPU pixel PT, 256 spp | 9.9581% | +0.2343% | PASS |
| Controlled C7 / T_B8 | GPU pixel PT, 1024 spp | 5.5750% | −0.0599% | PASS |

Sources: [C1 fixed PT ladder](031-c1-b2-pt-quality-ladder.json),
[C1 RC scores](032-c1-b2-cohort-scores.json),
[C7 fixed PT ladder](013-c7-pt-cohort-pilot.json),
[incumbent summary](017-comparison-pilot-summary.json).
PASS requires all preregistered total/indirect/bias gates, not just the
indirect metric displayed here. C1 PT at 256 spp has total NRMSE 3.5254%.
The C1 reference passes the unchanged support-aware screen at 16384 and
32768 consecutively; its T_B8 acquisition is still in progress.

The [controlled dynamic cohort](019-controlled-dynamic-cohort.json) retains
all 145 source, first changed and recovery images. After C9 light motion,
incumbent T_B2 indirect energy is approximately 7.645 times the reference.
This is an overestimation loss; C7 demonstrates underestimation instead.
The complete C8/C9 PT ladders select 1024 spp for both transports. Original
256-spp dynamic losses remain in the record. All 29 owned Vulkan allocation
ledgers independently replay within the 8 GiB cap and to zero at teardown
([memory summary](020-controlled-dynamic-summary.json)). Driver-private
memory and CPU heap are outside this owned allocation scope.

The historical vanilla-software role retains the same work producer and
sparse radiance storage; it is a traversal control. The separate dense RC
role is a repository estimator control, not an external production RC.
Quality-failing roles cannot claim a same-quality speed win.

## Correctness and unresolved limitations

The incumbent Sponza direct term still has two GPU-zero/reference-positive
pixels, with maximum relative error **1.0: unresolved (未解決)**. They remain
included in all scores. Native pixel PT has no direct support disagreements
on C1. N009's SC NO GO, BF PASS and PT INCOMPLETE, including its post-hoc
sensitivity analyses, remain unchanged.

This corpus uses 320×180 BF-P gray, opaque two-sided Lambert transport with
the declared finite T_B2/T_B8 depths. It is not a textured or glossy Sponza
demonstration, an infinite-bounce reference, or a multiple-GPU result.

## What is being completed next

1. Finish the existing Sponza reference ladders and score the remaining static
   and dynamic pilots. Keep every failed level and quality loss.
2. Calibrate complete Renderer GPU timing after CPU/reference acquisition
   finishes. Failed diagnostic sizing [027](027-calibration-sizing.json) and
   [028](028-calibration-inner-work-sizing.json) remain retained. Prospective
   Amendments 4/5 change dose sizing and instrumentation; the acceptance
   thresholds remain unchanged. No accepted calibration block has run.
3. Run the fail-closed handoff check. The executed interim check
   [030](030-readiness-preflight-interim.json) correctly returns NOT_READY.
4. Proceed to Lane M to measure quality, complete GPU cost and owned true-peak
   memory together. RTXGI source is pinned, its Vulkan host SDK builds on AMD,
   and the pinned DXC compiler runs on the CPU; integrated DDGI GPU execution
   is still required before the accepted broader Lane M campaign. No CUDA is
   used ([SDK build](023-ddgi-vulkan-host-build.json),
   [compiler provenance](034-dxc-cpu-compiler-provenance.json)).

Continuing has a concrete purpose: measure the quality–cost frontier and
identify whether the incumbent has a useful tradeoff. The existing quality
losses already motivate transport/estimator changes more strongly than
further isolated traversal optimizations. No favorable result is promised.

Builds and listed GPU captures were actually executed under user authorization
on Radeon 8060S / RADV. Pilot times are DIAGNOSTIC_UNCALIBRATED, including
concurrent CPU reference load. No default Renderer promotion, new unit tests,
CI workflows, power/clock changes or N001–N009 result changes are made here.
