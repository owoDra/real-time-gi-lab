# N006 P1m1 — canonical-probe marginal value controls (CONDITIONAL DESIGN, NO GPU RUN)

Issue #42; 2026-10-11. Follow-up after [P1m0](./020-p1m0-probe-consumer-coverage.md). This document **does not authorize P2 scheduler**, and is **not** evidence of a successful predictor. Its eligibility depends on M0 5/5 accepted image/hit/consumer-accounting PASS and demonstration that consumer counts can be computed **after primary visibility but before secondary tracing** with realistic GPU costs.

## Why canonical-key rather than owner-local selection

P1a tested one owner×cascade, mostly no final pixel change; P1b observed integer spatial storage changes and dilution among up to 151 sharing owners; P1c found 81.85% duplicate ray inputs. Later P1j canonical tracing established a unique `(probe xyz,cascade)` key per output. Composite looks up this **spatial key**, not `tile_id`. M1 adds directions to **canonical output key**, retaining 8 immutable base directions and exact base output identity/owner weight.

## Prior conditions and fail-closed design

1. M0 must show five fully accepted frames with 320×180 full-original byte parity after auxiliary consumer pass, 4 cascades, all canonical keys present, source/software composite key expression matched, no invalid hash/overflow, N004 primary CPU sampled oracle pass. If absent/invalid, **STOP M1 implementation** and fix M0 rather than reuse untrustworthy counts.
2. Stable P1j-A lean-hash+copyback canonical reference is used for **software and HWRT separately**. Do not generalize their images or timings; first M1 causal pilot should use only one backend before cross-backend claims.
3. Candidate *cheap pretrace signal*: `valid_primary_pixel_consumer_count` for each **canonical key**, measured using the pretrace M0 counting pass. Zero-key and positive-key classes must **both** be retained. Each of four cascades is reported separately. This is a visibility/coverage eligibility feature, **not** a radiance prediction or asserted gain. Compute overhead (extra GPU pass + hash table writes/reads + barriers + scratch) must be included when a candidate selector is tested; a diagnostic postframe pass isn't free.
4. If M0 indicates strong storage/key mismatch or consumer pass cannot be run before secondary dispatch at bounded cost, **M1 STOP/REFINE**; no alternate freely tuned feature.

## Conditional causal intervention: what must be made correct

- New N006-only per-canonical-key +4-ray injection stage **after** canonical key compaction and **before** secondary tracing. Preserve base 8 directions and primary frame; exactly one additional deterministic 4-ray block per chosen key. No old owner-local serial-scan `n006_extra_producer` used as a runtime scheduler. Capacity/overflow/invalid token fail closed.
- A key with N sharing owners must retain the accepted post-radiance integer quantization and storage owner-weight reconstruction; variable per-output ray count must not use the hard-coded 8 for new extra rays. Existing GPU `canonical_weight_storage` assumes 8 for base owner output reconstruction; this is a **known implementation contract to revise only in N006 candidate stages**, not by editing historical accepted shader.
- Extra direction rule should be the existing deterministic `extra_direction(probe key,ordinal)` from N006 P1a; no post-hoc direction search. Verify distinct direction seeds and GPU exact work IDs. A zero-consumer key can still affect other pixels indirectly only if storage/probe routing differs from the documented lookup; preserve contradictory evidence.
- Paired original/candidate images against an **independent converged HDR reference**, and a candidate-no-extra control proving bit exact. Per-key signed global RGB RMS gain = `RMS(current,reference)-RMS(intervention,reference)`; store negative/zero outcomes as-is. Also record affected-pixel fraction, p99 relative and absolute and local impact, with raw normalization. Never infer signed global benefit just from `consumer_count>0`.

## Prospective M0→M1 calibration-key selection (frozen BEFORE M0 GPU evidence)

This selection is **calibration sampling ONLY**, not a predictive threshold, quality-outcome optimization, statistical significance test, or P1 held-out split. Selection must use *only* the verified M0 `p1m0_consumer_coverage.key_rows` counters: no reference HDR, no RGB error or interventions.

For each one of the frozen five scenario frames and *each* cascade 0–3, select **exactly one canonical probe key per predeclared coverage stratum**, in canonical token numerical order:
- `zero`: all rows with `consumer_pixels == 0`; select the smallest integer `token`;
- `low_positive`: among rows with `consumer_pixels > 0`, select one with **minimum positive count**; ties broken by smallest `token`;
- `high_positive`: among rows with `consumer_pixels > 0`, select one with **maximum positive count**; ties broken by smallest `token`.

If a stratum has no key, or minimum and maximum positive counts are equal (the low/high groups are not separable), preserve `stratum_missing` / `insufficient_positive_variation` in the manifest rather than substituting a different key or silently deleting that scene. No M1 intervention study is allowed for such incomplete 5×4×3 calibration strata without a *new, prospective* design. Rows must be revalidated as sorted, unique, nonnegative, one owner minimum, correct SHA/cascade conservation before selection. Freeze the result in M0 output: **60 expected selections = 5 scenarios ×4 cascades ×3 strata, if all available**, with `token`, `consumer_pixels`, `producer_owner_outputs`, scenario/cascade/stratum, full per-case row hash. This is NOT an authorization to trace 60 extra-ray interventions until M0 correctness and pre-secondary GPU-cost gate are passed.

Calibration set uses existing five-scene source and cannot be relabeled evaluation/holdout. Formal P1 must freeze and generate **independent trajectories** for evaluation and sealed holdout, without retrofitting source-set outcomes.

## Sampling and evidence separation (to freeze numerically before GPU)

- **Calibration** only: choose keys deterministically from source M0 **coverage strata** (zero, low nonzero, upper-tail nonzero), across **all four cascades** and at least stable-deformation + illumination/camera-control regimes, without consulting reference error or observed outcomes. Freeze sorted key tokens and inclusion/failure handling before candidate rays run. Sealed evaluation/holdout must use *different geometric/light/camera trajectories*, not only seeds on the same fixed frame.
- One-key marginal labels are NOT additive. Before any equal-K P2 comparison, validate a selected **combined-key intervention** for nonadditivity, carry exact total actual traced rays and report all confounding overhead.
- GO to predictive ranking design only if: (a) canonical +4-ray injection is correct with accepted baseline parity, (b) signed image gain has signal larger than calibrated repeat-reference variance for some coverage strata, and (c) the coverage signal's performance can be compared on *unseen* source trajectories without selected-point leakage. Numeric gain thresholds need to be frozen from calibration noise **before evaluation**. If no visible signed gains or all signal is swallowed by quantization, **STOP predictive scheduler** as unproven (do not relabel ray dedup a P2 success).

**M1 status: CONDITIONAL RESEARCH DESIGN ONLY. M0 and C0 target GPU evidence not supplied.** No N004/N005, original E003/N003, CI, Actions, or PR changes.
