# N010 depth-split numerical outcome and full-frame pilot

2026-10-18 JST. Plan112/source committed0ce0e21c before build360;
plan113/driver committedf0d3263b before361--366; plan114/driver committed
a58c2e3a before368--370. Every native was explicitly invoked after the prior
worker terminated. No retries, automatic queue or concurrent scientific work.

## Completed evidence

[360](360-whole-path-full-frame-build.json) is isolated build PASS: original
352 CPU snapshot/context byte-identical, shader edit inverse exact,
220 NoContraction results. Shader/host compilers both exit0,
0.083614/4.157025elapsed seconds, CPU31/nice15/4GiB. Build evidence itself
continues to say runtime_validated=false; later results supply runtime proof.

[361](361-depth-split-hybrid-probe.json) is an independent retained-CPU
1spp probe PASS. It reuses353's original CPU bytes, never rerunning or
substituting the CPU baseline. Every depth part/raw/corrected record and
accumulated statistic reconstructs exactly. Indirect NRMSE3.505256e-16;
3/8 paths routed to CPU, all with intersection ambiguity bit. Native0,
1.143500elapsed/1.089025CPU seconds; maximum depth wait8.226ms.

All four original8192spp/eight-pixel seed parts and
[366](366-depth-split-hybrid-numerical.json) are **all32 selected-C1
numerical PASS** under unchanged1e-10 mean/moment and1e-8 NRMSE cuts:

| Part / seed | Native elapsed s | Native CPU s | Indirect NRMSE | CPU fallback paths |
| --- | ---: | ---: | ---: | ---: |
| [362](362-depth-split-hybrid-seed0.json) /305419896 |58.857702|3.519707|2.084697e-16|23135 |
| [363](363-depth-split-hybrid-seed1.json) /2596069104 |60.377829|4.069004|3.290970e-16|23032 |
| [364](364-depth-split-hybrid-seed2.json) /81985529216486895 |59.867131|3.970002|3.167184e-16|22942 |
| [365](365-depth-split-hybrid-seed3.json) /18364758544493064720 |61.139407|4.259705|3.261866e-16|23038 |

Direct/emission means AND second moments, primary/cache/hit bits and scored
integer counts match the independent original CPU. Proposal query/attempt/
null/own counts also equal original254 audits in every8192 part. All262144
raw/corrected paths, route masks and1,835,008 depth parts remain. Reassembly
verifies raw path bytes, unflagged raw/corrected identity and corrected
stats/sidecar bits. All14336 depth submissions and2048 assembled tiles are
complete. Max depth submit/wait26.102352ms; owned true peak89,956,016bytes,
all ledgers zero. These walls/allocations are standalone-backend observations,
not calibrated GPU performance or Renderer/comparator memory admission.

## Post-hoc routing diagnosis, no guard change

Across the four full-count parts,92147/262144 paths use full CPU fallback,
unchanged35.1513%. Overlapping reason counts are:

| Original routing reason | Paths carrying bit |
| --- | ---: |
| Intersection ambiguity |88674 |
| Reconstructed-target/plane/backward-error guard |5256 |
| Own-density discrepancy |4 |
| Tiny cosine/pdf |553 |
| Potential CPU coincident surface |4 |
| Other invalid/nonfinite/exponent route |4 |

Intersection ambiguity occurs in96.2310% of routed paths. This identifies
the main recorded routing category, not proof that those flags are all
necessary or all spurious, and not a cause of earlier timing variability.
The shader currently sets a global path flag on a near tie against ANY
intermediate closest hit, even if a later hit is nearer. That source fact
motivates a possible execution optimization, but these data do not quantify
such provisional ties or authorize dropping guards. Raw closeness is not
independent evidence that bypassing fallback is correct. No guard changed.

## Full-frame extension: independent CPU/GPU conformance PASS

[368](368-full-frame-one-sample-cpu.json) is an independently executed
original254 CPU exporter, original C1/depth8/320x180/seed305419896/1spp,
ALL57,600 pixels. [369](369-full-frame-one-sample-gpu.json) computes exactly
that same physical sample in full mode, batch1/tile256, with original guards.
[370](370-full-frame-one-sample-hybrid-pilot.json) is the verified summary.

Full-frame max absolute mean/second-moment error is1.7277845820728999e-15;
unmasked indirect RGB NRMSE3.3108698463438282e-15. Every emission/direct
mean/moment and primary hit byte matches; all four global scored counters
and proposal query/attempt/null/own counts match independently. All means,
moments/PFM conversions are finite; all57600 samples,225 tiles and1575 depth
submissions complete, no uncomputed pixel or mask. Maximum depth wait
25.016954ms. CPU fallback20011/57600=34.7413%, of which19411 carry
intersection ambiguity. Owned peak89,973,904bytes, ledger teardown zero.

Native CPU-only4.673466elapsed/4.651305CPU seconds; hybrid28.837857elapsed/
3.402438CPU seconds. At this frozen1spp/batch1/tile256 layout the hybrid takes
longer elapsed time. This is a single-run operational comparison, not a GI
speedup/loss claim or accepted GPU timestamp evidence. Startup, small batches
and fixed per-depth pauses are included. It does not predict throughput at
the required8192--262144 counts or a different batch/tile layout. Do not
launch a long reference campaign on an assumed GPU acceleration. Measure
bounded cost at the actual intended layout before choosing an execution path.

## Current decision and next required work

The depth split and aggregate-storage interface now have selected full-count
and full-frame1spp numerical evidence. Original106/108/109 controls/prefix
obligations have NOT been silently replaced. Original full physical inventory
remains14/17 including one diagnostic-only artifact;259 is still only one of
four A6a seeds. References remain16/24. Full original physical/IID/bias,
all24 states/exact prefixes, full-count execution feasibility, missing eight
references, complete quality/dynamic/memory pilots and frozen comparison
budgets/intake remain required. Direct relative-error1.0 pixels remain
**UNRESOLVED / 未解決**, included in scoring. N010 **NOT_READY**; no N011.

Timing methodology follows249/103/255/256: GPU Renderer ratios with uncertainty
and conditional order/control allowance remain the performance axis. CPU
wall/clock/busy/other-app telemetry is diagnostic; no generic2% stability or
idle requirement is added. Static-C7 bounded calibration has already PASSed;
actual selected comparison workloads/quality budgets and final intake still
need matching qualification. Valid quality or memory results remain reportable
when timing is inconclusive. No old FAIL is reclassified.

## Publication checks and scope

Verified778 unique result/input/payload SHA identities exactly, including all
new data and shared inherited inputs. All9 new compiler/native receipts are
exit0 and their recorded PID/start identities terminal. No scientific worker
or automatic queue remains. No power/clock/display/driver/other-app settings,
N001--N009 results, Renderer/default build graph or Actions changes.
Build/unit/regression tests **NOT RUN**; isolated compilation and registered
scientific image/stream/audit/count/owned-ledger checks above were executed.
Metadata/link checks are not runtime regression or full readiness proof.

Immutable summary SHA-256 identities:

- 366: `cf9d5c4dc301fc28fd43542b961322890b5425a1ff9d8460f77028628ea7661a`.
- 370: `b61a916823dfe1c46830b572bcaf051eab768e6bc0e648c3514cc70155cf1d0c`.
