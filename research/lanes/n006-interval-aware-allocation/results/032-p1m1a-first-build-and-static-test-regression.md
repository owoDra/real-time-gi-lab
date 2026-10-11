# N006 P1m1a first local build — shader/C++ PASS, stale M0b static test assertion fixed

2026-10-11. User-provided complete terminal text (not a GPU outcome), local checkout after fast-forward `359e6b8..b356a5c`.

- The newly added `n006_p1m1_canonical_key_extra.comp.glsl` compiled to SPIR-V, `n006_runtime.cpp` compiled, and `phos-n006-intervention` linked successfully. Compiler emitted existing N001 anonymous-namespace and unused helper warnings, no compile errors.
- `python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'` reported **222 tests, 1 failure**: `test_pretrace_runs_after_primary_and_hash_before_secondary` at line 133 in `test_p1m0_consumer_coverage.py`.
- The failing assertion was **source string only**, `self.assertIn("request.p1m0_pretrace_coverage ? 22U", runtime)`. P1m1a intentionally shares the 24-entry Vulkan timestamp pool and expanded query-count gate to `(request.p1m0_pretrace_coverage || request.p1m1_canonical_key_intervention) ? 22U`. Thus the old single-arm literal is no longer in source. This failure **does not indicate a GPU M0b regression**.
- Corrective patch updates the static test to `assertRegex` that matches **both opt-in branches** in the conditional in source, preserving the 22-query requirement and the pretrace GPU placement checks. This is a test-only correction; no shader or runtime changes, no accepted historical behavior changed.
- The shell script used `set -e`, therefore exited **before any P1m1a GPU frames**. Status: **P1m1a NOT RUN / no signed quality result / no causal effect observed**, despite clean shader/C++ build.
- Re-run the exact previously frozen one-command pilot on the new branch HEAD:
```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1a_canonical_pilot.sh
```
- The existing experiment 023/024 protocols and frozen static/C3 tokens remain unchanged; if later intervention fails, retain per-case logs and investigate without replacing zero/low/high calibration keys. No PR or GitHub Actions.
