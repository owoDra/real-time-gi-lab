# N010 — final comparison preparation

N010 is the final preparation study before **Lane M GI competitiveness**. It
must deliver executable comparisons, eligible references, correctness evidence,
quality matching, calibrated GPU timing and allocation-lifetime memory records.
The historical Lane M topology study retains its existing identity and results.

Protocol: [001](experiments/001-comparison-readiness.md). N001–N009 are immutable
inputs. The default Renderer is not promoted by this study.

Status: active; readiness has not been demonstrated. [Execution evidence and
remaining gates](results/008-interim-execution-and-resume.md). Actual GPU-key
replay passes on all 10 captures; the C7 key-driven counterfactual validation
passes V1–V4 on both backends. Direct shadow-offset diagnosis is post-hoc;
new physical sampler validation and comparison harness work continue.

**Current execution:** [130](results/130-validated-reference-acquisition-and-comparison-transition.md).
Hybrid numerical/physical/state/prefix proofs 098/099/101 are complete PASS;
actual first-reference provenance [123](results/123-first-qualified-hybrid-provenance-audit.json)
passes C4 B2 at 16384/32768 with 5,413 unchanged read identities. The hybrid
queue continues. At the user's request, both old CPU recovery jobs were stopped
with all complete/partial files retained (124); idle comparison waiter 120 was
retired without jobs. Point-guided 113 remains FAIL after an analysis wrapper
error; post-hoc replay 125 passes the original physical/iid checks without new
rendering. Fresh [126](results/126-replayed-point-guided-all-state-and-prefix.json)
now passes all 24 low-dose/two actual-level cases and 78 native attempts;
[131](results/131-replayed-point-guided-proof-chain-audit.json) rechecks the complete
proof chain. Fresh nine-slot acquisition 128 has actually started. These runs
and comparison view 127 are separate from the historical failed attempts.
New comparison execution waits for
all 24 eligible references, complete provenance and quiescence. Interim
preflight 129 is **NOT_READY**; final pilots/calibration/047 remain pending.

## Earlier execution checkpoints

The progression below records earlier checkpoints. Use the current section
above and `research/status.md` for present process and reference status.

New executable cohort: native GPU pixel PT and the separately frozen dense
repository RC estimator control. [C7 budget/quality results](results/013-c7-pt-cohort-pilot.json)
include all losses and passing PT levels. [Construction lock](results/016-corpus-state-lock.json)
contains source/target dynamics and local light motion. C7 and C8–C12 references
are eligible in both finite transports. The [dynamic cohort](results/019-controlled-dynamic-cohort.json)
retains all 145 executed source/target/recovery images, all losses and two
explicit software-churn capture limitations; [independent memory replay](results/020-controlled-dynamic-summary.json)
passes for all 29 roles. Sponza C1/C3 T_B2 references now qualify. [C1 quality comparisons](results/033-interim-comparison-findings.md)
show incumbent/dense RC FAIL and pixel PT PASS at 256/1024 spp. Remaining
Sponza reference acquisition and calibrated timing are in progress.
Historical vanilla-software is a traversal control, not a separate GI baseline.

[RTXGI provenance](results/021-ddgi-source-provenance.json) pins the fetched SDK
for the required additional Lane M DDGI comparator. The chosen path is Vulkan
on AMD, without CUDA. The [Vulkan host SDK builds](results/023-ddgi-vulkan-host-build.json)
and the [pinned CPU DXC runs](results/034-dxc-cpu-compiler-provenance.json);
integrated DDGI runtime is not yet demonstrated.

[Post-hoc CPU primary diagnosis](results/053-residual-primary-contract-diagnosis.md)
localizes both residual C1 direct-zero pixels to differing primary primitives
and supports a legacy tie-interval mechanism. No GPU repair is claimed; both
pixels remain unresolved and included in scoring.

