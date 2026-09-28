# Lane C scripts

Lane-specific storage/locality benchmark and analysis helpers live here.

- `experiment_001.py` is the deterministic C001a structural/correctness
  bring-up for the three required storage representations. It deliberately
  records no wall-clock or GPU timing and must not be used as performance
  evidence.
- `test_experiment_001.py` checks semantic parity and includes controls that
  prevent the experiment from assuming that brick storage always wins.

Use `mise run research:record` for raw experiment artifacts on the target
environment.
