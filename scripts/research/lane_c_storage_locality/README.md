# Lane C scripts

Lane-specific storage/locality benchmark and analysis helpers live here.

- `experiment_001.py` is the deterministic C001a structural/correctness
  bring-up. It records no timing and must not be used as performance evidence.
- `test_experiment_001.py` checks C001a semantic parity and prevents the
  experiment from assuming brick storage always wins.
- `run_c001b.sh` launches the Lane C Vulkan executable through the repository
  Vulkan/NixOS wrapper.
- `c001b_matrix.py` runs repeated Vulkan C001b processes under one
  `research:record` artifact and writes `c001b_summary.csv`.

Accepted C001b timing should use the matrix runner with validation disabled;
validation runs are diagnostics. Raw artifacts must be created through
`mise run research:record`.


## C001c exact Lane A replay

- `run_c001c.sh` launches the same Vulkan storage executable in exact-stream
  mode with `--stream <stream-v1.bin>`.
- `c001c_matrix.py` consumes the `static`, `camera-motion`, and
  `light-motion` A001 exports from one Lane A artifact root and writes
  `c001c_summary.csv`.

Example:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/c001c_matrix.py \
    --lane-a-artifact out/research/lane-a-split-rc/001-representative-producer/<timestamp> \
    --repeats 3 --iterations 100"
```

Run `--repeats 1 --iterations 10 --validation` first for diagnostics.


## C001d exact transition

`c001d_matrix.py` measures the recorded frame-to-frame transition without
sorting the target producer stream. By default it replays:

`static/stream-v1.bin -> camera-motion/stream-v1.bin`

from one A001 artifact root.

Diagnostic validation:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/c001d_matrix.py \
    --lane-a-artifact <A001-artifact-root> \
    --repeats 1 --iterations 10 --validation"
```

Accepted timing uses `--repeats 3 --iterations 100`.