[Cache equivalence](results/022-cached-oracle-equivalence.json) is complete and
PASS in all 20 cases. The [controlled reference provenance audit](results/051-controlled-reference-provenance-audit.json)
rechecks C7–C12, both transports: canonical scene/state, four fixed seeds,
all component/f64/primary-hit hashes, and every original convergence screen.
All 12 pass. This is a subset audit; remaining Sponza references and the full
readiness gate are unfinished. Incremental equivalence 050 is now complete/PASS in all three declared
cases. Reference jobs and the waiting driver terminated (065), with cause unestablished.
Complete prefixes and partial later seeds are retained. Amendment 8 prepares
fresh acquisitions from the validated complete C1 T_B8/C3 T_B8/C2 T_B2
prefixes; view 067 fixes all 24 slots before recovery output. Prior view 061 and
statuses are historical. GPU numerical-port compilation/build (066/068) are
isolated diagnostics and establish no reference eligibility.

The unmanaged SDK also validates reduction shader modules/pipelines even when
variability is disabled. [Result 056](results/056-ddgi-reduction-shader-compilation.json)
compiles both official reduction entry points for 32/64-lane configurations,
using the pinned DXC and SDK. All four compile. Runtime must select the shader
against supported subgroup configuration; this is CPU compilation, not an
integrated DDGI GPU execution or quality result.

[Official SDK GPU volume bring-up](results/057-ddgi-volume-runtime-bringup.json)
now executes on Radeon 8060S/RADV with subgroup width 64. Both preregistered
constant-field controls pass every irradiance/distance texel, including borders:
maximum errors 5.96046e-8 / 2.98023e-8. Owned Vulkan peak is 131,472 bytes,
20 lifetime events independently replay to zero teardown. The standalone build
is [058](results/058-ddgi-volume-build.json). No default CMake/Renderer changes.
This is resource/dispatch normalization wiring: scene tracing, finite-depth
transport, surface gather and dynamic histories remain unimplemented. It is
not DDGI frame-quality qualification or a calibrated timing result.

Historically, recovery executed C1 T_B8 16384→32768 and C2 T_B2 8192→16384 in
two 16-thread qualifiers. Continuation-v3 used view 067; its later retirement
and the user-requested CPU stops are recorded in 120/124. C7 T_B2
GPU numerical-port conformance at 16 spp passes (070), with exact counters and
max mean discrepancy 2.71051e-20; this does not grant reference eligibility.

C2 T_B2 recovery is now eligible at 16384/32768; independent canonical/
payload/prefix-chain audit 080 passes, scoped to this one transport. C1/C3
T_B8 and the remaining slots still run. GPU conformance 074 preserves its
120-second Sponza guard failure; prospective 075 uses the recorded 900-second
guard. First C1 T_B2 8192 numerical comparison passes with exact counters and
max mean difference 1.73472e-18. GPU references remain ineligible pending
full numerical, physical-control, all-state and actual-level prefix proof.

The resource follow-up 075 is now terminal: twelve cases pass, then the first
C1 T_B8 case times out at 900 seconds without numerical output. 075 remains
failed; 081 records that conditional physical/prefix workers refused dispatch
(NOT RUN). Plan 021 starts 082 with the twelve unchanged completed cases and
a fresh 1800-second guard for the remaining four. New conditional workers
use 082 and fresh work roots; no GPU reference is admitted.

### Completed deep GPU numerical failure

082 completed C1 T_B8 seed 0 (8192 spp) but failed unchanged Amendment 7
gates: mean 6.78235e-7, moment 5.31950e-9, indirect NRMSE 2.94757e-6,
shadow-test/blocked counter differences +26/+31. Primary/direct/emission
remain byte identical. The candidate is ineligible; dependent physical and
all-state/prefix runs refused dispatch (085, NOT RUN). 084 maps 54 affected
pixels as post-hoc diagnosis; plan 022 uses eight selected pixels to replay
and intervene on sampling arithmetic. No exclusions or relaxed thresholds.
CPU reference recovery continues independently; 15/24 slots are eligible.

