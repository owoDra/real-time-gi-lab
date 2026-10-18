# N010 tiled PT: first-tile diagnostic stops on observed duration

2026-10-18 JST. Plan125/driver committede8231881 before396 preparation,
397 host/link and one398 probe. All three manual steps are terminal valid;
all_pass/accepted_timing/reference_admission stay false. No repeated probe.

Source396 is exactly invertible to389's whole host. Only Vulkan-call trace
logging and a mandatory first-tile stop were added.390 SPIR-V remains exact
SHAa1e62d3ca4550a751afeadfb3e859c456611d4d0b0fa9f9d96e72b972aaade85.
Build397 changes private host/object/dependency/link outputs only; no shader
compile or default build. Host2.069734s/2.011084CPU, link0.066033s/0.049588CPU.

[398](398-tiled-pt-first-call-probe.json) uses original C1/1024spp/depth8/
seed305419896/tile64. All11 traced Vulkan calls return VK_SUCCESS(0),
including queueSubmit,500ms waitForFences and getQueryPoolResults. One
complete timestamp receipt covers pixels0..63, raw begin638766804095,
end638816770667, actual timestampValidBits64/period10.019036293029785ns.
GPU duration500616.89830628585us exceeds the unchanged250000us completed-
tile operational guard, so execution stops before any second tile or image.
Native62236 exits1 after0.619221elapsed/0.088319CPU seconds, CPU31/nice15,
10CPU/5elapsed/unlimited Vulkan virtual address-space limits. This is a
valid diagnostic trace, not a valid complete capture or timing comparison.

395's generic Vulkan error is NOT reproduced: no nonzero VkResult is seen.
Do not retrospectively label395 a fence timeout or device loss. Its original
exact call remains unproven. The observed half-second timestamp is one
run on this desktop, not an intrinsic lower bound, calibrated throughput,
statistical instability verdict or proof that other apps caused the stop.
No error justifies changing display/power/driver/apps or raising these guards.
No successful PFM/equivalence result, C7 capture or391 summary exists.
Exception-path ledger/partials are retained; no accepted memory conclusion.

## Next implementation work

Pixel-only tiling has not demonstrated the required bounded execution at
PT-B8/1024. Continuing toward the same full-image/quality boundary requires
an implementation that can yield within each pixel's sample sequence:
retain its exact uint RNG state, float accumulated indirect sum and next
sample index between dispatches; preserve sample order/transport/rounding,
then require EVERY final PFM byte to match046 before any comparator use.
This requires a new prospective source/build/equivalence contract, explicit
additional persistent memory and full-cost accounting. Do not replay123,
change its tile size, lower spp or silently reuse a failed record as PASS.
No continuation implementation, source proof, compiled/runtime equivalence
or new acquisition is claimed by this outcome; no work is queued.

C1 guarded reference backend393 remains a separate full-frame16spp PASS,
not a qualified physical/reference backend. CPU259/260 are terminal original
A6a seeds0/1 only. References16/24, physical inventory14/17 incl one diagnostic
item; full controls/states/prefixes/counts, all quality/dynamic/memory pilots,
selected timing and final intake remain. N010 NOT_READY; then Lane M, no N011.
Timing uncertainty may be INCONCLUSIVE under120; missing evidence cannot.
Sponza direct-relative1.0 pixels remain UNRESOLVED/未解決 and scored. N001–N009,
Actions, default build and user settings unchanged. Tests NOT RUN.
