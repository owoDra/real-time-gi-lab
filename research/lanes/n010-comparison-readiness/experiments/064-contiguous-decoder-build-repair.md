# N010 prospective contiguous decoder build repair

Date: 2026-10-17 JST. Parent: `ac1ac7a`. Before corrected build/GPU dispatch.

063 build 204 terminated after one compiler invocation (exit1, 1.604 seconds,
no GPU). Moving the original CPU result decoder into a helper exposed its
original `target_state` dependency. Do not overwrite or rerun 204. Preserve
all original generated sources, compiler output and resource receipt.

Pass the original bool target_state explicitly to the helper; the batch entry
passes false because only static C7 is permitted. Three exact source edits,
with whole 204-generated-source inverse. All original timing expressions and
GPU recording stay identical. No numerical, scheduling or acceptance change.
Retain original builder source and use a wrapper; record all prior failure
bytes, new script/plan and all generated sources as hashed inputs.

Corrected isolated build result 205, `contiguous-c7-build-v2`. No retries there.
The 063 bounds and all scientific/identity/memory/CPU rules remain. Subsequent
single sizing is 206 (`contiguous-c7-sizing-v2`); if genuine PASS only, the
single eight-block/512-frame diagnostic is 207 (`contiguous-c7-diagnostic-v2`).
Results 205–207 replace the unused future names in 063, never its actual 204.
Any operational or numerical failure stops; no automatic retry or full run.
This is an implementation repair, not a second acquisition attempt; no GPU
acquisition has occurred for 063. No app, display, clock or power changes.
Unit/runtime regression tests NOT RUN. N010 remains NOT_READY.

Vulkan implementation sources consulted: [dynamic descriptor offsets](https://docs.vulkan.org/guide/latest/descriptor_dynamic_offset.html),
[descriptor ranges](https://docs.vulkan.org/spec/latest/chapters/descriptorsets.html),
[synchronization](https://docs.vulkan.org/spec/latest/chapters/synchronization.html).
These support API construction, not measurement validity or success.
