# N010 execution tools

## Current execution: plans 034–037

The current record is [130](../../../research/lanes/n010-comparison-readiness/results/130-validated-reference-acquisition-and-comparison-transition.md).
Earlier command/status descriptions below are historical execution checkpoints.
The old idle finisher is retired (120), both old CPU recovery jobs were stopped
at the user's request (124), and the old point-guided queue terminated on the
113 analysis error. Do not restart them or overwrite their results.

`launch_hybrid_qualification.py` now runs the fixed nine-slot hybrid ladder
after complete 098/099/101 proof. Actual C4 B2 provenance 123 passes; acquisition
121 remains mutable. `audit_reference_slots.py --references ROOT --lock LOCK
--slots SLOT... --output NEW_JSON` replays selected complete hybrid/original
references without GPU dispatch. It is not whole-corpus admission by default.

`replay_point_guided_physical.py --output NEW_JSON` rechecks all retained 113
outputs and reuses its exact physical/iid analysis with the missing wrapper
fields derived from canonical geometry. Actual post-hoc replay 125 passes;
113 remains FAIL. Plan-036 guarded adapters pin their original sources and
retain all counts/seeds/thresholds/resources. `validate_replayed_point_guided_prefix.py`
executes fresh 126; `launch_replayed_point_guided_qualification.py` waits for
125/126 before one fresh 128 acquisition. Their roots are separate from the
terminal old attempts. Never import original/hybrid moments into those prefixes.

`assemble_replayed_reference_view.py` fixes plan-037 view 127 (fifteen original
plus nine pending point-guided targets). `finish_replayed_readiness.py` accepts
the original finisher CLI; it runs under `continuation-replayed-point-guided-v1`.
It requires full eligibility/provenance and actual reference-work quiescence
before the unchanged pilots, sizing, accepted calibration and final 047.
`readiness_preflight_replayed.py` preserves all six original gates and accepts
the original preflight CLI; actual interim 129 is NOT_READY. Neither a waiting
queue, a scheduling view nor a subset provenance PASS is readiness evidence.

The frozen inputs of each active worker must remain unchanged. Do not relaunch
existing work roots or infer failure from an observation timeout. Terminal
results are indexed only after completion and identity verification; mutable
121/126/128 are explicitly not published as completed results.

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

`qualify_incremental_references.py` implements the unchanged complete ladder
using that variant. It refuses to start unless 009, 022 and 050 are complete
and PASS with matching binary/sampler/proof identities. Each level records the
prior metadata/payload hashes and its actual sample interval; every level
remains scored by the original support-aware assessor. It requires a fresh
directory and never overwrites an existing acquisition. This runner has not
yet acquired references; coordinate any scheduling change only after proof
050 passes and at the completed transport boundary specified by Amendment 6.

`reference_provenance.py --lock LOCK --references ROOT --output NEW_JSON`
validates all 24 reference chains against canonical locked scenes, physical
validation 009, current binary/net identities, each retained f64/component/hit
payload, fixed replicate headers, and a fresh execution of the unchanged
convergence assessor. Exact-prefix variants additionally require the complete
009/022/050 dependency chain and each preceding metadata/payload identity.
`--cells` is only a subset audit and cannot assert readiness. Result 051 is the
executed C7–C12 subset audit (12 transports, PASS); the full corpus is pending.
This new helper has not changed the frozen running completion driver.

The prepared `assemble_reference_view.py` requires the complete 009/022/050
proof chain before creating a fresh, full 24-transport symlink view. Its fixed
scheduling map retains original C1/C3/C7–C12 acquisitions and selects fresh
incremental C2/C4/C5/C6 acquisitions. This map is fixed before incremental
images exist; it never picks an acquisition based on image quality. Pending
links do not imply eligibility. A recorded view is only scheduling provenance,
and all 24 actual references still need final provenance/preflight checks.
This helper has not been executed. Switching the current driver or stopping
an original generator still requires the completed transport boundary and
retained status/partial-attempt record specified in Amendment 6.

`compile_ddgi_reduction.py` completes the official SDK module set required by
unmanaged volume creation: reduction and extra-reduction entry points for
32/64-lane configurations. It verifies the pinned SDK/DXC files before and
after compilation, inherits the bound resource configuration from 038 and
retains commands, diagnostics and SPIR-V bindings/hashes. Actual result 056
is complete/PASS (four CPU compilations); runtime subgroup selection and GPU
validation are still required. Existing frozen compilation helpers are unchanged.

`acquire_ddgi_bringup.py --binary BINARY --shaders SHADERS --reduction REDUCTION
--work NEW_DIR --output NEW_JSON` runs the isolated official-SDK volume adapter
with an AMD physical GPU and no concurrent GPU image producer. The binary name
must begin with `phos-` so the completion driver's concurrency check detects it.
It verifies pinned official shader/SDK files, retains all raw readbacks and
independently scores every RGB/distance component and memory event. Protocol
015 fixes both controls and tolerances before dispatch. Results 057/058 are
actual diagnostic runtime/build evidence; no scene GI, architecture promotion
or performance comparison follows. Existing frozen GPU binaries/shaders remain
unchanged. Validation layers were not run in this diagnostic.

