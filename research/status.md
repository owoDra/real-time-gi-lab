# Current research status (2026-10-19)

## Current decision and execution

**N010 NOT_READY.** N010 is the final preparation study; the next study is
separate Lane M GI competitiveness. No N011. The goal is a valid executable
comparison; an incumbent quality loss is a result and does not block handoff.

- Eligible references: **16/24**. Missing: C1/C2/C3/C4 T_B8 and C5/C6 T_B2/T_B8.
- Compensated sampler: **14/17 full physical artifacts**; original14/17 including
  its diagnostic-only item is a separate historical inventory.
- A6a489–492: **4/4 seeds, pooled analytical physical PASS**, no reference
  admission. Direct allowance has0 violations; indirect relative7.5096e-5 /
  NRMSE7.9006e-5 pass unchanged. All1498 hashes in terminal492 match. Original261
  and prior per-seed records are preserved; this does not prove global bias.
- **Live acquisition:**145 A6b seed0 was separately invoked once after
  publication dd4097aa (nativePID674045/start_ticks8670629/session8893,
  source dd4097aabcf8326a784ac35ffb3731f8df87add3).
  CPU31/nice15/one render thread/7200CPU/10800elapsed/4GiB; sole scientific
  worker, no queue/retry. Mutable493 stays uncommitted/unindexed until terminal.
  The updated optional CPU preference is unanswered; no CPU increase.
- Selected full PT captures: **2/28**. All **8/8 non-PT raw executions** exist;
  descriptive union10/36 is not final-auditor acceptance. Non-PT quality replay
  **4/8**: C7 dense/HWRT/software and dynamic C12 HWRT complete; four pending.
  New POST-HOC714/715 retain12 quality-target FAILs, indirect NRMSE97–98%.
- Sponza direct-relative-error1.0 pixels remain **UNRESOLVED / 未解決**, included.
- No accepted Lane M speed or general GI-superiority result; no architecture
  promotion. Tests **NOT RUN** in the current work.

[Latest full-A6a/quality outcome716](lanes/n010-comparison-readiness/results/716-a6a-full-physical-and-retained-quality-outcome.md),
[terminal execution and full-frame equivalence628](lanes/n010-comparison-readiness/results/628-terminal-seed1-and-thread-private-equivalence.md),
[non-PT/prefix outcomes617](lanes/n010-comparison-readiness/results/617-terminal-seed-full-non-pt-captures-and-prefix-build.md).
A live process receipt is observation, not a passing research result.

## What is established

1. **The incumbent has real quality weaknesses.** Retained static comparisons
   include Sponza C1 B2 indirect NRMSE88.8399%/bias+35.8544% and C3 B2
   NRMSE87.9404%/bias+35.2394%; both fail. Pixel PT256/1024 passes those retained
   cases. Controlled C7 misses roughly91% of indirect energy; dense RC also
   fails. Complete retained static42 rows and controlled dynamic34 histories/
   265 scores include losses; PT1024 passes the retained controlled dynamic
   targets. These are scoped observations, not complete Sponza/dynamic coverage.
   [415](lanes/n010-comparison-readiness/results/415-retained-pt-ladder-proof-replay.json),
   [423](lanes/n010-comparison-readiness/results/423-retained-controlled-dynamic-cohort-proof.json).
2. **Reference and correctness work was necessary.** N007 stopped with bounded
   cross-class reference NO GO and isolated missing probe-shadow visibility in
   its new matched diagnostic frame. N008 validated the independent finite-
   transport oracle, but its cross-class reference set was bounded NO GO.
   N009 concluded SC NO GO/BF1–BF3 PASS/PT INCOMPLETE; Amendment1, V1/V3
   incompleteness and post-hoc sensitivity remain historical facts. No N001–N009
   result is rewritten. [N007](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md),
   [N008](lanes/n008-hdr-oracle/results/011-n008-final-decision.md),
   [N009](lanes/n009-scene-contract/results/009-n009-final-decision.md).
3. **Execution defects have been localized.** Original261's density abort has
   an operand-rounding mechanism; the separate compensated candidate passes
   its local checks but is not fully admitted.507 timing intake mixed binary32
   with binary64;516 intake assumed the wrong static RC counter. Explicit
   post-hoc509/616 replay retained bytes, keeps original failures and quality
   losses, and grants no speed claim. Environment instability is not assumed
   to explain those defects. [451](lanes/n010-comparison-readiness/results/451-compensated-raw-target-candidate-outcome.md),
   [508](lanes/n010-comparison-readiness/results/508-raw-query-pilot-and-posthoc-replay-outcome.md),
   [617](lanes/n010-comparison-readiness/results/617-terminal-seed-full-non-pt-captures-and-prefix-build.md).
