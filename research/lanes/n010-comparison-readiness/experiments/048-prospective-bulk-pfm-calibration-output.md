# Prospective row-bulk PFM output for full Renderer calibration

Date: 2026-10-15 JST. Parent checkpoint: `0c64576`.
Registered after post-hoc diagnosis 162 and before building this fixture or
acquiring its GPU output. Current 158 remains running and must be retained.

## Evidence and falsifiable question

All ten static decisions in 162 reproduce the original gates: C1 PT B8 PASS,
the other nine FAIL. C1 HWRT/software block-0 saved-output cadence is about
9.30/12.57 ms, versus 394/498 ms in an earlier acquisition. Reduced bulk
diagnostic output alone has not established the required timing precision.
These file mtimes are not direct GPU busy/idle or clock/power measurements.

Both current PFM writers call `ofstream.write` once per pixel. Three C1
320-by-180 component images require 172,800 such calls per frame. Test whether
reducing this remaining CPU serialization overhead permits the **unchanged**
full-boundary calibration to pass. This is a prospective acquisition repair,
not a claim that PFM writing caused previous failures. Keep all earlier data.

## Exact isolated change and build 167

Generate a separate fixture in `minimal-calibration-build-v3`, retaining
plan-044/045's minimal output and directory repair. Change only the two PFM
writer loops: construct one row of exactly the same repeated grayscale RGB
floats, then write that row in one call. Retain header bytes, bottom-to-top row
order, component selection, binary32 values, file paths and output checks.
No buffering across frames, dropped output, new warmup or extra GPU work.

The complete runtime source must equal build 159's runtime source. Reversing
only the row-writer overlays must reproduce build 159's capture/PT files
exactly. The inherited complete-source inverse proof must also reconstruct
the original active sources. Timed methods, shaders, queries, barriers,
resource allocation hooks, frame schedule and source/first-target semantics
remain unchanged. Record all input/generated identities and compile commands.
Keep active/default source, binaries and build graph unchanged.

Use the original five serial compile/link steps and 8 GiB / 21600 aggregate
CPU-second / 3600 elapsed-second guards per invocation. No build may overlap
current 158 or other GPU research work. CPU build may coexist with CPU
reference controls, whose CPU wall time remains diagnostic; the native
scientific bytes, sample/resource guards and all their gates are unchanged.
Build/source failure stops with all bytes retained; no automatic retry.

## Fresh GPU gates and scheduling

Only after complete 167 PASS and actual termination of CPU reference/control
work and all other GPU research may a new guarded wrapper execute:

1. Fresh sizing 168, all sixteen original boundaries and the original
   Amendment-5 three-dose schedule, +20% sizing and dose cap. Require every
   direct/indirect/total image to equal immutable 046, exact known-work scratch
   witnesses and allocation-ledger replay to zero within 8 GiB.
2. Only complete 168 PASS permits fresh 169: all sixteen boundaries, eight
   fresh-process blocks, four warmup/twelve measured pairs, original AB/BA
   order, one-second settle and the sized immutable doses.
3. Apply the exact original schedule/analysis functions and thresholds.
   Failure is retained; no subset acceptance, correction, retry or gate change.

Results 158/162 and old 029 remain separate. Do not retroactively calibrate
earlier pilot timings. No new GPU acquisition overlaps reference work; CPU
controls 163/164/165 may proceed after 158 terminates, before this fixture's
GPU gates. Eight-slot acquisition 166 can be scheduled after those independent
GPU gates terminate, keeping every full-corpus and final-readiness requirement.

All 24 eligible references, complete quality/memory pilots, explicit unresolved
direct discrepancies and final six-gate 047 remain mandatory. A build or sizing
PASS alone cannot admit Lane M. No N011, CUDA, Actions, clock/power change,
active Renderer promotion or N001–N009 result modification.