Current transition: 050 is complete/PASS; fresh incremental C2/C4/C5/C6
acquisition runs with 12 threads, and fixed full 24-transport view 061 is
created. Original C1/C3 acquisitions continue. Driver retirement 059 occurred
while idle, before any pilot/calibration. The updated `finish_readiness.py`
freezes all current helpers and proof/binary/view identities; preflight
re-executes convergence and verifies incremental chains, and quiet calibration
rejects both original and incremental qualifier/validation/watcher activity.

`retire_original_qualifier.py --pid ORIGINAL_PID --references ORIGINAL_ROOT
--work NEW_DIR --output NEW_JSON` privately verifies the exact original
C7/C1/C2/C4/C5/C6 parent, waits for a fully completed C1 T_B8 eligible pair or
frozen cap, then retires it at that transport boundary. All original files
and any subsequent partial child are inventoried and retained. It never
changes outcomes or uses partial results; the independent C3 runner finishes
naturally. Its eventual 062 record must be executed before listing complete.

### Interruption recovery

The preceding running-job description is historical: 065 records terminal exits.
Amendment 8 uses `--transports` / `--imports` to copy validated complete prefixes
into fresh work roots, retaining later partial seeds in the original roots.
`assemble_reference_view.py --selection` records an explicit full-24 scheduling
map (067); pass its result using `--reference-view-record` to the continuation
driver and readiness preflight. Neither view nor compiler/build success grants
reference admission. The separate GPU numerical-port diagnostic uses bounded
compilation/runtime and is excluded from the driver's comparison dependency
freeze because it supplies no admitted references or comparison executables.

### Gated high-sample hybrid qualification

`qualify_hybrid_references.py --lock LOCK --transports C1_T_B8 ...
--work NEW_ROOT --output NEW_RESULT [--proof-only]` implements prospective
plan 029. It requires complete 098/099/101 coverage and their recorded bytes,
095/100 build identities and 009 sampler proof before acquisition. It retains
all raw per-seed outputs/ledgers and runs the unchanged four-seed six-level
support-aware screen, stopping at the first qualifying pair or the frozen cap.
It uses only its own complete raw prefix sums/counters; no CPU-prefix import,
accepted-view replacement or default Renderer change occurs.

Actual prerequisite-only invocations 104, 105 and 106 all exited 2 because
098 was incomplete. They dispatched no GPU work and created no acquisition
root. This verifies refusal at that gate, **not** the unexecuted success,
physical, all-state or high-sample acquisition paths. The current script is
the revision recorded by 106. Earlier revisions are archived at
`out/research/n010-comparison-readiness/hybrid-reference-prerequisites-v1/`:

- `attempt-104-script.py`: SHA256 `19d62916181a064a3f8cf0d3e687057ea90c772b466270cd951487b34147a1d3`.
- `attempt-105-script.py`: SHA256 `b59d94ea3f811362d82d39ef228e292430ac86f196fc8504e9595b2542b4c3ad`.

The exact partial-098 input bytes of all three checks are retained there as
`pending-098-df77757d4019fc731b59649a98566fd7526d7f85be99c271d8151ace029819b3.json`,
with SHA256 equal to the filename digest. The live 098 producer may continue
changing its own file; that does not make these historical refusals current
proofs. Source review corrected the later proof filename/payload-root handling
and extended provenance/attempt logging between these revisions. Those later
branches have not been executed. The live CPU qualifiers and continuation-v3
remain unchanged.

### Hybrid raw export and reference provenance

`hybrid_reference_provenance.py --raw-results COMPLETE_DIAGNOSTIC_JSON ...
--output NEW_JSON` performs CPU-only checks of retained raw exports. It checks
every pixel's GStats ABI/length, finite nonnegative sums, exact binary64
mean/moment ↔ raw-sum reconstruction, all four PFM components, primary header,
per-pixel integer-counter sums, fallback metadata and owned-memory replay.
Actual result 108 passes both full C1 B8 8192-spp seed-0/seed-1 exports from
096/107. It launches no GPU work and provides no statistical eligibility.

Its `verify_reference()` API prepares a separate full ladder audit for the
new numerical hybrid variant: prerequisites 098/099/101, canonical scene,
all level/seed/interval commands, raw/copy identities, prefix inputs, moment
exports, counters, support-aware convergence and first qualifying stop. Old
CPU variants delegate to the unchanged original provenance helper. This full
hybrid qualification path remains unexecuted because no such acquired ladder
exists. The existing frozen preflight/continuation do not import this new API,
and a recorded transition/integration is still required before comparison use.

Actual result 109 exercises the new API's original-CPU delegation on all fifteen
currently eligible CPU transports through recovery view 067. It replays every
scene/payload/header/screen/prefix proof, passes all fifteen and confirms frozen
input bytes after the audit. The exact CPU-only invocation source is retained
as `out/research/n010-comparison-readiness/hybrid-provenance-existing-cpu-audit-v1.py`
and hashed in 109. This does not exercise the new hybrid-variant branch or
verify the nine unfinished transports.