Post-hoc intervention 087 reproduces all eight selected original CPU/GPU
payloads byte exactly. Supplying CPU trigonometry removes the discrepancy
in two pixels (13450, 55934), with exact counters and mean error <=4.34e-19.
Six pixels retain mean/moment/counter discrepancies. Trigonometry alone is
insufficient; full causation is unestablished and no GPU reference is admitted.
Plan 023 records path/bounce diagnostics with aggregate replay required.

Deep-path diagnosis 089/091/092 reproduces every selected aggregate/counter
and establishes a signed-zero sampling-basis mechanism in all eight traced
original paths: nearby coplanar closest primitives have opposite zero signs
in normal.z, producing large next-direction changes under identical uniforms.
CPU sign-bit-only direction intervention matches the original CPU direction
exactly (8/8); the other 46 above-gate pixels are not individually traced.
Plan 024 tests a general ambiguity flag and independent complete CPU-path
recomputation, with all samples retained and unchanged admission gates.
It is a separate candidate; 082 remains failed, GPU references unadmitted.
The Renderer direct-zero pixels remain unresolved.

The general ambiguity-guard/whole-path CPU fallback feasibility 093 passes
unchanged numerical/counter/finite/direct/emission gates on all eight selected
pixels (mean <=8.674e-19, moment <=1.017e-20). It recomputes 11864/65536
paths without reference-radiance or hit/sign overrides. Audit 094 replays
all diagnostic GPU memory ledgers, verifies separate build 095 and confirms
53 frozen continuation inputs remain unchanged. Plan 025 streams the same
guard over complete frames with bounded per-dispatch storage. Its first full
C1 T_B8 seed-0 trial 096 has now passed; full sixteen-case/physical/all-state/
prefix admission remains unexecuted. CPU acquisition remains independent.

C1 T_B8 recovery now completes all four 32768-spp seeds with verified prefix
provenance (097). Active absolute p99 3.54031e-5 exceeds the fixed 1e-5 gate;
relative p99 2.51347% alone does not qualify the reference. The original
qualifier continues at 65536 spp. The remaining cap outcome is unmeasured.
Full-frame hybrid deep trial 096 completed with the frozen 64-epsilon
guard and original CPU fallback, 16-sample batches / 16 CPU workers. No GPU
reference is admitted from the selected success or the standalone build.

Full-frame C1 T_B8 seed-0 feasibility 096 **PASS** at unchanged gates:
max mean difference 1.38561e-16, moment difference 3.59820e-18, indirect
NRMSE 4.10311e-16, exact counters/primary/direct/emission, finite output, zero
faults and owned-memory replay PASS. CPU fallback recomputed 40861185 of
471859200 paths (~8.66%), with every path retained. Original 082 stays failed.
The new complete numerical suite 098 is executing; physical worker 099 waits
for that complete PASS. Separate prefix host build 100 succeeds, but prefix
runtime validation is NOT RUN. No reference admission or N010 READY yet.

### Completion evidence inventory

[102](results/102-completion-evidence-and-handoff.md) maps each unchanged
completion requirement to executed evidence, pending work and the runnable
final verification command. Actual full-gate preflight [103](results/103-interim-full-gate-preflight.json)
is NOT_READY: correctness accounting and additional-family source/device
boundaries pass, while full references, Sponza pilots and accepted timing
calibration remain pending. It is an interim check, not final result 047.

Prospective [hybrid acquisition plan 029](experiments/029-hybrid-reference-acquisition.md)
and `qualify_hybrid_references.py` now prepare a fresh, proof-gated high-sample
ladder without changing the live CPU view. Prerequisite checks 104–106 refused
GPU dispatch while 098 was incomplete (exit 2, no work root). Successful proof
validation/acquisition remains unexecuted; reference admission still requires
all unchanged gates and a separate completed-boundary provenance transition.

Full-frame C1 T_B8 seed 1 [107](results/107-hybrid-full-frame-deep-seed1-conformance.json) now passes
the unchanged numerical gates: maximum mean difference 8.67362e-17, moment
6.28498e-19 and indirect NRMSE 3.65583e-16; exact counters/primary/direct/emission,
finite output, zero faults and memory replay PASS. It is an exact-byte copy
of the completed 098 child result, not a repeat acquisition. The suite now
has 14/16 passing cases and proceeds to seed 2. Physical/all-state/prefix
proof and statistical qualification remain required; no reference is admitted.

