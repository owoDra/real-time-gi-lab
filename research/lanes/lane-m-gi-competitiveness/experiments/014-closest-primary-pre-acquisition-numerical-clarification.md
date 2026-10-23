# Closest-primary013 pre-acquisition numerical clarification

2026-10-24, after CPU build088and before implementing the full-image auditor or
any variant GPU acquisition: finite unit normal means
`abs(length(normal)-1) <= 1e-4`, inclusive, for each actual hit. Miss records must
retain the original invalid-ID/clear convention. This fixes the previously
unspecified float normalization tolerance before any candidate observations;
none of the image, depth or named-pixel gates changes. Position differences are
diagnostics reconstructed from captured camera/hit distance and the canonical
reference ray, not exported GPU positions or proof of exact GPU arithmetic.

This is a prospective clarification of [013](013-closest-primary-development-validation.md), not a new GPU sequence. The original013bytes bound by build086remain exact; the future execution plan must bind both records. No identical build or native contract is rerun merely because of this added prose. The brief intermediate Git commit43b58029included the clarification inside013; this separate record restores its exact build-bound original bytes before any new metric test or GPU acquisition. No capture, CPU build output, test receipt or scientific outcome was changed.
