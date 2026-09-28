# Lane B research scripts

`run_b001.sh` is the target-side entry point for Experiment B001. It runs the
HWRT capability probe and the CPU traversal-control matrix inside the same
`research:record` artifact.

Target command:

```bash
mise install
mise run research:check
mise run build
mise run research:record --lane lane-b-traversal \
  --experiment 001-traversal-contract-and-controls \
  --command "scripts/research/lane_b_traversal/run_b001.sh build/release/phos-lane-b-b001"
```

Optional environment overrides:

- `B001_RAYS` (default `65536`)
- `B001_REPEATS` (default `5`)

Expected extra artifacts:

- `b001-controls.csv`
- `hwrt-probe.json`

The probe only establishes whether implementing a comparable HWRT/ray-query path
is viable on the target Vulkan device. Extension presence is not performance
evidence.


## B002 target execution

B002 consumes the already-recorded accepted A001 artifact. It does not rebuild
or modify Lane A.

Expected A001 input:

`out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z/`

Run from a clean `research-lane-b-traversal` checkout:

```bash
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-b-traversal \
  --experiment 002-lane-a-exact-stream-traversal \
  --command "python scripts/research/lane_b_traversal/run_b002.py --build-dir build/release --lane-a-artifact out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z --iterations 30 --build-repeats 3"
```

The runner first executes the three exact Lane A streams, then the controlled
moving-geometry maintenance gate. Validation layers can be enabled for
diagnostics with `--validation`, but validation runs are not accepted
performance evidence.

Expected additional artifacts:

- `b002-results.csv`
- `b002-correctness.json`
- `b002-device.json`
- `b002-config.json`
- `b002-maintenance.csv`
- `b002-maintenance.json`

If the accepted A001 artifact is no longer present locally, restore or rerun
A001 on its own branch first; do not merge Lane A into Lane B merely to
regenerate the stream.


## B003 Stage A target execution

B003 records the rejected Macro-BVH8 top-level control and now also tests a
DDA/hash-preserving wide micro-BVH8 candidate in the same exact-stream run.

Run from a clean `research-lane-b-traversal` checkout:

```bash
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-b-traversal \
  --experiment 003-wide-software-traversal \
  --command "python scripts/research/lane_b_traversal/run_b003.py --build-dir build/release --lane-a-artifact out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z --iterations 30 --build-repeats 3"
```

Expected additional artifacts:

- `b003-results.csv`;
- `b003-stage-a-summary.json`;
- `b003-correctness.json`;
- `b003-device.json`;
- `b003-config.json`.

`advance_to_stage_b=true` requires at least 20% same-run mean traversal
improvement, no more than 1.15x persistent memory, and zero correctness/runtime
errors. A false value is a valid rejected Stage A result, not a harness failure.


### B003 Stage B pivot

The corrected Stage A evidence rejected replacing the segment DDA/hash with a
Macro BVH8. The current B003 executable now also measures a third candidate that
retains DDA/hash and replaces only the per-segment binary micro BVH with a
collapsed float BVH8.

The same formal command is used. New artifacts include:

- `b003-stage-b-summary.json`.

`advance_to_quantization=true` means the uncompressed wide-micro path is within
15% of the same-run binary baseline, uses at most 1.5x persistent memory, and is
fully correct. This is deliberately a viability gate for compression, not the
final B003 success target.


### B003 Stage B2 quantization

The same formal B003 command now also measures conservative 16-bit quantized Micro BVH8. It emits `b003-stage-b2-summary.json`; `advance_to_triangle_packets=true` requires zero errors, <=1.10x float-BVH8 traversal, and <=0.90x float-BVH8 persistent memory.


### B003 Stage B3 triangle packets

The same formal B003 command now also measures direct four-triangle leaf packets on top of the quantized BVH8. It emits `b003-stage-b3-summary.json`. `retain_triangle_packets=true` requires zero errors, packet traversal <=0.95x the quantized non-packet traversal, and packet persistent memory <=1.25x.
