# I001 — calibration workload and harness correctness

Status: **implemented; target validation pending**.

## Contract

The workload is a Lane-I-only Vulkan compute kernel. It has no dependency on
transient LBVH, HWRT/software traversal choices, dynamic geometry, C001 storage,
or the production GI runtime.

All variants use the same pipeline, descriptor layout, buffers, dispatch
dimensions, barriers, and batch structure. The only controlled variable is the
runtime push-constant `work_iterations`:

| variant | iterations | controlled work |
| --- | ---: | ---: |
| baseline | 200 | 100% |
| plus5 | 210 | 105% |
| plus10 | 220 | 110% |
| plus20 | 240 | 120% |

`controlled_work_units = element_count * work_iterations * batch_dispatches`.
This is a work-count contract, not an assumption that elapsed time scales
linearly.

Each shader loop iteration performs a state-dependent storage-buffer read and
updates state used by the next iteration. Repeated dispatches also depend on
prior dispatch state. A CPU reference implementation uses the same unsigned
32-bit operations. I001 validation compares the full GPU output checksum against
that reference for every variant, so a removed or short-circuited delta fails
correctness.

## Boundaries

- GPU timestamp: starts after deterministic state reset and ends after the final
  controlled dispatch.
- complete CPU wall: starts before command-buffer reset/recording and ends after
  fence wait and timestamp retrieval. The recurrent deterministic state reset is
  included in wall time but excluded from the controlled-work GPU timestamp.
- checksum readback: validation-only and outside both accepted timing boundaries.

Warmup and measured rows are retained separately. Measurement mode supports
adjacent baseline/candidate pairs, alternating AB/BA order, same-process batches,
and fresh-process orchestration by the Lane I runner.

## GPU-independent validation

`phos-lane-i-contract-test` verifies exact 5/10/20% work ratios,
input/state determinism, distinct reference checksums, and invalid-size
rejection. The source contract is the source of truth for the work-count mapping.
