# G001 — Memory ownership and lifetime census

Status: implementation in progress

## Frozen purpose

Explain the F007 transient-LBVH sparse peak-memory failures (3.0836x and
3.2025x run-local vanilla) before making any memory optimization.

Required replay scenarios:

- static
- moving-rigid
- sparse-stress
- sparse-moving
- dense-moving

Required allocation classes include shared persistent, static HWRT persistent,
dynamic LBVH persistent, current-frame geometry, radix/sort scratch,
node/topology/bounds scratch, double-buffer capacity, producer stream, C001
storage, host mirrors, Vulkan allocation size versus logical payload, and
lifetime overlap.

G001 is diagnostic. Timing is not a promotion gate and G002 must not start until
this census has a result document and Issue #17 provenance update.
