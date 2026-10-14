# N010 controlled dynamic PT budget confirmation

Prospective acquisition declaration, after results 019/024/025 and before
the following new dynamic images. This is pilot budget selection on observed
N010 states, not a held-out Lane M campaign or a quality-threshold amendment.

The complete fixed ladders for C8 camera and C9 light motion select 1024 spp
for both finite transports. Retain result 019's original PT 256-spp T_B2
losses. Add a separate T_B2 1024-spp dynamic confirmation for every controlled
transition C8–C12, using the unchanged state lock 026, fixed seed 305419896,
one source frame, the first changed frame and three recovery frames. No
frame is discarded, no transition is omitted, and no rerun is selected for
quality. Scoring, transport, numerical profile and memory gates are unchanged.
T_B8 1024-spp confirmation already exists in 019. The additional acquisition
does not overwrite that original cohort or its allocation ledgers.

GPU timestamps remain DIAGNOSTIC_UNCALIBRATED while CPU references are active.
The full retained images, state and binary identities, sample counts,
allocation lifetimes and per-frame quality scores are required. If any frame
fails, report its loss; do not raise the budget after this acquisition.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_comparison_readiness/acquire_dynamic_pilot.py \
  --cells C8 C9 C10 C11 C12 \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/references-v1 \
  --roles pixel-pt-B2 --pt-spp-b2 1024 \
  --work out/research/n010-comparison-readiness/controlled-dynamic-pt1024-v1 \
  --output research/lanes/n010-comparison-readiness/results/037-controlled-dynamic-pt1024.json
```
