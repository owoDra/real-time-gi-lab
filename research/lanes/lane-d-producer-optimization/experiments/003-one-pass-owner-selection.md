# D003 — one-pass visibility owner selection

Status: active

## Question

Can A001's two full source scans for visibility depth and deterministic owner be
replaced by one exact source scan without changing owner semantics or shifting
cost into an unmeasured conversion pass?

## Candidate

Use one 64-bit value per screen tile:

```text
high 32 bits = floatBitsToUint(positive camera depth)
low  32 bits = surface_id
```

A single `atomicMin` over that packed value selects:

1. the smallest positive camera depth; then
2. for exactly equal depth bits, the smallest surface ID.

This is the same tie-break rule as A001's depth pass followed by owner
`atomicMin`.

The candidate requires Vulkan 1.2
`shaderBufferInt64Atomics` / 64-bit buffer atomics. That requirement is part
of the architecture cost/compatibility result, not assumed to be free or
universal.

The existing A001-style surface producer reads the low 32-bit owner directly
from the packed visibility buffer. There is no GPU unpack/conversion pass.

## Compared paths

1. **accepted-a001** — unchanged accepted A001 runtime.
2. **two-pass-staged** — Lane D staged A001 depth + owner visibility followed by
   the unchanged surface producer.
3. **packed-one-pass** — one packed visibility reset + one source scan, followed
   by the same surface-source work semantics.

D002 tile emission is rejected and is not composed into D003. D001 renderer
depth reuse remains a separate retained integration contract and is not used to
hide standalone D003 visibility cost.

## Hypothesis

Removing one full Sponza surface projection/scan and one visibility-buffer
reset should reduce complete producer cost enough to survive synchronization
and downstream work.

The packed 64-bit atomic may instead be slower because its atomic throughput or
contention cost is higher. The experiment does not assume 64-bit atomics win.

## Correctness gate

For static, camera-motion, and light-motion:

- packed owner set must equal accepted A001 owner set exactly;
- visible-owner/output/work-item counts must match;
- all schema-v1 producer semantic checks must pass;
- gather/merge/resolve must pass A001 tolerance;
- overflow must remain zero;
- natural GPU append order/locality is measured without normalization;
- no depth quantization is allowed.

A device without required 64-bit buffer atomic support cannot produce a valid
D003 packed candidate and is recorded as unsupported, not silently replaced by
a weaker packing scheme.

## Measured boundary

Record separately for the packed candidate:

- packed visibility reset;
- packed visibility select;
- producer reset;
- producer emit;
- finalize/synchronization;
- producer total;
- gather / merge / resolve / end-to-end;
- owner/work/output counts;
- natural stream locality;
- persistent/transient/scratch/peak bytes;
- packed visibility bytes;
- stream capacity / actual bytes;
- overflow state.

For the two-pass staged control retain D001's explicit depth reset/depth,
owner reset/owner, emit/finalize boundaries.

## Memory

A001 uses 4 bytes/tile depth + 4 bytes/tile owner. Packed D003 uses one 8-byte
value per tile. No memory win is assumed.

Any driver alignment or buffer allocation increase must be reported if
observable.

## Decision gate

The packed mechanism is retained only when all three target cases pass
correctness and, relative to the matched `two-pass-staged` median:

- producer total improves by at least 10%;
- end-to-end improves by at least 5%;
- visibility memory does not increase beyond the equivalent 8 bytes/tile;
- no unmeasured GPU/CPU conversion or reorder is required.

For direct accepted-A001 relevance, packed one-pass must additionally:

- improve accepted-A001 producer total by at least 5% in all three cases; and
- not regress accepted-A001 end-to-end in any case.

Failing either group prevents composition promotion. A performance loss from
64-bit atomics is a valid rejection result.

## Target workload

- real Sponza;
- static / camera-motion / light-motion;
- AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- diagnostic validation first;
- accepted timing validation disabled;
- 3 process repeats;
- 50 timed iterations per case.
