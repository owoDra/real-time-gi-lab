# J003 persistent Vulkan replay checkpoint

Status: **IMPLEMENTATION READY — representative target-GPU replay pending**

The all-profile host persistent-layout gate passed. Lane J now contains the
first persistent Vulkan implementation of the frozen v1.3 slot policy.

## Implemented

Candidate persistent lifetime:

- device-local triangle slot buffer;
- device-local fixed-capacity micro-BVH slot buffer;
- device-local cluster metadata buffer;
- device-local upper-BVH buffer.

Transition updates:

- dirty triangle slot ranges only;
- dirty micro-BVH slot ranges only;
- dirty cluster metadata records only;
- full active upper-BVH prefix on cluster-set rebuild;
- exact dirty upper-node records on membership-stable refit;
- full candidate migration only when slot capacity grows.

Resize accounting:

- old candidate buffers remain live while replacement buffers are allocated and
  populated;
- actual Vulkan allocation sizes are read from
  `VkMemoryRequirements::size`;
- old/new simultaneous allocation overlap is reported;
- transient staging allocation size is reported;
- candidate true peak is computed as persistent overlap plus maximum live
  staging allocation.

Validation:

- the existing exact J003 traversal shader binds directly to the persistent
  candidate buffers;
- ray/hit buffers are validation-harness allocations and remain separate from
  candidate persistent memory;
- every frozen snapshot receives deterministic validation rays;
- GPU Hits are compared against the independent CPU brute-force reference;
- traversal runtime-error counters must remain zero;
- diagnostic timestamps remain non-ranking evidence.

## Representative gate

Run:

```bash
git pull --ff-only
mise run research:j003:persistent-gpu --validation
```

Default profile:

`medium-global-representative`

Default validation rays:

4096 per snapshot × 8 frozen snapshots.

Required result:

- build succeeds;
- target resolves to RADV STRIX_HALO;
- total Hit mismatch count = 0;
- total traversal runtime error count = 0;
- every transition records actual persistent allocation bytes;
- dirty transitions report partial upload bytes/regions;
- no resize is expected for this representative profile.

After PASS, expand the same gate to the large-global resize path and then all
five profiles before comparator-memory acceptance.