4. **Private parallel execution has bounded positive evidence.**621's headers
   permitted threads while its CLI rejected them;626 corrects only that CLI
   scope.627 full/prefix builds pass.623/624/625 show byte-identical six full
   output files and complete audit/counter metadata on C1/320x180/16spp/one
   original seed,1 versus4 render threads on the **same CPU31**. This is not
   multicore throughput, full physical/state/prefix qualification or admission.
   [628](lanes/n010-comparison-readiness/results/628-terminal-seed1-and-thread-private-equivalence.md).

## Completion requirements

The last complete six-gate audit426 was NOT_READY. Later source-only metadata
is not a final gate result.120/147 prospectively separate valid timing evidence
from timing precision. Final state-bound auditor619 has **NOT RUN**.

| Requirement | Required next evidence |
| --- | --- |
| Eligible locked physical references | After A6a PASS, finish A6b/A10 all4 seeds, A6b IID and separate level5 diagnostic; complete density/support/Jacobian/numerical-bias assessment, full state/prefix, whole-frame two-level feasibility and unchanged reference qualification for all8 missing slots. |
| Correctness and explicit discrepancies | Keep full physical/state/key checks and all pixels. Report direct-relative1.0 as unresolved; no masked acceptance or retroactive V1/V3 repair. |
| Whole-corpus dynamics/quality/memory | Finish Sponza C2–C6 histories and all selected boundary captures/replays; retain owned persistent/true-peak allocation/free evidence and zero teardown. |
| Frozen ladders/quality selection | Complete C1 B8 ladder once its reference is eligible; retain every failed budget and full-pixel score. |
| Valid timing pilot and selected execution | Complete the original16 plus selected28 union36 scope, with native/state/budget/raw-query/fence/ledger proof; execute160 final intake/auditor. Complete valid timing may remain TIMING_INCONCLUSIVE; missing/invalid data still blocks. |
| Additional family/device boundary | DDGI source is pinned and Vulkan host SDK/CPU compiler evidenced. N010 RC/PT handoff does not invent a DDGI runtime gate; integrated DDGI correctness/quality/cost qualification precedes accepted DDGI comparisons in Lane M. |

[Last complete audit427](lanes/n010-comparison-readiness/results/427-selected-scope-readiness-audit-outcome.md),
[160 full36 intake source618](lanes/n010-comparison-readiness/results/618-state-bound-selected-adapter-description.json).
All-split reference admission/dispatch remains unfinished and fails closed.
[614](lanes/n010-comparison-readiness/results/614-compensated-density-support-source-assessment.md)
is only a partial post-hoc ideal-measure/source assessment: its2^-30 selection-
only bound is **not** a native radiance-bias bound.

### Executed replays and prepared routes

- 166 POST-HOC714/715 are **complete**:517 static-C7-software (both transports)
  and519 dynamic-C12-HWRT (all5 frames/both transports), using eligible C7/C12
  chains,160 full intake and unchanged full-pixel scoring. All12 targets FAIL;
  valid evidence, no accepted speed. Source capture bytes remain unchanged.
  Four remaining new replays are513/514/515 static C1 and518 dynamic C6,
  pending their required eligible references; no recapture is needed for these.
- Original compensated full state/prefix route157:78 natives532..609 and
  summary610 **NOT RUN**. Prefix526 builds only.
- Private route165/629 retains the same full78 cases, scientific analysis and
  prerequisites;630..707/708 **NOT RUN**. Four render threads remain on one CPU.
  Physical-evidence transfer requires a justified assessment; it is not automatic.
- 158 raw-chain reader611/612 and161 level-I/O component620 are not an admission
  API. Actual612 raw replay and scientific acquisition/feasibility launcher remain
  unfinished;620's CLI only describes source.
- 160's whole36 corrected state/snapshot route618 exists;619 final audit **NOT RUN**.

[629](lanes/n010-comparison-readiness/results/629-private-state-prefix-description.json),
[620](lanes/n010-comparison-readiness/results/620-compensated-single-level-io-description.json).

## Measurement and host policy

GPU timestamps over the complete Renderer are the performance axis. CPU wall,
GPU busy/clocks, other-app activity and global free VRAM are diagnostics.
Owned persistent/startup/recurring true peaks, full quality and provenance remain
required, with the unchanged8GiB owned cap and zero teardown. Additional idle/stability or known-work campaigns are optional for
N010 handoff. Lane M speed claims still require actual-boundary precision,
matched quality, uncertainty and the frozen practical effect margin1.20.

