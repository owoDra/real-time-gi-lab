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
