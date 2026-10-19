# N010 — user-requested project suspension (2026-10-19)

## Decision

**PROJECT PAUSED. N010 NOT_READY / INCOMPLETE.** The user requested that research
resources move to other projects, with possible resumption after model capability
improves. There is no technical need to keep a process running or to finish another
measurement before pausing. This is a suspension checkpoint, not N010 completion,
a new scientific NO GO, reference admission, or promotion to Lane M/main.

No further acquisition, diagnosis, retry or queue is authorized during this pause.
The research goal is paused. Resume only on an explicit user request. N010 remains
the last preparation study; any eventual comparison study is separate Lane M,
without N011. No existing result, threshold or accepted evidence byte is changed.

## Last acquisition: terminal failure before the stop request

[737 terminal record](737-four-core-c1-b8-feasibility-8192.json) is
`INCOMPLETE_NO_RETRY_PARTIALS_RETAINED`, `complete=true`, `pass_=false`,
`reference_admission=false`. Here “complete” means the controller produced a
terminal record; the scientific acquisition is incomplete. Full C1 T_B8,
320×180, 8192 spp and four original seeds were intended. Only seed0's five
payloads plus the shared hits file survive; these do not constitute a reference.

The native had already exited with **returncode -6 (SIGABRT)** before the stop
action. Driver PID797441/start11011629 and native PID798642/start11035451 were
confirmed absent; the observer also terminated. **No stop signal was sent.**
There is no remaining owned acquisition or queued next step. Reserved 738
(16384 spp) and 739 (summary) were **NOT RUN**.

The stderr terminates with:

```text
terminate called after throwing an instance of 'std::runtime_error'
  what():  conditioned raw-target/plane reconstruction error
```

This identifies the immediate guard failure, **not its detailed root cause**.
The responsible pixel/path/operands have not been diagnosed. Earlier bounded
`unmatched target` messages do not establish the cause. This is not attributed to
GPU load, environment variability, the user's pause, or a resource time limit.
CPU32135.752459 seconds / elapsed8117.664288668006 seconds were below the
original CPU172800 / elapsed43200 second ceilings; the original 4 GiB limit,
four render workers on CPUs28–31 and nice15 profile were retained. Timing here
is offline diagnostic information, not comparative GI performance.

The controller's generic `native/actual resource failure; retain all partials`
label is preserved verbatim in 737; the observed stderr above gives the more
specific immediate failure. No post-hoc diagnosis or repair was performed while
preparing this suspension checkpoint.

## Frozen provenance and local evidence

- Acquisition source commit: `7e0520686a7a492f62d152c963345421cba5f0d9`.
- Published pre-suspension checkpoint: `66b35f9bf35043573a6a0cac1b825ca16041e26b`.
- 737 SHA256: `aa86b68e74b1b21f53981beaf6aaba96d5be9deae5f6492c3042bcd25b81e410`.
- Attempt SHA256: `aec8fbad8419c0e47740c2629cc65e218759a339420397dea60537f61f0c46a8`.
- Stderr SHA256: `d969d2aa58fb6a58d5d82fcd5a384f182c2976a8b2677a40183042dd47b84b2b`.
- Stdout SHA256: `f5f84e6f558159a0e576e58cfb8f07d6a0722b5ada42c2326c9ec4d03485a0b2`.
- Resource receipt SHA256: `fb1fc2fbef4d52bbfeae31f7d98b981df47fb448b3d8d245a2937bc196262ea2`.

Native files remain under
`out/research/n010-comparison-readiness/private-four-core-reference-ladders-v1/C1_T_B8/`.
Do not clean `out/`, overwrite this failed attempt, or reinterpret partial seed0
as eligible evidence. All5006 input identities in terminal737 and the retained
attempt/stdio/receipt/six partial payloads were independently hash-checked.

A separate local uncompressed archive preserves all11 files in that failed
native directory, terminal737, the exact627 prefix binary, generated prefix
header/main source and the exact sampling-net file: **16 members**. Their bytes
were read back from the archive and verified against the manifest.

- Archive: `/var/owo/workspaces/artifacts/gi-lab/n010-suspension-20261019T130319Z/n010-737-failed-native-evidence.tar`
- Size: **80578560 bytes**.
- SHA256: `407c8f446eeb125b41ef14762236314990142f55f80a323627af039ab1c50590`.
- [Committed copy of the archive manifest](evidence/740-suspension-local-archive-manifest.json)
  records exact paths, sizes and identities, including all six partial payloads.

