# N006 P1m3a — Q8 fractional canonical storage opt-in implemented, GPU pending

2026-10-11. Explicitly new storage representation under prospectively frozen [protocol 028](../experiments/028-p1m3a-fractional-storage-mechanism-calibration.md), **not** a retry or GO reclassification of the 32/32 exact-image-null original integer-storage [result 039](./039-p1m2b-bounded-screen-32of32-exact-hdr-null-stop.md).

## GPU implementation shipped on research branch

Two **N006-only** shader clones:
- `shaders/research/n006_interval_aware_allocation/n006_p1m3_fractional_storage_update.comp.glsl`, original I001 storage update reservation unchanged, accumulation now `S=256u`, `sample_value_q8=(merged.x*S + merged.y/2u)/merged.y`, slot `data.y+=sample_value_q8`, slot `data.z+=256`; int32 overflow/fail counters reject rather than clip.
- `shaders/research/n006_interval_aware_allocation/n006_p1m3_fractional_weight_storage.comp.glsl`, original canonical owner weight pass cloned; only accepts original single-output `slot.data.z=256`, owner scales both numerator and denominator; numerator/denominator overflow guarded before write.

CMake builds separate `n006_p1m3_fractional_storage_update.spv` and `n006_p1m3_fractional_weight_storage.spv`, only in N006 dependency. N006 runtime allocates & dispatches both alternative stages **only when opted in**, otherwise continues using the original `impl.storage_update_stage` and `state_->canonical_weight_stage`. All original shaders untouched, including existing N006 8+4 producer and active N001 physical-Lambert radiance. N006 CLI `--p1m3-fractional-storage` **requires** `--p1m2b-independent-state`, scenario camera/light, original M1a extra directions, and frozen listed calibration tokens (or zero token for control); full historical flags/warmups/mode guards remain enforced. Output JSON includes explicit `p1m3_fractional_storage`.

## Prospective SMALL calibration runner

`scripts/research/n006_interval_aware_allocation/run_p1m3a_fractional_storage.py`:
- 2 independently warmed Q8 control processes in **camera-motion** and **light-motion** each (4 controls). They must match one another and accepted original M0 coverage and CPU/GPU hit oracle, but **Q8 control PFM is NOT required to equal historic INTEGER baseline SHA**: Q8 is a representation change. Retain old/new SHA for attribution.
- From previously observed M2b diagnostics (NOT holdout), frozen 3 arithmetic nonzero/consumer-positive keys: camera c1-high `1084233745` (base0,extra2), camera c3-high `3223324678` (base10,extra0), light c3-high same token `3223324678` (base1,extra0); plus camera c2-high **negative** `2152730633` (base0,extra0).
- On each target verify original raw GPU contribution sums and unchanged M0 selected row, exact eight plus four ray contract, Q8 numerator arithmetic prediction, N004 oracle, then compare entire PFM against **same-scenario Q8 control**, not accepted historical unmodified output.
- A changed PFM requires exact independent-process reproduction. Negative control changed pixels is a failure. No output changes on all 3 positive-calibration cells means **STOP Q8 mechanism**; a reproduced difference means **mechanism GO ONLY**, not signed quality. Separate converged HDR reference, unique holdout and cost ROI required for P1/P2.
- New unittest `test_p1m3a_fractional_storage.py` asserts frozen Q8 arithmetic, source isolation and overflow guards, separate CLI/stages, max-four prospectively chosen cells, runner repeat/STOP policy.

One command requires user's real AMD GPU, clean research branch and available NixOS `mise` environment:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m3a_fractional_storage.sh
```

Script will fast-forward, `mise run build`, run full N006 Python unittest suite and only then run Q8 GPU calibration. Results: `out/research/n006-interval-aware-allocation/p1m3a-fractional-q8-calibration/<UTC>/n006-p1m3a-fractional-storage-summary.json`. **No new build, test or real-GPU result has been received** and no production P1/P2 design is authorized. Do not re-run old B1/C0/P1m2b campaigns. No PR/GitHub Actions.
