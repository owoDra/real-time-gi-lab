# Private execution: estimator identity and physical-evidence transfer

2026-10-19 JST. **POST-HOC source assessment** of162/164/165's existing
execution-qualification obligation. N010 **NOT_READY**. No sampler,
scientific threshold, corpus, required physical control or stop is changed.
This assessment concerns the exact existing candidate, not a new renderer.
Tests **NOT RUN**. No rendering, image replay, compiler or GPU operation.

## Source and executable boundary

Reviewed the actual [626](626-thread-private-cli-source.json) generated sources
and [627](627-thread-private-cli-build.json) executable identities. Rechecked
their SHA256 against those immutable records:

| Mode | File | SHA256 |
| --- | --- | --- |
|full|header|f2238e39eb3cb268188be7709643432b1b4d295e5259bf614fb1a7ae0db205eb |
|full|exporter.cpp|a8f03d1a3581037f92a44d3a37abb99c8f8c152570999218c73c4e2320e00ab5 |
|full|binary|7da13c4a718d8f6415c83d404f8968a2c7d7e10db63e9562abce6ce19eeb7a09 |
|prefix|header|f797ad867cdc1b7a760abf0a435f3afef619f7e7da2495d2332b0719bf96c9f8 |
|prefix|n010_rqmc_main.cpp|08b8541eb4cb816509773634c995d5e04511b51c713a1532e1629f08e9ce6941 |
|prefix|binary|b2d6e8689d671088693a053783808bc42d9dea545a528634ec6527b81219793e |

Both use the retained GCC15.2.0 compiler/flags from452/525/526:
`-mavx512f -std=c++20 -O3 -fno-fast-math -ffp-contract=off -pthread`, same
original include directory. Neither defines `N010_VERIFY_BVH`.
Using `prepare_thread_private_reference.transform`, regenerated both private
headers from original452/525 sources and confirmed exact equality to626:
seven reversible substitutions per header, exact whole-header inverse,
unchanged complete physical/density/geometry/sampling block and unchanged
`sample_all_split` body. Reversed626's two CLI substitutions per main and
confirmed exact equality to621's original copied mains. These are source
identity checks, not new scientific acquisitions or runtime validation.

## Ownership and arithmetic reasoning

1. **Every pixel retains one owner.** In full/header lines1583–1634 and
   prefix/header1583–1637, an atomic row allocator assigns each row once.
   Each owner visits its pixels and sample indices in original order. A
   pixel's statistics, primary record, optional checkpoint entry and primary
   cache are written only by that owner. Allocations/resizes precede the
   workers; joins precede output. Prefix statistics are copied from the
   original initial payload before workers and keep the same sample start.
2. **RNG and radiance order stay fixed.** `N010NetRng` derives values from
   seed/pixel/sample/dimension, without worker index. Its shared net is loaded
   before render and then read only. Scene, camera, emitter tables and BVH
   are also constructed before render and read only in the normal build.
   Each pixel's scalar component/total sums and second moments use unchanged
   expressions and sequence. No floating radiance reduction spans workers.
3. **Mutable diagnostic state is separated.** Two witness coordinates become
   thread_local. The witness-enabled flag remains false/read only in these
   mains. The normal render overload passes private WholeAudit/prime state;
   the old wrapper remains for serial callers. Global renderer audits reset
   before workers and are merged only after joins. Paired BVH counters are
   modified only by the debug macro, whose candidate guard requires one thread.
4. **Audit merging retains the declared quantities.** The complete pinned
   WholeAudit/RenderCounters layouts account for all integer scalars, strategy
   arrays, per-key counts, direct counters, prime count and finite nonnegative
   maxima. Integer addition (including defined unsigned modular arithmetic)
   and maxima do not change with grouping on this valid domain. Per-call
   shadow-counter differences are taken from the same worker's local audit.
   Audit totals do not feed sample selection, density, throughput or radiance.
   The inspected counter-dependent branch `unmatched_visibility++<8` only
   limits stderr diagnostics: its log count/order can differ across workers.
   Do **not** assert identical stderr bytes. Numerical and support failures
   still fail; this assessment does not turn a failed run into valid evidence.

Consequently these source changes preserve the compensated estimator and
per-pixel arithmetic under the same scene/net/seed/prefix/floating-environment
inputs and a valid terminal execution. They address ownership of diagnostic
state; they do not change the target integrand or proposal. This is a source
argument, supported by the scoped actual [625](625-thread-private-full-frame-equivalence-summary.json)
comparison: six full-C1/16spp/one-seed outputs and complete exported audits
are identical for original1 versus private4 threads on the **same CPU31**.
625 does not establish full state/prefix equivalence or multicore throughput.

## Transfer decision and remaining qualification

**Estimator-level transfer is justified for the exact above identities.**
Completed original compensated physical controls may be cited as evidence
about this unchanged estimator, with this source argument and625 attached.
There is no scientific reason to duplicate every analytical control solely
because diagnostic audit storage becomes private. This is the explicit
assessment requested by162/165; it is not automatic adoption of an old count.

**Execution/reference qualification is still incomplete.** All original
compensated full physical controls, A6b independent IID and separate level5
diagnostic must actually complete and pass. The complete private165/708
24-state/two-actual-C7, all-four-seed exact-prefix qualification remains
required for the private binaries before reference generation. It cannot be
replaced by625 or this source reasoning. Actual approved-load whole-frame
two-level feasibility and all unchanged convergence/support/SE/admission
rules also remain. A source/binary/compiler/input change invalidates this
specific transfer argument until assessed again.

At publication A6a's four-seed aggregate492 passes, compensated artifacts
are14/17 and refs16/24. A6b seed0 is live; no verdict is inferred from its
receipt. No private708, scientific ladder or reference admission is claimed.
This assessment leaves614's global finite-arithmetic density/support/
Jacobian/radiance-bias obligation open; estimator identity transfers existing
evidence and its limitations, not a missing bias theorem or unsupported claim.

No CPU load increase is authorized by this record. Current four-thread pilots
remain on CPU31; actual multicore throughput has not been measured. No host
settings change or native job was dispatched. Sponza direct-relative1.0 pixels
remain **UNRESOLVED / 未解決**, included. N010 then separate Lane M, no N011,
N001–N009/default-build/Actions changes or accepted comparative speed claim.

