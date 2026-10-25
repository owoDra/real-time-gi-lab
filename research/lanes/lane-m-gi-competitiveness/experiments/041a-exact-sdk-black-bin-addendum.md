# 041a — Exact black-bin boundary, before implementation or execution

This prospective addendum resolves an analytical imprecision in041/7eb7af4f
BEFORE any041 implementation, metrics, test, build or experiment. Preserve the
original041 text and Git identity; this addendum controls the exact bound.

The official encoder truncates clamped logY to integer Le and returns black
when Le==0. Therefore its exact real-arithmetic positive-black boundary is
Y0=2^(-20+1/409.6), not2^-20. The earlier041 sentence claiming every decoded-black
original value is<2^-20/64 is too strong by about0.17%. Use Y0/64 instead.
Include adjacent float32/bin-boundary values to cover finite arithmetic.

The fixed choice is unchanged:
C=2^ceil(log2(Y0/(.02*1e-6)))=64; Y0/64<1.50e-8<2e-8. Thus the original2% floor
still has margin. This corrects the derivation, not any measured threshold,
sample, condition, codec algorithm or proposed unit factor. All041 process/
diagnostic/grid/CPU/GPU/stop/provenance rules remain in force. Record both041
and041a identities in execution/publication. No previous failure is rescued.
