# Lane I scripts

- `run_i001.py`: target checksum/provenance validation. Timing is not accepted evidence.
- `analysis.py`: frozen paired-statistic and resolution logic.
- `test_analysis.py`: GPU-independent unit tests for the frozen decision logic.
- `test_protocol.py`: verifies frozen workload ratios and counterbalancing invariants.
- `run_i003.py`: accepted batched calibration plus frozen individual-sample diagnostic.

Accepted timing must use the committed I002 config, retain every sample, and use
automatic GPU power management only.
