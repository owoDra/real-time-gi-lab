# Compensated density, support and numerical bias: independent assessment

2026-10-19 JST. **POST-HOC assessment**, using the now-complete original
physical controls and state/prefix evidence. This continues614; it does not
replace614, amend a threshold or retroactively repair261. **N010 NOT_READY.**

## Decision and scope

The ideal estimator has the original forward physical target. The actual
implementation has passed the registered independent physical/IID accuracy
controls and numerical guards for the examined scope. This is sufficient to
attempt the **unadmitted, full-frame two-level feasibility acquisition** under
172. It is not a proof of zero finite-arithmetic bias, a global radiance-error
bound, reference admission, or permission to bypass the unchanged qualification
ladder. A feasibility result cannot establish physical validity by itself.

The finite-precision support convention remains an explicit approximation.
In particular, neither78 matching executions nor four agreeing replicates can
exclude a systematic Sponza-specific error. Keep that limitation in the eventual
admission decision; do not silently turn this assessment into a universal
finite-operator equivalence claim. Actual reference admission/dispatch remains
unimplemented and fails closed.

## Independent ideal-measure derivation and source correspondence

For a fixed source spawn o, the solid angle subtended by a target area dA at
x is `abs(n_x dot (x-o)/r) / r^2 * dA`, r=|x-o|. This follows by projecting
dA perpendicular to the ray and dividing by the sphere's squared radius.
The cosine hemisphere law integrates to1 (`2*pi/pi * integral_0^(pi/2)
cos(theta)*sin(theta) dtheta`); the first light sphere law1/(4*pi) also
integrates to1. Closest-hit/range/self-ignore restrictions remove outcomes;
their probability stays at a zero-contribution null outcome. There is no
conditioning on success or omitted normalization constant.

With previous raw vertices held fixed in each generation order, the canonical
nudge/offset spawn is fixed. Conditional densities therefore multiply as
`q_j = E_(k-j) * L_j`, including independently evaluated forward/reverse support.
This argument uses a triangular conditional construction, not reciprocity.
The unsampled middle connection is tested by the full forward target q_0;
it is not an additional sampled edge with a missing PDF. Since the mixture
contains q_0, ideal target support is covered. For n=k+1 strategies,
`F=q_0*R`, `qbar=sum(q_j)/n`, and `F/qbar=n*q_0/sum(q_j)*R` on target support.
The weight is nonnegative and at most n<=8. Summing correlated depth estimates
uses linearity of expectation, not an IID claim.

The reviewed **active whole_sample**, not whole_sample_legacy, reads14 net
coordinates, selects/remaps the split, generates eye then light branches,
retains nulls, concatenates the reversed light suffix and evaluates every
ordered q_j through whole_density_prefixes. Its actual log-sum-exp weight
is `(k+1)*exp(log_q[0]-largest)/sum`. It returns zero when q_0 has no support.
Forward RGB throughput uses primary and intermediate physical rho, forward
one-sided backface absorption, and endpoint original direct*rho/pi. Original
point falloff, shadow query, high-point nudge/spawn and far bounds remain.
No cached sampled density is substituted for a reconstructed cross-family PDF.

The exact32-bit selector calculation615 remains a **selection-only**2^-30
conditional discrepancy bound. Remapped grids, four actual digital shifts,
rounded intersections and cross-family visibility are outside that bound.
It is not a native radiance-bias bound or a fitted accuracy allowance.

## Finite arithmetic and genuinely independent evidence

139 retains the original high hit point for physical spawning while carrying
FMA/TwoSum residuals into all families' target deltas.450 independently checks
the failed witness with Decimal80 arithmetic. This fixes a demonstrated loss
of geometric bits; it changes weights and is not an exact finite-operator
identity proof.072/074's restricted coincident-axis-plane allowance requires
matching material, strict interiors, identical nudge/spawn bits, the original
normal allowance and actual alternative-ignore ray/direct checks. Those cover
evaluated rays, not every possible outgoing ray. No support mask is added here.

The independent physical evidence is now complete, rather than614's incomplete
inventory. All16 original gated controls pass:473–481,483,484,486,487 and
pooled492,496,500.529 is the separate diagnostic and remains **NOT_GATED**.
These controls check deterministic direct/backface/material/state behavior,
sealed visibility, independent quadrature, and original sphere/range targets;
they do not all constitute independent indirect-density experiments.

