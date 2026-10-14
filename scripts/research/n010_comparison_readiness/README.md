# N010 execution tools

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
