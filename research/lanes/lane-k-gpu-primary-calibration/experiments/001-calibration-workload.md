# K001 — architecture-neutral calibration workload

Status: **prepared; target validation not yet accepted**

## Provenance

K001 selectively reuses the architecture-neutral workload mechanism from Lane I.
No Lane I target timing result or accepted resolution is imported.

## Validation shape

- 8192 elements;
- baseline 200 iterations;
- +5% = 210;
- +10% = 220;
- +20% = 240;
- accepted batch shape = 16 dependent dispatches;
- one-dispatch profile = harness diagnostic only.

## Correctness contract

The runtime iteration count is the only controlled variant difference. Resource
shape, descriptor layout, dispatch geometry, input buffers, and shader are
otherwise identical.

`work_iterations` is a runtime push constant. Every loop iteration mutates the
state, derives the next storage-buffer read from that evolving state, and
contributes to the final state. K001 therefore validates work by observable
state rather than trusting a logical variant label.

Target acceptance requires:

1. exact baseline/+5/+10/+20 controlled-work-unit ratios;
2. GPU checksum equals the CPU reference for every variant;
3. non-zero and variant-distinct final checksums;
4. both 16-dispatch and one-dispatch validation profiles pass;
5. exact GPU/driver/API/timestamp provenance is recorded.

K001 is harness/correctness evidence only.