Lane K's5% calibration is not transferable to Lane L's heavy20% boundary or
these pilots. Preserve active GPU sum, complete yield envelope and readback
separately for continuation PT. Its added persistent state is921600bytes at
320x180; exact two-image046 equivalence is scoped evidence.
[406](lanes/n010-comparison-readiness/results/406-continuation-pt-equivalence-outcome.md).

Keep one-core low-priority acquisitions pending the optional CPU preference.
621 planning from old371 projects ~30.4h for four8192 seeds at one core, above
original12h elapsed guard. It is post-hoc planning, not candidate throughput,
a feasibility verdict or an ETA. Do not blindly launch the oversized route or
relax stops. No clock/power/display/driver/app changes or unrelated process kills.
AMD/Vulkan is the current device boundary; CUDA is not used.

## Current architecture

| Subsystem | Current incumbent / classification | Evidence and boundary |
| --- | --- | --- |
| Work producer | **Adopted:** A001 GPU visibility-driven Split RC, natural append order; no global reorder | [Lane A](lanes/lane-a-split-rc/results/index.json), M0; Lane D does not supersede A001 |
| Primary traversal | **Adopted on measured Radeon 8060S:** HWRT/TLAS | [Lane B](lanes/lane-b-traversal/results/index.json), [I001](integration/results/index.json) |
| HWRT-free traversal | **Adopted fallback:** Segment DDA/hash + conservative quantized Micro BVH8 | Lane B B003; lower-tier alternative, not claimed universally equal to HWRT |
| Radiance storage | **Adopted baseline:** C001 per-probe open-addressed sparse hash | [Lane C](lanes/lane-c-storage-locality/results/index.json); page/clipmap variants conditional |
| Dynamic ownership | **Adopted incumbent:** immutable static, transform-only rigid, object-local deform UPDATE, object-local rebuild for topology changes | [Lane E](lanes/lane-e-dynamic-geometry/results/index.json), [timing revalidation](lanes/lane-e-timing-revalidation/results/) |
| Dynamic backend replacements | **Not promoted:** transient LBVH, clustered two-level variants | [Lane M](lanes/lane-m-topology-backend-crossover/results/); Lane E incumbent retained |
| Full Renderer | **Working research implementation:** N001–N004 and separate N005/N006 experimental variants | [Lane N](lanes/lane-n-end-to-end-renderer/results/index.json), [N005](lanes/n005-adaptive-tracing/), [N006](lanes/n006-interval-aware-allocation/) |
| N005 adaptive tracing | **REFINE / conditional:** no universal policy accepted | [N005 evidence](lanes/n005-adaptive-tracing/results/) |
| N006 interval-aware allocation | **STOP:** Q8 influence exists; +4-ray signed HDR quality lift not detectably proven; do not initiate P2/P3 | [N006 final result 045](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) |
| N009 scene contract / back faces / probe attribution | **Concluded:** SC NO GO, BF1–BF3 PASS, PT INCOMPLETE; C1/BF-P remain opt-in | [N009 final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md); no architecture promotion |

N-series Renderer sources/shaders are pinned imports. Historical source presence
does not activate an old lane or change the default build. This checkpoint
promotes no new executable behavior to research/main.

## Earlier results and open scientific questions

N003's reported2.35–3.11x speedup versus its tested vanilla Split RC cases costs
~24–27% additional GPU memory; it is not a general same-quality GI comparison.
Lane E's accepted object-local recurring-boundary improvements remain scoped
results. Historical Lane M topology alternatives did not qualify; they are
separate from upcoming GI competitiveness. N004 detected motion weaknesses;
N005 has conditional findings and no universal accepted policy; N006 found no
detectable signed HDR improvement and remains stopped.

The next question is the measured quality/GPU-time/owned-memory/dynamics tradeoff
against matched RC, PT and DDGI families, followed by structural improvements
motivated by those measured losses. Multiple scenes/devices are required before
a general superiority claim. [Research charter](../docs/research.md),
[roadmap](roadmap.md), [protocol](protocol.md).

This is AI-assisted research with human oversight; actual retained hardware
measurements are evidence, and unavailable verification is never implied.
[Workflow disclosure](../docs/ai-research-workflow.md).

## Provenance

Detailed outcomes: [N010 results index](lanes/n010-comparison-readiness/results/index.json).
The previous long status/roadmap/README chronology is retained byte-for-byte as
historical text snapshots with source SHA/blob/hash identities in
[712 consolidation record](lanes/n010-comparison-readiness/results/712-current-summary-consolidation.json).
Those snapshots are provenance, not competing current summaries. No historical
result, failed run or accepted raw byte is changed. Tests **NOT RUN**.
