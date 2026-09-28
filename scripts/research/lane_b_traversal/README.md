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
