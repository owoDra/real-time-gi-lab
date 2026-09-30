# J003 target-GPU traversal probe preparation

Status: **IMPLEMENTATION READY — target GPU evidence pending**

This checkpoint records the first target-GPU implementation boundary. It is not
a J003 acceptance result and contains no candidate ranking.

## Implemented

The Lane-J-owned probe now provides:

- exact `PHOSJ2G1` snapshot loading with magic/version/record-size fail-closed
  validation;
- deterministic J003 initial clustering at target occupancy 48 and hard maximum
  64;
- conservative per-cluster binary micro-BVH;
- conservative upper cluster BVH;
- exact triangle payload with primitive/material/instance/two-sided metadata;
- B001-compatible CPU brute-force reference and nearest/tie semantics;
- deterministic validation hit/miss rays;
- Vulkan compute traversal of:
  `upper BVH -> cluster -> micro BVH -> exact triangle`;
- GPU output counters for upper-node visits, micro-node visits, exact triangle
  tests, and traversal runtime errors;
- explicit descriptor payload bounds so malformed cluster/triangle leaf payloads
  fail closed instead of reading out of range;
- diagnostic GPU timestamp capture;
- candidate-vs-validation allocation census;
- a host-only contract executable to isolate C++ layout/reference failures from
  target-GPU failures.

Diagnostic timestamps are not promotion evidence. J004 ranking remains
prohibited.

## First target-GPU gate

Build:

```bash
mise run configure
mise exec -- cmake --build "$PHOS_GI_BUILD_DIR" \
  --target phos-lane-j-contract-test phos-lane-j-j003-probe
```

Run the host contract first:

```bash
"$PHOS_GI_BUILD_DIR/phos-lane-j-contract-test"
```

Then validate the representative frozen snapshot through the repository's
NixOS/Vulkan launcher. Direct execution is intentionally avoided because NixOS
may not expose `libvulkan.so.1` or the host ICD search paths to the development
shell:

```bash
bash ./scripts/run_with_vulkan.sh \
  "$PHOS_GI_BUILD_DIR/phos-lane-j-j003-probe" \
  --validation \
  --snapshot \
  out/research/lane-j-topology-backend-alternatives/002-deterministic-topology-contract/materialized/medium-global-representative/step-00.bin \
  --output \
  out/research/lane-j-topology-backend-alternatives/003-target-gpu-prototype/j003-traversal-probe.json
```

Required first-probe outcome:

- host contract PASS;
- target device resolves successfully;
- `hit_mismatch_count = 0`;
- `traversal_runtime_error_count = 0`;
- occupancy maximum <=64;
- complete six-buffer probe allocation census.

## Not implemented yet

This checkpoint does not claim completion of:

- transition-time persistent cluster state;
- dirty-cluster-only device updates;
- split/merge device lifetime accounting;
- upper refit vs rebuild transition handling;
- static/dynamic nearest-hit merge;
- A001 natural-stream integration;
- C001 storage integration;
- Lane E HWRT rebuild memory comparator;
- hardened LBVH comparator;
- final J003 hard-memory eligibility.

Those are subsequent J003 gates after the first target-GPU traversal proof.


## Invocation correction

The first attempted target-GPU invocation used the executable directly and
failed at vk-bootstrap instance initialization with `vulkan_unavailable`.
No Vulkan instance, device, shader dispatch, or candidate evidence was produced.

The repository already standardizes NixOS Vulkan execution through
`scripts/run_with_vulkan.sh`, which exposes the Vulkan loader and
`/run/opengl-driver` paths. All retained J003 target-GPU commands must use that
launcher (or an equivalent environment proven to expose the same loader/ICD).
