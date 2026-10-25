# 044 — Calibrated matched-quality and equal-cost GPU timing on M001

Registered after 043 publication `e7fd8501`, BEFORE any 044 code, build,
calibration or timing acquisition. All earlier timings are uncalibrated
diagnostics and are not reused as evidence.

## Questions and fairness boundary

M001 quality evidence now fixes which configurations meet the unchanged gates
on all six static targets (total NRMSE<=5%, indirect<=10%, |bias|<=5%):
raw PT at its first passing rung (023: 256spp B2, 1024spp B8) and PT plus the
fixed quadratic reconstruction at the 022 rung (16spp H01/B2, 64spp others).
Every tested NRD (026/028, 1-64spp), corrected DDGI (012), fixed RC (028) and
ReSTIR GI (042/043) configuration fails. The 022 rule "no speed ranking against
raw PT alone" was written while no standard denoised family was qualified;
NRD has since been qualified and fails at every budget, so it cannot be timed at
matched quality. This study therefore asks:

- T1 (matched quality, accepted-capable): is PT+reconstruction at the 022 rung
  faster per frame than raw PT at the 023 first-pass rung, by at least the
  practical ratio 1.20 and the calibrated minimum effect?
- T2/T3 (equal-cost descriptive, both sides fail the gates): per-frame GPU
  cost of ReSTIR V1 + reconstruction (RSR, the 043 R1 configuration) versus
  PT1 + reconstruction (T2) and PT4 + reconstruction (T3). Combined with
  published per-frame quality (043 RSR; 018 4spp/1spp reconstruction rows),
  RSR dominates a comparator only if its cost is not significantly higher AND
  its published indirect NRMSE is lower on that target.
- Owned memory per role (true buffer bytes plus shared acceleration structures).

No architecture-novelty claim: PT, ReSTIR GI and local regression are prior art.

## Harness (one native host, one Vulkan context per process)

Exact reused SPIR-V: 022 `integrated_producer`, `surface_quadratic_device`
(geometry/fit/filter), `integrated_composite`; 041 `physical_producer`; 042
`reuse_s0..s4` (variant V1 only). New GLSL: an accumulation pass (raw PT chunk
average), a copy pass (V1 indirect -> reconstruction source) and an
architecture-neutral calibration kernel (fixed-iteration FMA loop over 57,600
threads). Roles, each one complete frame on the admitted 022 state:

- PT_REF: raw PT, 64spp chunks (4 at B2, 16 at B8) + accumulation per chunk.
- PTR: 022 sequence at its rung (producer, geometry, fit x3, filter x3, composite).
- PT1R / PT4R: the same at 1 / 4 spp.
- RSR: 041 producer 1spp, 042 initial/temporal/spatial/shade/copy (V1), copy,
  geometry, fit x3, filter x3, composite. History persists across RSR samples.

Each role sample = its fixed submit sequence (one submit per chunk/frame,
<=250 ms fence guard); cost = sum over its submits of GPU end-start
timestamps. CPU wall is diagnostic only. Per-pass timestamps are diagnostics.

## Calibration (before any target timing), Lane-K structure

8 fresh processes, 1 s settle, per process 4 warmup + 12 measured AB/BA pairs
per comparison, pair order alternating, comparison order rotated. Neutral
comparisons at two boundary sizes (short single submit ~5 ms; long 16-submit
~300 ms): control (identical work), +5%, +10%, +20% iterations. Statistic: the
median over processes of each process's median paired log(B/A). Control passes
iff |process medians| <= log 1.02, span <= log 1.03 and max order bias <= log
1.02 at both sizes. A delta is resolved iff all 8 process effects exceed the
control envelope (max |control process median|), span <= log 1.05, order bias
<= log 1.03 and positive-pair fraction >= 0.75. MDE = smallest delta resolved at
BOTH sizes. Control failure or no resolved delta => all target timings are
TIMING_INCONCLUSIVE (still recorded). Calibration is not rerun.

## Target timing and decisions

Six targets in order H01/B2 ... H03/B8, 8 fresh processes each, the same pair
structure with comparisons T1 (A=PT_REF, B=PTR), T2 (A=PT1R, B=RSR), T3 (A=PT4R,
B=RSR). T1 is ACCEPTED_FASTER iff all 8 process effects are negative, effect
<= -max(log 1.20, log(1+MDE)), span <= log 1.05, order bias <= log 1.03 and
positive-pair fraction >= 0.75; ACCEPTED_SLOWER symmetric; else INCONCLUSIVE.
T2/T3 report cost ratios with the same criteria (SIGNIFICANT if all criteria
hold with threshold log(1+MDE)) and the prespecified dominance rule above.
All samples retained, no exclusion, no rerun, no threshold change. Any
native/provenance failure stops 044 (later targets NOT_RUN).

Owned memory: allocation ledger true peak and per-role static accounting.
One AMD Radeon 8060S/RADV only; static targets; no power/clock change; no
default Renderer/CI change. Results do not by themselves complete Lane M:
dynamic/Sponza/new-heldout/multi-device gates remain.
