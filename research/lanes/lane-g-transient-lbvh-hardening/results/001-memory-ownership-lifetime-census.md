# G001 — Memory ownership and lifetime census

Status: **PENDING TARGET-GPU EVIDENCE**  
Plan: `lane-g-g001-v1`

## Purpose

Explain the F007 transient-LBVH sparse peak-memory ratios before any memory
optimization:

- sparse-stress: 3.0836x run-local vanilla;
- sparse-moving: 3.2025x run-local vanilla.

## Frozen implementation

The G001 runtime is an instrumented, Lane-G-owned snapshot of the F007
measurement implementation. F007 measurement commit
`041bf0287e2095302b61d31b222de958dd3b6412` and the later Lane-F head differ
only in research documentation, not runtime/source/shader files.

G001 adds accounting only. Buffer sizes, layouts, capacities, algorithms,
producer ordering, Hit semantics, traversal paths, and storage semantics are
unchanged.

## Required evidence

Target: **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**

Required scenarios:

- static;
- moving-rigid;
- sparse-stress;
- sparse-moving;
- dense-moving.

Run-local variants:

- transient-lbvh;
- vanilla-software;
- combined-hwrt;
- combined-software/B003.

The runner rejects any case where the sum of individually counted Vulkan
allocations differs by even one byte from the F007-derived
`peak_resident_bytes` accounting.

## Result

**Inconclusive / pending.** Target-GPU artifacts have not yet been supplied.
No G001 memory optimization conclusion is recorded yet, and G002 must not start.