### Separate CPU point-guided sampling prototype

Prospective plan 030 registers a sampling/importance-weight candidate for the
same independently validated finite-transport integral. It retains the
canonical geometry/intersection/primary/direct behavior, with cosine branch
0.75 and a geometry/direct-only triangle CDF (area floor 0.10). Null events
remain samples; the deferred visible-surface mixture weight is explicit.

`generate_point_guided_oracle.py --work NEW_DIRECTORY --output NEW_JSON`
builds a standalone CPU executable with O3, no fast math or FP contraction.
Actual build 112 passes; it changes no default Renderer/build graph.
`validate_point_guided_oracle.py --work NEW_DIRECTORY --output NEW_JSON`
executes all seventeen original point-light controls, four seeds and original
counts, then eight fixed analytic/support checks and two retained iid checks.
Actual 113 is executing, not a completed physical proof. Existing output
paths are refused and original/frozen inputs are hashed before and after runs.

No new reference or sampler transition follows from build/control success
alone. All locked-state primary/direct identities, its own exact prefix proof,
a recorded acquisition/provenance transition and the unchanged full corpus
qualification screens remain required. Old cosine moments/prefixes cannot be
imported into this sampler. Existing CPU acquisitions continue independently.

`generate_point_guided_prefix.py --work NEW_DIRECTORY --output NEW_JSON`
copies exact 112 sources and overlays the original strict dyadic-prefix loader
and render continuation, restoring all five counters. Sampling/intersection
source bytes outside render are verified unchanged. Actual build 114 passes.
`validate_point_guided_prefix.py --wait-for-physical-proof --work NEW_DIRECTORY
--output NEW_JSON` waits for complete 113 PASS before launching the fixed plan
031 corpus. It requires 24 low-dose rows, two actual-level C7 rows, all four
seeds and 78 native attempts with zero byte/counter disagreement. Current 115
is waiting (**NOT RUN**); passing build 114 admits no reference. No original
cosine prefix may be used by this sampler.

### Gated point-guided qualification and provenance

`qualify_point_guided_references.py --lock LOCK --work NEW_ROOT --output NEW_JSON`
requires completed 112/113/114/115 proofs and every actual proof payload before
acquiring the fixed nine unfinished transports of prospective plan 032. It
retains all six levels/four seeds/screens/cap, all twenty-one payloads per level,
actual commands/outputs, five counters and its own exact prefix intervals.
Every completed level is replayed by the new provenance API before continuing.
Original cosine/hybrid moments are not imported and the current view is not
replaced. The other fifteen original references remain included in the corpus.

Actual `--prerequisites-only --audit-archive NEW_ARCHIVE` invocation 116 exits
2 at incomplete physical 113, creates no acquisition root and archives every
exact read input byte (eleven files). These archived partial proof bytes are
historical refusal evidence, not hashes of later completed live producer files.
The full acquisition and new sampling variant audit remain unexecuted.

`launch_point_guided_qualification.py --queue NEW_QUEUE --lock LOCK --work
NEW_ROOT --output NEW_JSON` freezes source/build inputs while waiting for
complete 113/115 PASS, then invokes exactly one fresh acquisition with no
retry. The current queue is waiting under `point-guided-qualification-queue-v1`;
result 118 and its acquisition root are absent. Completed dependency failure
stops the queue, retaining status/logs. Acquisition success still requires a
separate recorded view/provenance/scheduling transition before comparison use.

`point_guided_reference_provenance.py` exposes `verify_reference()` for the
new `validated-point-guided-mixture` variant. It audits actual proof scope,
canonical state/scene, all headers/values/component rounding/primary records,
execution outputs/commands/counters, own prefix chains and unchanged first
qualifying stop. Other variants delegate to the existing CPU/hybrid API.
Actual 117 exercises that delegation on all fifteen existing eligible CPU
slots and confirms frozen inputs; it provides no new-variant admission.
Its exact invocation is retained and hashed as
`out/research/n010-comparison-readiness/point-guided-provenance-existing-cpu-audit-v1.py`.

### Exact-source final readiness adapter

`readiness_preflight_point_guided.py` accepts the original preflight CLI,
rejects an existing output, and verifies original source SHA256
`87985c62edd7ad9a7a8e931e0f36264d939a4e4774507fe0653ac9d483857e2c`.
It changes only the reference-provenance import/success description and adds
adapter/original/plan identities. It executes the exact adapted source in a
private namespace: no shared-module monkey patch, original source edit, gate
change or current frozen-driver replacement. All six original gates remain.

Actual interim 119 runs with lock 026/view 067 and the originally declared
static/dynamic/calibration inputs, classifying NOT_READY. All six gate names
and pass/fail classifications match 103; 162 recorded inputs remain unchanged.
The reference gate stops at the first ineligible C1 B8, so this does not attest
all 24 references or exercise the point-guided-reference branch. Missing 044,
048 and 029 remain explicit failures. New sampling use requires a separately
recorded full view/provenance/scheduling transition and a fresh final audit;
119 is retained and does not manufacture absent final 047.
