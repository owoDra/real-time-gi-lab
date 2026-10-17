# N010 prospective intended-batch full-frame execution pilot

2026-10-18 JST; parent f6243976. Freeze this plan and driver before either
native.370 full-frame1spp PASS does not qualify batch16/tile512 throughput.

## Question and unchanged physical scope

At the intended maximum360 layout, is the hybrid sufficiently useful to
continue its execution qualification, or should remaining work use the
existing CPU path? This is bounded execution planning, not GI competition,
environmental stability acceptance or GPU timestamp performance inference.
Require terminal360/366/370 PASS and original254 source/binary identities.

Use original C1_T_B8 scene/net/320x180/depth8, seed305419896, ALL57,600
pixels,16spp. No mask, guard relaxation, new sampler, source rebuild, count
reduction or state/seed substitution. Original24 states,17 artifacts, four
seeds and reference ladder/quality/physical thresholds remain unchanged.
The single selected seed is pilot scope, not four-seed/all-state admission.

## Exact manual steps, finite stop

Driver: scripts/research/n010_reference_sampling/probe_batched_full_frame_hybrid.py
Work: out/research/n010-comparison-readiness/batched-full-frame-hybrid-pilot-v1

1. --step cpu creates371-batched-full-frame-cpu.json. Original254 standalone
   exporter,16spp/one seed/one worker, with original --checkpoints8 support.
   Keep independent full-frame16spp and nested8spp HDR means/moments/PFMs,
   original primary hits, final16spp counters/audit and native receipts. The
   checkpoint contains no independent8spp global proposal/counter metadata;
   do not invent that evidence. It is retained for a possible later prefix
   comparison, not itself a validated restore or a separate CPU acquisition.
2. Only after371 terminal PASS, --step gpu creates372-batched-full-frame-gpu.json.
   Unchanged360 binary/shader, full mode16spp/batch16/tile512, BEGIN0/PREFIX
   '-', one fallback CPU worker.113 tiles,791 depth submissions,921600
   complete scored paths. Last tile256 pixels; all others512.
3. A separate --step summarize creates373-batched-full-frame-hybrid-pilot.json
   only after both terminal PASS and complete input/payload identity checks.

Each native CPU31/nice15/4GiB,300CPU/420elapsed seconds. One native/compiler
at a time, manual invocation only,2GiB free before dispatch, retained work
<=1GiB. Keep360 fixed2ms depth pauses and250ms submit/wait operational guard.
All partials/failures retained; no retries, altered layout, automatically
queued extension or favorable-data repetition. Re-poll a live process after
observation timeout. No power/clock/display/driver/other-app changes.

## Frozen validation and execution choice

Recheck original scene/net/geometry/seed/source/binary/shader hashes and all
prerequisites. Preserve source commit, exact command, actual PID/start and
resources, terminal exit, stdout/stderr and all payload SHA identities.
Check full16spp and checkpoint8spp dimensions/count/seed, finite nonnegative
means/moments and exact bottom-up f32 PFM conversion. Primary hit bytes must
match original C1. CPU own/null/attempt identity and original numerical
guards remain: own-log<=1e-6, conditioned fraction<=1, unconditioned values
retained without a new cut. Checkpoint8 gets no invented counter-audit match.

GPU full stats sums/16 and second moments/16 must equal o.f64 exactly,
every pixel count16, every original selected pixel in order, valid112 schema,
zero GPU faults. Require exact emission/direct means AND moments, primary-hit
bytes, all four global scored counters and proposal query/attempt/null/own
counts versus371. Max absolute error over ALL means/moments<=1e-10 and full
unmasked indirect RGB NRMSE<=1e-8; zero CPU energy requires zero difference.
These are the existing numerical cuts, unchanged after acquisition.

Require audit.bin/metadata exact, finite nonnegative audit maxima, own-log
bound<=1e-6, conditioned fraction<=1, max weight<=8. Verify every113 tile and
791 depth interval, completion and operational wall<=250ms; reconcile every
fallback/reason count and maximum wall with metadata. All aggregate sample
evidence remains, no per-path full-frame dump. Replay owned allocations with
peak<=8GiB/zero teardown; exclude/report CPU and driver-private memory. This
is not Renderer/comparator peak qualification.

Before data, freeze a practical execution choice: retain hybrid as a candidate
only if numerical/integrity/operational checks PASS AND its complete native
elapsed time<=371 CPU native elapsed. Otherwise stop scaling this variant
and continue existing CPU qualification. The ratio1 cutoff is an operational
choice to avoid spending more wall time in this measured fixture, not a
scientific superiority margin, statistically proven acceleration or a GI
quality FAIL. Single-run noise/hardware scope and CPU checkpoint output costs
remain explicit; no inference about general GPU/CPU performance. No further
generic stability tuning or automatic GPU campaign follows either outcome.
Even a favorable16spp ratio does not prove full8192--262144 feasibility or
transfer to all scenes; original physical/bias/state/prefix/intake remains.

References16/24; original full artifacts14/17 including one diagnostic-only
item. Direct relative1.0 pixels UNRESOLVED/未解決 and scored. N010 NOT_READY;
no N011. No CUDA, Actions, default Renderer/build changes or N001--N009 edits.
Unit/regression tests NOT RUN; registered scientific numerical pilot only.