**The archive is local, not uploaded with Git, and is not a complete backup of
all5006 prerequisite inputs or the historical evidence corpus.** A Git clone alone
does not restore this native attempt or all prerequisites. Preserve the local
archive and existing `out/` tree if moving machines. No claim of an independently
reproduced or fully portable scientific checkpoint is made.

## What was learned, and what remains incomplete

The incumbent has demonstrated scoped quality weaknesses: retained C1 B2 indirect
NRMSE88.8399% and C3 B2 NRMSE87.9404% fail, while retained pixel PT256/1024 passes
those controlled cases. New retained714/715 replays include12 target FAILs around
97–98% indirect NRMSE. These are useful negative findings, not a general comparison
of existing GI methods. All quality losses remain recorded.

Reference preparation established16/24 eligible slots, complete physical controls
(16 gated PASS plus one separate NOT_GATED diagnostic), independent A6b IID PASS,
and78/78 state/prefix steps across26/26 cases with exact restored comparisons.
These checks localize some implementation defects and provide scoped positive
controls; they do not prove zero global finite-arithmetic bias or admit the
compensated candidate. [735](735-independent-compensated-density-and-bias-assessment.md)
is explicitly a post-hoc assessment permitting only unadmitted feasibility;
[736](736-four-core-reference-scientific-preparation.json) validated prerequisites.
737 then failed at an actual full-scene acquisition. Preparation has not delivered
the complete comparison promised for N010, and its cost now warrants pausing.

Outstanding work, preserved without relaxed criteria:

1. Diagnose the precise737 numerical guard failure and independently review the
   finite-precision estimator/admission argument. Do not blindly retry the same
   attempt, overwrite evidence, loosen the guard or infer whole-scene validity
   from the smaller passing controls. Any repair needs explicit qualification.
2. Complete whole-frame feasibility and reference admission for missing
   C1/C2/C3/C4 T_B8 and C5/C6 T_B2/T_B8. Original four seeds, all pixels, six
   levels8192…262144, active absolute p99≤1e-5/relative≤5%, stable support,
   two consecutive qualifying levels and first qualifying stop remain unchanged.
3. Finish Sponza dynamics, C1 B8 quality ladder, required selected capture/replay
   and state/budget/raw GPU query/fence/owned persistent and true-peak memory
   evidence (8 GiB cap, zero teardown). Selected PT raw2/28; non-PT raw8/8;
   non-PT quality replay4/8. Final state-bound auditor619 is **NOT RUN**;
   last complete six-gate426/427 remains NOT_READY.
4. Keep Sponza direct relative-error1.0 pixels **UNRESOLVED / 未解決**, included.
   Preserve N009's SC NO GO/BF1–BF3 PASS/PT INCOMPLETE, Amendment1,
   V1/V3 INCOMPLETE and post-hoc sensitivity analysis as historical facts.
5. Only after the existing N010 gates, publish the distinct Lane M executable
   handoff. RC/PT is the initial cohort; DDGI source/host builds use Vulkan/AMD,
   without CUDA. Qualify DDGI runtime before any accepted Lane M DDGI comparison.

Timing amendments120/147 already distinguish validity from precision: complete
valid pilot timing may remain TIMING_INCONCLUSIVE; missing/invalid evidence still
blocks handoff. CPU wall, clock/busy/other apps and global free VRAM are diagnostic.
Lane M speed claims still need matched quality, calibrated actual GPU boundary,
registered uncertainty and the1.20 practical margin. No further environment
stability campaign is required by this suspension decision.

## Suspension checks and limits

Only evidence preservation and metadata/hash/index/link/Git checks were performed
for suspension. No new scientific acquisition, build, tests, GPU runtime checks or
root-cause investigation: **NOT RUN**. Source, shaders, active build graph,
N001–N009 results and host settings are unchanged. No Actions, power/clock/display
changes, accepted GI superiority claim or architecture promotion were added.

Model improvement can be a reason to reconsider the project; it is not evidence
that the unresolved estimator or comparison gates will then succeed. On explicit
resumption, first read this checkpoint and the frozen737/735 evidence, verify
local artifacts and current source identities, and decide whether a bounded
attempt at the known blocker is justified before restarting compute.
