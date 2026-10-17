# N010 prospective eight-pixel all-split hybrid numerical diagnostic

2026-10-18 JST. Before build352, CPU probe or any GPU acquisition. This plan
does not dispatch anything while original CPU259 remains live. Parent is
7c89075 plus the unexecuted110 primary/coincidence/probe source clarification.

## Question and immutable scope

Can the isolated110 Vulkan FP64/Int64 prototype reproduce selected254's
original all-split C1 diagnostic, with entire flagged samples recomputed by
the identical CPU oracle? This is an execution-backend numerical question,
not an independent physical proof, bias proof, reference qualification or GI
performance comparison. Outside the eight fixed pixels is uncomputed; sparse
full-size outputs are NOT eligible images. No masks or excluded observations.

Require352 terminal build PASS, all generated payload identities, terminal
254/257 PASS and no scientific worker. Original C1_T_B8 scene and net come
from254's paired-data acquisition command and its frozen input identities.
Use the original fixed eight pixels, original four seeds, original8192spp
and all32 pixel/seed records in254 paired-data.json. Compare mixture_mean /
mixture_second, NOT the earlier mean / second (a different sampler).

## Explicit steps, no queue

Driver: scripts/research/n010_reference_sampling/acquire_whole_path_hybrid.py
Work: out/research/n010-comparison-readiness/whole-path-hybrid-diagnostic-v1

1. One explicit --probe invocation creates353-whole-path-hybrid-probe.json.
   Run original CPU sample_all_split at sample index0, seed305419896, for all
   eight pixels, then a separate GPU native with1spp/batch1/one CPU fallback
   worker. CPU probe:30CPU/60elapsed; GPU native:60CPU/90elapsed seconds.
   Both CPU31/nice15/4GiB. Retain independent CPU components, moments, primary
   and cache/scored counters, GPU streams/primary/ledgers and all receipts.
2. Only after353 PASS, one explicit --seed-index 0..3 invocation creates
  354..357-whole-path-hybrid-seedN.json. One GPU native8192spp/batch16/one
   CPU fallback worker,360CPU/600elapsed, CPU31/nice15/4GiB. Prior seed parts
   must PASS before the next; no process is automatically queued or retried.
3. A separate --summarize invocation creates358-whole-path-hybrid-numerical.json
   only after all four parts terminal PASS. Preserve their immutable hashes,
   all32 pairs and every raw/corrected path/flag; no pooled external samples.

All limits are operational bounds. A timeout,250ms submit/wait wall guard,
device error or incomplete stream is a retained stopped/failed diagnostic,
not an algorithm-quality loss or measurement-stability gate. Observation
tool timeout does not terminate or authorize restarting a live native. No
settings/app changes. Only one scientific native, compiler or GPU worker at
a time. No automatic launch when an existing process exits.

## Frozen validation

For each pixel: exact direct/emission means AND second moments; exact four
scored integer counters; original primary(t, triangle, front) bits. Over all
12 component/channel values per row, max absolute mean and second-moment
error<=1e-10, and indirect RGB NRMSE<=1e-8 across all eight rows. These retain
the earlier hybrid numerical tolerances; no new tolerance after viewing data.
Zero CPU signal requires exactly zero difference, otherwise fails.
All values finite/nonnegative, GPU fault flags zero, dimensions/depth/seed/
sample count/geometry correct, and owned allocation ledger replays exactly
to zero with true peak<=8GiB (CPU/driver memory excluded and reported as such).

The1spp probe validates the manually assembled GPU-host primary/cache against
independent original CPU sample_all_split, as well as its corrected path.
The CPU primary cache is seed independent in this locked center-camera,
one-point/nonemissive scene: direct() consumes no random draw, and its scored
cache shadow counts are reused per sample. For8192spp expected shadow counts
are353 CPU cache counts*8192 plus254 endpoint_shadow_tests/blocked; expected
primary_hits=8192 and backface_absorbed=0. Validate the full seed's primary
records/cache counts against353 again; do not infer expected counters from
the same GPU run alone. Original retained hits for the fixed pixels must
match the independent CPU probe and every GPU native.

Reconstruct sums/moments/counters from corrected-paths.bin in original sample
order, verify gpu.stats and selected o.f64 records bit for bit, flags and
batch intervals/lengths, and require unflagged raw paths equal corrected paths.
All flagged samples are retained/recomputed, not discarded. Report raw GPU
discrepancies and fallback fractions descriptively. High fallback does not
relax scientific cuts or prove viability; CPU254's paired acquisition also
does extra old/new work, so its cost is NOT a fair speedup denominator.
Every batch submit/wait wall observation is diagnostic, not GPU timestamp.

Before accepting any step, recheck all inputs and generated binary/SPIR-V
identities; record actual child PID/start/resources, terminal returncode,
stdout/stderr, payload hashes and zero-retry history. A stopped step remains
recorded and prevents subsequent steps. No cherry-picking pixels/seeds or
raising resource limits within this acquisition.

## Interpretation and remaining work

All steps PASS means only bounded selected-C1 numerical conformance for this
prototype. This does not transfer095/098/099/101 old-sampler evidence, replace
106/109 CPU artifacts, pass independent density/bias assessment, validate24
states/exact prefixes, establish whole-frame feasibility or qualify the eight
missing references. Any such backend transition requires explicit evidence
and a prospective intake amendment. Keep16/24 references,14/17 full artifacts
including one diagnostic-only item, and Sponza direct max-relative-error1.0
pixels UNRESOLVED/未解決 and scored until actual new evidence changes them.
N010 NOT_READY; no N011. Build/unit/regression tests NOT RUN; acquisition
here is scientific validation, not release regression validation. No CUDA,
Renderer/default build graph/Actions/N001–N009 changes.
