# M001 / 025: NRD sky-material initialization intervention

Prospective baseline: `72da1d4a`, after completed024's first-control failure.
Keep024, its strict failed reset gate and all original SDK/evidence bytes.
This registration precedes new source, compiler/API runs and GPU acquisition.
It is a disclosed private NRD implementation variant, not unmodified upstream.

## Question and exact intervention

Does avoiding the uninitialized shared world-position/material read in fully
sky-classified tiles remove024's material-history reset mismatch, with every
other saved physical/input/radiance/history field unchanged on its H01/B2
control? Can the same variant then pass the original three runtime controls?
Source/data diagnosis alone does not answer the intervention question.

Pin NRD e06852bd545973cb224eb28820b891205cfc1624, ShaderMake3f01623a,
MathLibaa432ad9 and the verified official DXC1.9.2609 from023. In an exclusive
private copy only, change exactly one occurrence in
`Shaders/RELAX_AtrousSmem.cs.hlsl`:

```hlsl
float4 centerWorldPosMaterialID = s_WorldPos_MaterialID[sharedMemoryIndex.y][sharedMemoryIndex.x];
```

to:

```hlsl
float4 centerWorldPosMaterialID = isSky == 0.0 ? s_WorldPos_MaterialID[sharedMemoryIndex.y][sharedMemoryIndex.x] : float4(0.0, 0.0, 0.0, 0.0);
```

The existing tile classification, normal fallback, history writes, early-outs,
all in-range equations, NRD settings/guide conventions and producer are fixed.
Sky world position is not subsequently used after the existing tile early-out;
sky material history becomes canonical zero. Do not change the original
shared-preload macro or clear histories each frame. Save exact old/new source
identities and the single-line diff. No other SDK or shader change is allowed.

## CPU preparation and executable identity

Reuse the unchanged023 ShaderMake executable, all other SDK shader headers,
six other SDK objects, ShaderMakeBlob library and024 native/API objects,
producer/packing/composition SPIR-V. Recompile only the registered upstream
AtrousSmem family (six original signal/mode permutations, original compile
options) using a one-line subset of the original shader config. Compile the
original Relax.cpp once with the replacement header, replace only its archive
member in a new copied library, and relink the unchanged native and API objects.
Do not invoke the old all-shader/default CMake build or rewrite old outputs.
Prove all other archive members and selected SDK pipeline binaries unchanged.

Before GPU, run meaningful intervention/manifest/plan/stop tests and actual
CPU SDK inspection on the three original cameras under an unusable ICD. Each
inspection records the same65 API frames as023; compare every dispatch/resource/
constant byte to its original scene, independently audit with the existing023
CPU auditor, and validate the changed SPIR-V. Exactly the selected AtrousSmem
pipeline may change; preserve every other selected pipeline byte. Reuse prior
33 C++/39 Python/18 native024 contract results, without rerunning them or
implying they test the SDK patch. Commit all new executable scripts, tests and
audit rules before CPU execution; commit CPU readiness before GPU plans.

All source/compiler/build/API receipts live in new repository `out/` paths.
CPU compiler/API subprocesses: one worker, <=4GiB address space, <=240 CPU
seconds and <=360 wall seconds each. Preserve any failure and stop; no blind
recompilation or automatic rerun. Parsing/relink/ABI-only identified repairs
must have a committed new version and exclusive outputs. Any further SDK,
algorithm, setting or criterion change needs another preregistration.

## GPU sequence and gates

025 has its own exclusive three-control cohort, in the original fixed order:
H01/B2/16spp, H02/B8/64spp, H03/B2/64spp. It does not resume failed024.
Announce and execute one explicit command at a time, never a queued cohort.
Each process uses the identical024 adapter/physical producer/shaders, one
SDK/device/AS/pool and exactly three frames: CLEAR/frame0/seed305419896,
CONTINUE/frame1/seed2654435769, CLEAR/frame0/seed305419896. Identical450 bounded
producer chunks per frame, actual SDK21/10/21 dispatches, GPU guide packing/
composition and post-composition readbacks. No CPU image/hit/guide upload or
inter-stage readback. Same guard:120 CPU/180 wall seconds,4GiB process space,
8GiB aggregate owned pre-allocation cap,250ms per wait,2ms unit pauses,
16GiB free disk and no competing workload. No power/clock/desktop changes.

For H01 intervention, compare **all three** saved frames to the corresponding
immutable024 frames. Require every binary guide/raw PT/secondary-ray/source/
SDK-constant/final-RGB/other-pool field bit-exact. The sole allowed difference
is material-history bytes inside the original fully sky-classified tiles;
all new bytes there must be zero, all other material bytes bit-exact. Retain
full difference masks/counts, including old unchanged zeros. Prove the shader
family/source and selected-pipeline change is precisely the registered one.
No tolerance, pixel exclusion or quality-based exception to this intervention
gate. Failure stops025 before H02/H03, even if strict reset separately passes.

For every control retain024's strict complete-field reset gate: every binary
output/pool/guide/constant, including sky material history, must be byte-exact
between cold and reset. Raw PT must also equal original022 same-budget bytes.
All pool/RGB finite and relevant histories/radiance nonzero; continuing history
must update and reset, actual resources/constants must agree with the scene's
CPU SDK capture. Reuse byte-identical saved H01 physical-ray/guide audits from
024 only after verifying equality of every required input. New H02/H03 cold
and continuing rays require the full original independent double-precision
physical-intersection/sample-order/primary/guide/float bounds from024, without
exclusions; reset reuses cold after exact equality. Preserve full error maps.
All allocation lifetimes/true peak/zero teardown and1,454 timestamped units
must reconcile with the unchanged024 auditor. Timing stays uncalibrated and
cannot qualify performance; ownership is not memory-superiority evidence.

Independently terminal-audit each control before preparing the next. Stop the
entire cohort after any implementation/runtime/intervention/oracle/resource/
timeout/ownership failure; save partial and failed evidence, no retry or
advance. Classify intervention failure distinctly from HDR quality loss.
End025 after three control passes or the first failure. A pass qualifies only
this disclosed sky-initialized variant at these runtime boundaries, with no
NRD HDR/temporal quality, speed, novel architecture or Lane M completion claim.

Publish compact outcomes/verification, update the current status/index, commit
and push the research branch, update Issue7OPEN. Default Renderer and
N001–N010 remain unchanged; no CI/Actions/main promotion or raw data in Git.
Next separately freeze fair cold AND64-frame warm quality cohorts/independent
seeds/all tracing/guide/history costs before calibrated matched-quality full
system timing/memory. Novel transport, new heldouts/dynamic/Sponza/multiple
GPU classes/deployability gates and the full Lane M objective remain open.
