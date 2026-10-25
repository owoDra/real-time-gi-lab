# 042b — Disclosed development smoke executions, no quality scoring

Prospective addendum to 042/042a, written after the 042 native host and HLSL
compiled in a scratch build and BEFORE any 042 GPU execution, CPU preparation
or metric. Nothing in 042/042a changes.

The CPU replay must be developed against actual GPU record layouts. Development
smoke executions are therefore allowed, limited and disclosed:

- Target H01/B2 only, admitted 022 state; native option `--stream-base 16`
  (streams 16-19: SDK frameIndex `4096(16+s)+f` and the 042 producer-seed
  formula with `16+s`). Registered cohort runs use `--stream-base 0` only, so
  no development stream or path is reused as registered evidence.
- Outputs only under `out/research/lane-m-gi-competitiveness/m001-restir042-dev-*`;
  every directory, including failed runs, is kept and inventoried in the
  publication. At most 6 development GPU processes.
- No reference, NRMSE, bias or image-quality value is computed, displayed or
  used from development outputs. Allowed checks: process/ownership/guards,
  shader error flags, finite values, record ABI and CPU-replay agreement.
- No parameter, gate, threshold, seed rule or variant may change after a smoke
  run. Code fixes are allowed only for implementation/replay defects and are
  listed with their cause. The registered CPU preparation then rebuilds and
  re-tests everything from committed sources before any registered GPU case.
