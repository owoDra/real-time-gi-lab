# 042a — Replay boundary and sample-normal addendum, before implementation

Prospective clarification of 042 (`d576bc75`) BEFORE any 042 code, test,
compilation, replay, GPU process or metric. 042 text and identity are kept;
this addendum controls the points below. No gate, parameter, target, seed,
variant or decision is changed.

1. Sample normal in the target function. The SDK passes only position and
   radiance to `RAB_GetGISampleTargetPdfForSurface`. The registered hemisphere
   test obtains the sample normal by EXACT bitwise position lookup in a
   per-thread table filled by the receiver-frame accessor on every SDK load of
   the current pass (selected samples are bit copies of loaded positions).
   Zero-luminance radiance returns 0 before lookup. A failed lookup or table
   overflow returns 0 and sets an error flag; any flag in any frame is an
   implementation failure.
2. Visibility near-boundary class for the CPU replay. A CPU float64
   Moller-Trumbore verdict over all triangles (owner primitive ignored) is
   STABLE when it is identical under tmax x(1-1e-4) with barycentric margin
   +1e-6 inside, and tmax x(1+1e-4) with margin 1e-6 outside (t>0 both).
   Only unstable queries may disagree with the GPU; stable disagreements are
   unexplained failures.
3. Decision margins for the CPU replay apply to: reservoir selection
   `random*weightSum<=risWeight`, Jacobian bounds 0.1/10, the normal (0.6) and
   relative depth (0.1) neighbor tests, and target positivity. Relative margin
   <=1e-5 makes a decision near-boundary. Integer RNG, z-curve, offsets,
   truncations, addresses and the registered position transforms are replayed
   exactly in float32/uint32 with no tolerance.
4. After an explained divergence the replay follows the GPU-selected source,
   identified by its exact transformed position, so later checks stay
   comparable. Explained divergences count toward 042's 0.1% limit per
   frame/variant; continuous outputs (W, M, age, radiance code within the 041
   decoded 2% gate, normal code within one snorm step) are otherwise compared
   at rtol 1e-4/atol 1e-6 after selection agreement.
