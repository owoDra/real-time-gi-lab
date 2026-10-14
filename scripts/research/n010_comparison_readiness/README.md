# N010 execution tools

## Continuous completion of existing acquisitions

`finish_readiness.py` waits for the already running original CPU reference
ladders, executes each qualified remaining GPU pilot sequentially, and waits
for CPU work to finish before quiet sizing and the single accepted calibration
campaign. It freezes script, binary, shader, state and sampler identities.
It records failures and stops; it does not retry accepted blocks, overwrite
partial work, change thresholds, use an unqualified cached oracle or publish
an architecture decision. Do not launch another GPU campaign or rebuild the
frozen executables while this driver is active.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_comparison_readiness/finish_readiness.py \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/references-v1 \
  --work out/research/n010-comparison-readiness/continuation-v1
```

Execution status and child logs are in `continuation-v1/status.json` and its
adjacent files. Future outputs: 043 C1 T_B8 ladder, 044 combined complete C1
ladder with both source evidence hashes, 048 complete Sponza dynamic cohort,
046 quiet sizing, 029 accepted calibration and 047 fail-closed preflight.
These are pending acquisitions, not passing results. Final result index,
decision, cross-lane summary and Lane M start require review of actual output.

`compile_ddgi_shaders.py` checks both pinned source/compiler file manifests
before and after CPU DXC compilation of official RTXGI shaders. Source is
not vendored or modified; compilation is not a DDGI runtime validation.
`score_corpus_captures.py` validates original payload hashes and scores into
a separate output directory, retaining the original captures unchanged.

All tools belong to the final preparation study. Default Renderer targets and
N001–N009 results are preserved. See the [protocol](../../../research/lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md).

## Build and environment

Configure the existing opt-in build with PHOS_BUILD_N007, PHOS_BUILD_N008,
PHOS_BUILD_N009 and PHOS_BUILD_N010 all ON, then build phos-n010-capture,
n010_direct_diagnostic and n010_probe_model. N010 uses unique shader output
names. The N009 C1/BF-P generated loaders are intentional dependencies.

Python dependencies: numpy 2.5.4 and scipy 1.18.1, installed in the ignored
out/research/n010-comparison-readiness/venv. On this NixOS host, expose the
standard runtime libraries through LD_LIBRARY_PATH = NIX_LD_LIBRARY_PATH.
GPU execution uses scripts/run_with_vulkan.sh; no clock/power configuration.

The CPU RQMC oracle is built by generating the sampling-only header/main with
generate_rqmc_oracle.py, then compiling with C++20, optimisation, pthread,
fno-fast-math and ffp-contract=off. make_sobol_table.py generates and hashes
the fixed Sobol table. Both source and binary identities are retained.

## Tools and evidence boundaries

| Tool | Purpose |
| --- | --- |
| diagnose_direct.py + n010_direct_diagnostic | Post-hoc N009 ray diagnosis; corrected version reproduces N008 camera rounding and edge nudge. |
| generate_capture.py | Isolated GPU capture, actual composite positions/keys; skips the expensive legacy N007 CPU audit. |
| replay_lookup.py | All-pixel replay using actual GPU keys, without exclusions. |
| generate_probe_model.py | N009 stage definitions with actual GPU key/position inputs. |
| generate_memory_hooks.py | Record both Vulkan allocation factories and frees across contexts. |
| validate_sampler.py | Frozen analytic/no-leak/iid controls; independent replicate statistics. |
| qualify_references.py | Locked-state ladder; refuses acquisition until physical validation passes. |
| score_hdr.py | Whole-image linear HDR errors, leak energy and fixed quality targets. |

The allocation ledger records startup/source/target/readback phases and proves
teardown returns to zero. Its high-water mark includes owned staging and
replacement coexistence. It excludes driver-private allocations and ordinary
CPU heap; those limitations must accompany comparisons. Diagnostic readback
is labelled separately from the recurring image-producing boundary.

## Active computation and resume

Original sampler validation 003 completed with A7 crosscheck FAIL. Amendment 2
confirmation 009 passes both fixed 16384-SPP iid controls with all 8192
checkpoint bytes unchanged. It carries forward the passing physical controls;
the original failed acquisition remains preserved.

Reference runners acquire distinct cell sets in references-v1. Do not restart
while either process is active or overwrite partial levels. C7 T_B2/T_B8 are
eligible at 16384 under unchanged thresholds; Sponza acquisition continues.
Complete construction state lock 016 includes the locally selected Sponza light
motion and actual non-Sponza camera/light/rigid/deforming/churn source/targets.
Reference eligibility remains a separate requirement.

Build phos-n010-pixel-pt for the native HWRT comparator. Its default family is
pixel-pt; --family dense-rc --spp 1 selects the separate cache-free repository
RC estimator control. The historical --backend vanilla in phos-n010-capture
is a traversal control retaining the incumbent producer/storage; it must not
be presented as an independent GI baseline. Both source/target capture tools
retain errors, source/binary identities and allocation lifetimes. Pilot GPU
timings are DIAGNOSTIC_UNCALIBRATED and were taken while CPU references ran;
no speed comparison follows from them.


Calibration: `calibrate_renderer.py --mode sizing|accepted --lock LOCK --work
NEW_DIR --output JSON`; accepted mode additionally requires `--plan SIZING_JSON`
and rejects active reference/GPU jobs. `--boundaries` may select named frozen
boundaries, but readiness requires all declared boundaries. Both GPU binaries
accept `--calibration-doses FILE` for exact per-sample known-work schedules.
No image/transport state is modified by the extra stage.

Amendment 3 computational cache: `generate_cached_oracle.py --out NEW_SOURCE_DIR`,
compile its main with the original O3/no-fast-math/ffp-contract=off/thread flags
to a separate `build/n010-cpu/n010_cached_oracle`; then run
`validate_cached_oracle.py --work NEW_DIR --output JSON`. Only complete exact
payload/counter equivalence may authorize cached qualification. The original
oracle and active reference outputs remain intact.

Amendment 6 continues the exact previous sample prefix instead of recomputing
it. `generate_incremental_oracle.py --out NEW_SOURCE_DIR` generates a separate
cached variant; compile with the same flags to
`build/n010-cpu/n010_incremental_oracle`. `validate_incremental_oracle.py`
requires complete cached proof 022 and physical validation 009, then resumes
the original 8192-SPP C1 T_B2 / C7 T_B2 / C7 T_B8 prefixes to 16384 and requires
every f64/PFM/primary-hit byte and integer counter to equal the existing full
original acquisitions. `--wait-for-cache-proof` polls the live cache acquisition
and never treats waiting as a passing proof. Build 049 is not eligibility;
complete all-pass proof 050 is required before any reference use. The running
original reference and continuation jobs are unchanged.
