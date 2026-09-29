# G003a — Immutable static-HWRT build-input release

Status: **pending target-GPU evidence**

This candidate is directly justified by G001's byte/lifetime census.

It releases only the static HWRT vertex build input, TLAS instance build input,
and shared AS scratch after the synchronously fenced immutable BLAS/TLAS build.

The unchanged transient-LBVH path is retained as the run-local control.

See `003a-immutable-hwrt-build-input-release-config.json` and
`results/003-memory-reduction-candidates.md`.
