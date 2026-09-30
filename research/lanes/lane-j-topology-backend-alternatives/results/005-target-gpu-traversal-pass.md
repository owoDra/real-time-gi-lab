# J003 representative target-GPU traversal result

Status: **PASS — exact traversal probe**

The first target-GPU traversal proof passed on the frozen
`medium-global-representative/step-00` J002 snapshot.

## Observed result

- device: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- triangles: 796;
- clusters: 17;
- upper BVH nodes: 33;
- micro BVH nodes: 1575;
- validation rays: 4096;
- hit mismatches: **0**;
- traversal runtime errors: **0**;
- diagnostic traversal GPU time: 1030.92 us.

The loader emitted a warning while probing the Mesa DZN ICD
(`vkCreateInstance -> -9`) and skipped that driver. RADV subsequently created
the Vulkan device and the retained probe completed successfully, so the DZN
message is not a J003 failure.

## Interpretation

This result validates the first GPU boundary only:

`frozen J002 snapshot -> deterministic clustered BVH -> GPU upper/micro traversal -> exact triangle Hit -> CPU brute-force comparison`.

It proves that the current GPU layout, exact triangle semantics, nearest/tie
selection, two-sided handling, miss encoding and traversal payload bounds agree
with the independent CPU reference for this representative snapshot.

The diagnostic timestamp is **not** promotion evidence and must not be used to
rank J003 against any comparator.

## Promotion

Proceed to transition-time J003 work:

1. persistent cluster identity;
2. dirty ownership classification;
3. dirty-cluster-only micro-BVH updates;
4. v1.1 split/merge plus v1.2 empty-cluster retirement;
5. upper refit/rebuild;
6. transition allocation lifetime/old-new overlap accounting;
7. exact GPU replay across topology transitions.

A001/C001 integration and comparator memory gates remain later J003 gates.
