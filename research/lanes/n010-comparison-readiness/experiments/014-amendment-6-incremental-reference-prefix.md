# N010 Amendment 6 — resume the exact randomized-net prefix

Prospective computational optimization, after C1/C3 T_B2 qualification and
before any incremental oracle acquisition. The original CPU jobs and their
accepted/partial payloads remain untouched. No physical expression, sampling
point, dimension, seed, level, cap, support rule or acceptance threshold changes.

The nested power-of-two ladder currently recomputes samples `[0,N)` at every
level. A separate cached oracle may restore the previous level's per-pixel
sums and second-moment sums, then execute only `[N,2N)` with the existing
sample-indexed Sobol generator and the same sequential floating-point additions.
All four seeds remain independent and fixed. Restoring sums from the f64
sidecar means uses exact power-of-two scaling; reject nonfinite values,
negative values, subnormal means or a failed encode/decode round trip.
Restore the original per-replicate integer counters from its hashed metadata.
The centre primary-hit record is regenerated without changing transport.
Reject mismatched state/scene, seed, sampler, binary/equivalence identity,
unsupported sampling/emitter scope or incomplete previous acquisition.

Before any incremental reference is eligible, require the complete Amendment 3
cached equivalence proof, unchanged physical sampler validation 009, and exact
f64/component PFM/primary-hit byte equality plus exact integer counters against
the already acquired original 16384-SPP **C1 T_B2, C7 T_B2 and C7 T_B8**, all
four seeds. Each replay resumes the actual original 8192-SPP prefix. The proof
also retains rejected-input outcomes for seed/dimension/header/round-trip
checks if encountered; no discrepancy can be masked or accepted with a
tolerance. A failure leaves the variant ineligible.

The first level remains a fresh cached 8192 acquisition. Later levels restore
that exact complete prior prefix. Qualification still evaluates and retains
every prescribed level, stops only at the first consecutive passing pair,
and caps at 262144. All previous f64/PFM/metadata hashes are recorded at every
continuation. New output lives in a distinct directory. No original binary or
in-progress level is overwritten. CPU time is diagnostic acquisition cost,
not comparative GPU performance.

Changing an existing reference runner is allowed only at a completed
cell/transport boundary after the equivalence proof passes, with explicit
provenance for every retained old result and any subsequent partial attempt.
The full C1–C12 corpus and both transports remain mandatory. N010 readiness
and Lane M timing/quality gates remain unchanged; this is not another study.
