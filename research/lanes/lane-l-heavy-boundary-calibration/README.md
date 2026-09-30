# Lane L — heavy-boundary timing calibration

Issue: #24  
Status: **L001 FROZEN — READY FOR TARGET EXECUTION**

Lane L calibrates the paired GPU timing methodology for the complete J002 heavy
recurring boundary. It does not rank topology backends.

## L001

L001 compares same-variant controls under two measurement environments:

- `dual-context`: J004-style independent Vulkan contexts and independent runtimes;
- `single-context-independent-runtime`: one Vulkan context/device/queue with two
  independent runtime/resource states.

Both primary and software incumbent controls are calibrated across all five J002
profiles. The frozen J004 1.02 / 1.03 / 1.02 control-health gate is unchanged.

The two environments are position-counterbalanced across fresh-process blocks.
GPU timestamp is the only performance decision axis. CPU wall is
diagnostic/health/provenance only.

Single-context timed memory is diagnostic-only because the context-level
allocation counters are shared. Independent allocation lifetime is instead
validated before timing by observing exact live-allocation restoration as the
two runtimes are created and destroyed.

Canonical pre-target records:

- `experiments/001-l001-heavy-boundary-calibration-plan.md`
- `experiments/002-l001-config.json`
- `experiments/003-l001-execution-freeze.json`
- `results/001-l001-target-execution-freeze.md`

J004 remains immutable and J005 remains forbidden.

L002 is permitted only if neither L001 environment passes every required
profile/control gate.
