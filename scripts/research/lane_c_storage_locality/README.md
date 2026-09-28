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
