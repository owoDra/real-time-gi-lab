# N010 Amendment 3 — deterministic camera/direct cache

Prospective execution optimization, frozen before cached oracle acquisition.
Sponza reference acquisition is still running with the original validated
binary; keep its output, metadata and identity. No reference thresholds, seeds,
levels, support rules, transport or floating-point expression changes.

For centre camera samples and point lights with no emitters, the primary ray,
primary intersection and direct shadow result are constant across a pixel's
samples. A separate N010 oracle variant may cache the first primary Hit and
first direct result, then reuse them for later samples. All secondary paths,
RNG dimensions/order, sequential sums/second moments and per-sample counters
remain unchanged. Box sampling or emissive geometry is rejected. Do not
replace the existing binary while its acquisitions are active.

Before accepting any cached reference, require exact byte equality of the
f64 sidecar and every component PFM versus the original implementation for
all sampler physical controls, plus complete four-replicate 8192-SPP C1
Sponza T_B2 acquisition and both C7 transports. Metadata counters must match.
Record old/new binary and generated-source identities. If any equality fails,
retain the discrepancy and do not use cached output for qualification.
The accepted validation establishes computational equivalence, not a new
physical-validation or convergence rule. Cached qualification uses a distinct
output directory and records the equivalence proof. Historical failed levels
remain retained. No existing in-progress level is overwritten or discarded.
