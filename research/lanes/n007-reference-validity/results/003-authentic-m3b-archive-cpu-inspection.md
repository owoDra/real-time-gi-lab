# N007 P0 result 003 — authentic archived M3b PFM diagnostic

**Classification:** decision-valid *reference ineligibility observation*, **not** GI algorithm quality/accuracy acceptance. Reported by the user's **actual local CPU run** on 2026-10-12; original PFM bytes and the generated JSON have **not** been transferred into the assistant sandbox, so image contents are not independently reproduced here.

## Artifact identification and command

- Current repository: `owoDra/real-time-gi-lab`, branch `research-n007-reference-validity`.
- Original private artifact root: `../gi-lab-old-private`, **not** committed to the public repo.
- Exact discovered capture relative to private artifact root: `out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed/20261011T115843Z/Q8_control_reference/`.
- Invocation: `python3 scripts/research/n007_reference_validity/inspect_archive.py --archive ../gi-lab-old-private`.
- Generated output in **new** repo: `out/research/n007-reference-validity/p0-m3b-archive-diagnostic.json`. Output file not uploaded/committed; only the console summary was provided.
- Inspector reads both reference PFMs and the Q8 GPU candidate PFM through original `n006-candidate-evidence.json` rather than guessed filenames; original archive remains unchanged.

## Observed CPU diagnostic console summary (authentic historical PFMs)

```json
{
  "reference_status": [
    "black_reference",
    "insufficient_active_pixel_support",
    "low_absolute_reference_signal",
    "identical_independent_replicates",
    "fewer_than_four_independent_replicates"
  ],
  "pairwise_rms": 0.0,
  "reference_black": [true, true]
}
```

The **specific reason for byte-equal M3b references is now resolved at image level**: both reference images are exactly black in this preserved capture, so their RGB difference is zero regardless of independent RNG streams. This **does not** establish the underlying physical cause of the black reference. A zero reference pair RMS cannot provide a useful stochastic uncertainty estimate. `fewer_than_four_independent_replicates` additionally reflects the **prospective N007** screening requirement and must not be retroactively imposed on historical N006 acceptance rules.

## Open causal split (do not prematurely classify)

- Real physical darkness or occlusion: possible.
- CPU tracer scene/camera/light-state or visibility mismatch: possible.
- Centered-primary undersampling and secondary sample starvation: possible.
- GPU probe radiance light leak: plausible code-level mechanism because the N001 GPU probe-hit direct-light shader omits the CPU's shadow-to-point-light occlusion test, but not proven for these pixels.
- GPU Q8 output signal (count/max/whole-frame RMS against black reference), original PFM SHA256 and archived summary-verification bit: inspect the complete generated JSON next. The supplied concise console summary lacks those fields, so no quantitative claim about GPU nonzero pixels is made here.
- Actual cause can only be isolated with aligned input state + component-level primary, direct and indirect visibility checks. **No GPU rerun and no N006 candidate experiment** is authorized by this diagnostic.

## Decision and provenance

Preserve N006 P1m3b `invalid-retained` and final N006 P1 NO GO. This N007 evidence establishes real-reference statistical **ineligibility**, not a physical-reference falsification nor proof that GPU is wrong. Further analysis belongs only to N007. N006 M3b source history SHA and rewrite mapping are recorded in `research/provenance/commit-map.tsv`; do not overwrite the past evidence.
