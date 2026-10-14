# N010 isolated shader overlays

N010 composites are generated from the pinned N-series shaders using
scripts/research/n010_comparison_readiness/generate_capture.py. Each actual
lookup key and composite position is saved in a dedicated diagnostic SSBO.
Image-producing arithmetic is retained; the new 10-capture pilot has identical
direct/indirect/total PFMs and primary-hit bytes to its N009 state controls.
Producer payload order can differ and is not asserted byte-identical.

The extra diagnostic output is counted in the allocation ledger. These
captures are not accepted performance evidence. Output names n010_hwrt_composite
and n010_software_composite are unique; all historical shader outputs remain.
