# G003a — Immutable static-HWRT build-input release

Status: **pending target-GPU evidence**

This candidate is directly justified by G001's byte/lifetime census.

It releases only the static HWRT vertex build input, TLAS instance build input,
and shared AS scratch after the synchronously fenced immutable BLAS/TLAS build.

The unchanged transient-LBVH path is retained as the run-local control.

See `003a-immutable-hwrt-build-input-release-config.json` and
`results/003-memory-reduction-candidates.md`.

## Lifetime boundary correction

G003a measures a true lifetime peak, not only post-setup residency. The hardened
variant builds immutable static HWRT before shared frame/stream/storage
allocations, releases the three G001 setup-only allocations after the fenced
build, and reports:

`peak_resident_bytes = max(setup_peak_bytes, runtime_resident_bytes)`.

This ordering change is part of the same G001-justified lifetime-overlap
candidate; it does not alter traversal semantics or capacity.
