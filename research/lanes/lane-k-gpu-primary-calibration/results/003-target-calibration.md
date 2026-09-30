# K003 — accepted target calibration

## Formal status

**Accepted target calibration.**

- Plan: `lane-k-k002-v1`
- Measurement commit: `0cab088ed2316ba38497b1aa92a8a507638471f5`
- Target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`
- Driver: `radv` / Mesa 26.1.2
- Timestamp period: 10.019 ns
- Primary axis: GPU timestamp
- CPU wall: diagnostic / health / provenance only
- Sample exclusion: none
- Completed-campaign rerun budget: 0

The uploaded evidence set did not include the outer
`run_experiment.py` `metadata.json`, so the canonical artifact timestamp path
cannot be reconstructed from the committed result alone. The K003 summary and
progress files identify the exact Git commit and the complete process set.

## Campaign completeness and structural health

The frozen K002 campaign completed exactly:

- 8 fresh-process blocks;
- 4 comparisons per block: control, +20%, +10%, +5%;
- 32 processes total;
- 4 warmup pairs and 12 measured pairs per process;
- 1,024 retained raw rows total:
  - 256 warmup rows;
  - 768 measured rows;
- 8 fresh processes per comparison;
- all process/sample ordering followed the frozen counterbalanced schedule;
- every timing sample was finite and positive;
- complete CPU wall was never smaller than its GPU timestamp;
- target device/driver/API/timestamp provenance remained consistent across all
  32 processes.

No sample was excluded and no instability rerun was permitted or used.

## GPU-primary result

Frozen GPU-primary baseline-control criteria all pass:

| Gate | Observed | Frozen limit |
| --- | ---: | ---: |
| max abs process median ratio | 1.004776 | <= 1.02 |
| process median span ratio | 1.008391 | <= 1.03 |
| max within-process order-bias ratio | 1.010745 | <= 1.02 |

Known-delta detection is contiguous:

| Delta | Campaign median ratio | Min process median ratio | Effect span | Min positive-pair fraction | Max order-bias | Detected |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| +20% | 1.171819 | 1.163442 | 1.016447 | 0.833333 | 1.013221 | yes |
| +10% | 1.085462 | 1.075652 | 1.012428 | 0.916667 | 1.011643 | yes |
| +5% | 1.048130 | 1.041299 | 1.008538 | 0.750000 | 1.014836 | yes |

The frozen contiguous resolution is therefore **5%**.

## CPU-wall diagnostic evidence

The CPU-wall baseline diagnostic control passes its annotation criteria. +20%
and +10% are detected under the annotation-only criteria. +5% receives the
predefined repeatability/detection warning because its minimum positive-pair
fraction is 0.666667, below the annotation criterion of 0.75.

This does **not** invalidate the GPU-primary decision. K002 froze complete CPU
wall as `diagnostic-health-provenance-only`, and the structural invalidation
rules all pass.

## Decision

K003 demonstrates safe 5% known-delta resolution for the exact frozen
GPU-primary methodology on the measured target. This is new Lane-K evidence and
does not reinterpret Lane-I I003.

K004 may classify the exact result under the predeclared mapping.