| Independent comparison | Observed relative RGB error/difference (maximum) | NRMSE |
| --- | ---: | ---: |
|A7 quadrature,486|1.04251e-5|.000444196791|
|A7 original IID,486|9.35685e-5|.007144046945|
|A6c analytic,487|8.16112e-5|.001383587510|
|A6a analytic,492|7.50959e-5|.000079006474|
|A6b analytic,496|7.95952e-5|.000297884204|
|A6b original IID,496|1.21124e-5|.000733499760|
|A10 analytic/range,500|7.95952e-5|.000297884204|

All use original per-channel.002 and NRMSE.01 criteria, original scenes,
four seeds, full pixels and original geometric direct allowances. The
analytical/quadrature targets and original IID estimator are distinct from
the candidate MIS estimator. A6b IID reuses accepted original16384spp bytes;
it was not rerun or replaced with a candidate self-comparison. A10 reuses the
sphere geometry, so it is not a separate statistical replication of A6b.
These observations constrain combined sampling/numerical/model error on the
registered controls; they do not isolate or upper-bound bias on every scene.

The now-complete708/734 independently qualifies execution: all24 locked states
and2 actual C7 cases, all4 seeds/full frames,78 steps and26 exact restored
comparisons. Maximum own-log2.4868995751603507e-13<=1e-6 and conditioned
fraction.7879659101024155<=1 satisfy the original guards. Unconditioned
77068299115.4783 remains diagnostic. This supports reconstruction/execution
health; it is not evidence of zero cross-family bias.717's source argument
transfers the same estimator to exact627 private binaries;720 additionally
checks four-core execution against retained original output bytes.

## Exact reviewed identities

| Artifact | SHA256 |
| --- | --- |
|[450](450-compensated-raw-target-arithmetic.json)|2b36be050674fd57d7078f279748f01e17a92a53b4168f4bbc32a125d117e787|
|[452](452-compensated-full-exporter-build.json)|57d7fb874689b80512489b97c0a1a8042315d7c89025770e755752639b6915ce|
|[614](614-compensated-density-support-source-assessment.md)|a80573cfa988610388bf550b5f7caf343bbdfd77945c6fb8ddf09f2be721f435|
|[615](615-compensated-split-grid-exact-arithmetic.json)|9bc2b06bd4ceb65a35a904e8384bef2a3f26e636d8825983ead79bb42dc07c87|
|[626](626-thread-private-cli-source.json)|45272802521e7995e733b659bc76a919ed55fa041f0b7fd054ee28607c7f8d35|
|[627](627-thread-private-cli-build.json)|64b6898db2a9c80e45518bb9b067de7242593fd0410b8a46e64b575f5d49c286|
|[708](708-private-all-state-prefix-summary.json)|440f7e8b448fab9aa8a9f9dfc24d02cfe0bcf8dfcb73c15dbdc43b629857c878|
|[717](717-private-estimator-identity-and-physical-evidence-transfer.md)|76972c1f2bcedc68cd8691f70cfa2f37fc3c3fd7493cd1aff1cfa6f10e36837b|
|[720](720-four-core-full-c1-equivalence.json)|2fe2270745612dbe4ebce6c1e0dcda74350850d637dee354175c04cf1d3583bb|
|[731](731-complete-physical-inventory-and-level5-diagnostic.md)|b420a206c99dd5ba7aca1b5a672915b650ef399f0c00cee8ec0add203a41c1db|
|[734](734-full-four-core-state-prefix-qualification-outcome.md)|723a014886bf89d5331986012a7e8d893262b5a9bc97c0f30c6821f6d4d38440|
|627 full header|f2238e39eb3cb268188be7709643432b1b4d295e5259bf614fb1a7ae0db205eb|
|627 prefix header|f797ad867cdc1b7a760abf0a435f3afef619f7e7da2495d2332b0719bf96c9f8|

Actual two-level feasibility, unchanged eight-slot reference qualification,
and explicit admission assessment/dispatch are next. Eligible refs16/24,
PT2/28, non-PT raw8/8 and quality replay4/8 remain. Sponza direct-relative1.0
pixels remain **UNRESOLVED / 未解決**, included. Tests **NOT RUN**; source and
retained-evidence assessment only. No Renderer/default build/N001–N009,
Actions, CUDA, power/display/driver/app changes. N010 then separate Lane M,
no N011; no accepted comparative speed or general-superiority claim.