CPU-only [raw-prefix export audit 108](results/108-hybrid-deep-raw-prefix-export-audit.json)
passes all pixels of both retained C1 B8 8192-spp seed-0/seed-1 cases: raw
sums/moments reconstruct saved binary64 values exactly, per-pixel counters
reproduce global metadata, all four PFM components agree, and memory replay
passes. This is a two-export consistency audit, not full prefix/runtime or
reference eligibility. A separate hybrid provenance API is prepared; the
existing frozen CPU view/preflight remains unchanged.

Existing eligible CPU-slot [provenance audit 109](results/109-existing-eligible-cpu-provenance-audit.json)
passes all fifteen selected references via the separate API's original-method
delegation: C1/C2/C3 B2 and C7–C12 both transports. Every canonical scene,
payload/header, convergence screen and imported-prefix chain is checked; all
recorded inputs remain unchanged after the audit. This is a selected fifteen-slot
audit, not whole-corpus readiness or execution of the new hybrid-variant branch.

C1 B8 / 8192 spp seed 2 [110](results/110-hybrid-full-frame-deep-seed2-conformance.json) passes
unchanged full-frame numerical gates, with exact counters/primary/direct/emission,
finite output, zero faults and owned-memory replay. This exact-byte copy of
the completed 098 child is not a repeat acquisition. At publication of 110, suite 098 had 15/16
cases passing and was executing the final seed; full physical/all-state/prefix
and statistical qualification are still required before reference use.

Full numerical suite [098](results/098-hybrid-full-numerical-conformance.json)
now completes all sixteen fixed cases with PASS. Physical 099 has started;
all-state/prefix 101 remains waiting. Numerical completion alone admits no
reference. All sixteen child result hashes were verified before publication.

Separate prospective [point-guided CPU sampling plan 030](experiments/030-prospective-point-guided-reference-sampling.md)
retains the original physical target and exact convergence gates. CPU build
[112](results/112-point-guided-oracle-build.json) passes and physical/iid
control acquisition 113 is executing. It changes continuation sampling and
importance weights only; it does not change the current Renderer or replace
any pending/accepted original reference.

Prospective [state/prefix plan 031](experiments/031-point-guided-state-and-prefix-validation.md)
requires all 24 original locked scenes/four seeds at 16 spp, exact direct/emission
and primary identities, zero own-prefix payload/counter disagreement at 8→16,
and both C7 transports at 8192→16384. Separate prefix build
[114](results/114-point-guided-prefix-build.json) passes. Runner 115 waits for
complete physical 113 PASS and has executed no state/prefix acquisition yet.
Neither build proves convergence or reference admission.

[Point-guided acquisition plan 032](experiments/032-point-guided-reference-qualification.md)
prepares all nine unfinished transport ladders, retaining the other fifteen
in the full corpus. [116](results/116-point-guided-qualification-prerequisite-check.json)
actually refuses acquisition at incomplete 113; all read bytes are archived.
The queue waits for complete 113/115 PASS before a single fresh acquisition.
No new sampling reference, successful new-variant audit or view replacement
has occurred. [117](results/117-point-guided-api-existing-cpu-provenance-audit.json)
passes only delegation to the existing audit on the fifteen original CPU
references. It does not attest new sampling, remaining nine slots or readiness.

[Readiness adapter 033](experiments/033-point-guided-readiness-adapter.md) keeps
all six exact original gates while dispatching reference audits through the
separate API. Actual [119](results/119-point-guided-adapter-interim-preflight.json)
executes against current view 067 and remains NOT_READY, retaining incomplete
reference/Sponza-pilot/calibration gates. The six gate names/pass classifications
match 103; all 162 recorded inputs were checked unchanged after execution.
No new sampling branch, current view/driver replacement or final 047 is attested.
