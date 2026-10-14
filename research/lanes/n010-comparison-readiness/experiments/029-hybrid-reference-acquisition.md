# Prospective hybrid reference acquisition after full validation

This is execution-method preparation within N010, after plans 025–028 and
before any high-sample hybrid qualification. It changes neither sampling nor
the reference eligibility screen. Original CPU acquisitions and their frozen
continuation remain active and authoritative for their current view.

## Admission prerequisites

Require complete PASS of 098 (all sixteen fixed original-8192 comparisons),
099 (all 68 applicable original physical-control replicates plus every
independent physical check) and 101 (all 96 locked-state/seed comparisons,
byte-exact low-level prefixes and all eight actual-level prefixes).
Verify the recorded input and output bytes, not only summary flags. Require
unchanged 009 physical sampler, 095 streamed build, 100 prefix build and net.
Missing/partial/failed proofs prohibit acquisition. An explicit proof-only
invocation records refusal without creating an acquisition work directory.

Use exactly the separately built prefix host from 100 and shared shader from
095. Start a fresh 8192 level, then restore only that acquisition's complete
previous mean/moment/raw-counter files. Do not import a CPU prefix that lacks
the raw per-pixel counter state or substitute a seed. Preserve every raw GPU
output, CPU-fallback statistic, ledger, command, stdout/stderr and hash.

The helper may acquire any explicitly selected subset of the locked 24 slots;
the final corpus still requires all 24 and a recorded fixed scheduling view.
Selection must be made before the helper's output exists. No accepted
scheduling transition or current-view replacement occurs merely by running
this helper. A future transition requires a separate executed provenance
record at a completed boundary and preflight support for this numerical
variant. Existing CPU reference results and failed GPU attempts remain intact.

## Unchanged screen and bounded execution

Use four fixed N007 seeds; levels 8192, 16384, 32768, 65536, 131072, 262144;
active p99 absolute <=1e-5, relative <=5%, stable support and two consecutive
qualifying levels. Re-execute the existing support-aware assessor. Stop at
the first qualifying pair; a cap failure is INELIGIBLE. All component moments
must be finite, geometry/state/header identities exact, fault flags zero and
owned Vulkan memory replay within 8 GiB with zero teardown. No masks.

Per-seed batch is 16 and CPU fallback uses 16 workers. One GPU producer at a
time. High levels do more work than the earlier fixed-8192 diagnostics:
prospectively bound each child to 4 GiB process address space, 172800 CPU
seconds and 43200 elapsed seconds. These are operational stop guards, not
quality thresholds or GPU performance criteria. Stop on first failure and
retain the complete/partial attempt without retry or overwrite. Reference
generation timing, including CPU fallback, is diagnostic and never a GI
baseline. No CUDA, power settings, default Renderer change, N011 or Actions.

The prefix host reports fallback counts only for its new sample interval,
while `total_paths` covers the full target prefix. Preserve the raw report
and explicitly record the new interval; do not divide those two quantities
to claim a whole-prefix fallback fraction.
