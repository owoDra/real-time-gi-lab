# N010 original A6a seed2: bounded one-pixel failure reproduction

2026-10-18 JST. Parent `d254d5f9`. Commit this plan, exact driver and probe
before execution. This is a POST-HOC numerical diagnosis of terminal261,
not a new reference, acceptance test, retry or threshold amendment.

## Fixed question and source boundary

Can the original pinned wide8 oracle reproduce261's own-family area-density
failure at pixel(96,77), using seed81985529216486895, its absolute pixel
index77*128+96, and the original8192 sample indices? Identify the first
failing sample without rendering other pixels. The exact original header
SHA256 is40607186e96cad47e9386b4fcd78a71958894946a237e628c546566819970537.
Do not edit it, its original1e-6 check, proposal, intersections, spawn,
offsets, RNG, scene, net or old failure bytes.

Use the original `sample_all_split` entry point, fresh original PrimaryCache,
the original sample order0..8191, and PrimaryRecord only at sample0, matching
the renderer. The diagnostic caller catches the original exception solely
to record its sample index and stop. It never continues after an exception,
produces an accepted image or changes the oracle. A diagnostic return77
means an exception was caught; only matching the exact original message,
sampled/reconstructed densities and all four vertex lines establishes
reproduction. A different exception or no exception is a distinct retained
outcome. No data-dependent extension or second run is allowed by this plan.

## Two manually dispatched parts

`diagnose_original_sphere_pixel.py --stage build` writes434 and an isolated
probe binary. Use the original exporter flags from254: -mavx512f,
-std=c++20,-O3,-fno-fast-math,-ffp-contract=off,-pthread. Include the pinned
wide8 header; record compiler realpath/hash and all local inputs. No default
CMake graph changes.434 must finish successfully and be reviewed before a
separate `--stage probe` invocation writes435. Neither part launches the
other or queues further work. Refuse existing result/work paths; retain
terminal failures and partial stdout/stderr/resources without retry.

Before either part verify433/261 terminal identities and pinned payloads,
the exact committed plan/driver/source, and absence of other scientific
workers. Both parts use CPU31/nice15, one native numerical thread,120CPU/
180elapsed seconds and4GiB address space. Each child gets its own process
group and PID/start/boot/limit receipt. On timeout terminate only that owned
group after identity verification; do not touch apps or system settings.
No original full-seed restart, next seed, compiler/GPU campaign or waiter.

## Meaning and follow-up

435 records complete terminal observation independently of reproduction;
`all_pass`, reference admission and accepted timing stay false. Record
sample index, original exception, exact matching witness lines and all
payload/input hashes. Recheck inputs after termination. This can identify
a reproducible numerical event but does not by itself establish the root
cause or prove a repair. Further operand instrumentation or a changed
numerical implementation requires a separately frozen source/recipe before
execution.436 outcome records findings/current status; no extra gate.

References16/24, physical14/17 including one diagnostic-only item, two of
four original A6a seeds complete, seed2 FAIL. Sponza direct-relative1.0
pixels remain UNRESOLVED/未解決 and included. No GPU or timing admission,
unit/regression/default-build tests, N001–N009 edits, Actions, CUDA or
power/clock/display/driver/other-app changes. N010 remains final preparation
then distinct Lane M, no N011.
