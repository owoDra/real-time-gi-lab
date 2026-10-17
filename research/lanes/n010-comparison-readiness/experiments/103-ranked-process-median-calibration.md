# N010 prospective timing Amendment — fixed ranked median intervals

Date2026-10-17 JST. Parent e8030b9; prepared while253 CPU control is active,
BEFORE any new GPU acquisition. Plan100/250 is complete/inconclusive and
stays stopped. No old samples enter this method, and no old rule/outcome is
changed. Commit this plan, analysis and driver before acquisition.

## Diagnosis and finite follow-up question

251 reports that the twelve-process min/max interval is sensitive to the
large process11 loaded-control median. The process is retained. This is a
known precision/power cost of the confidence construction, not proof that
the observation is erroneous or should be excluded. Ask whether a separate,
fixed24-process acquisition and its exact binomial-derived median interval
can resolve the same original approximately20% additional-work target.

Keep100's estimand, three kinds, per-kind balanced AB/BA order, four warmup/
six measured paired rounds, four consecutive frames/observation, both-load
controls, conditional nuisance model, conservative allowance/hull, all four
checks,1.20 interval-width criterion and prospective practical ratio margin.
No tighter GPU claim, changed workload boundary, control point subtraction,
outlier removal or stability-percentage gate. Approximate target work is not
an assumed exact GPU-time increment. Preserve all failures and raw data.

## Exact changes frozen before new data

1.24 fresh processes, each60 observations/240 actual frames;1440 mean
observations/5760 actual frames total. No adaptive extension, interim stopping
for a favorable statistic or repeated completed campaign. Preserve all warmups.
The new independently randomized schedule label is
`N010-plan103-ranked-process-median-v1:<block-index>` with the unchanged
SHA-256/Random construction; save every labelled schedule before its native.

2.For each of the six kind/order populations, sort all24 process summaries
and take `[x_(4),x_(21)]` as the median interval (one-based ranks). Report all
24 ranked values and the median of all24. This is a registered order-statistic
interval, not deletion of three high/low processes: those observations remain
in the input, sample count, point estimate, ranks, all other diagnostics and
retained raw evidence. No value-based filtering or changing the chosen rank.

Under100's independent-repetition/common-median assumptions, noncoverage per
closed interval is at most
`2*sum(comb(24,j),j=0..3)/2^24 = 0.0002771615982055664`.
For the reserved6x16 calibration family, the union bound is
`0.026607513427734375`, hence >=97.33924865722656% coverage for the raw medians.
Rank5 would give family noncoverage0.14821243286132812, exceeding5%; rank4
is the largest rank admitted by the fixed95% family requirement at n=24.
The conditional control allowance is not a universal systematic-bias guarantee.
Cross-process dependence, nonstationary common medians or workload-specific
carryover remain limitations; both order and same-role compatibility checks
remain mandatory. Confidence in a median is not a guarantee about tail latency.

The statistical basis is the binomial/order-statistic construction described
by [NIST median confidence limits](https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/mediancl.htm).
NIST does not validate our GPU fixture or conditional nuisance model.

3.Before each process require24GiB disk free; total new retained work<=16GiB
to accommodate double the raw observations. All original per-native GPU/CPU
spool, owned8GiB/zero-teardown/image/scratch/identity guards are unchanged.
One CPU31,nice15; each native<=30CPU/30elapsed; one-second settle. Keep100's
180second campaign acquisition budget: do not launch a further native once
it is exceeded. No power/clock/display/app/settings changes or idle demand.

## Preconditions, classification and scope

Do not dispatch while253 or any other research worker is active. Both252/253
must have terminal physical PASS;254 CPU prototype must have a terminal
complete/failure classification. The common worker guard still applies.
These are explicit manual invocations, not a waiting/acquisition queue.
Use unchanged206 binary/shaders/timed commands and frozen246 dose1301, exact
same environment/boot/device/driver/image baseline. No new sizing/tuning.

One independent acquisition only. All four100 checks must pass for a bounded
C7 calibration PASS; otherwise timing capability remains **inconclusive**,
or operational failure with partials on integrity/resource failure. A result
does not automatically queue an extension or another sample-count change.
The old12 samples are never pooled, reclassified or used to choose the new
rank. Repetition count and rank are both fixed here before viewing new data.

This remains static repeated-frame C7-only capability, not acceptance of all
sixteen boundaries, individual-frame/dynamic timing or Lane M comparisons.
Actual selected boundaries need separate accepted calibration and the final
preflight; candidate/state multiplicity/quality coverage must be registered
before architecture timing. Quality losses, all24 reference slots, all17
physical artifacts, memory/dynamics/DDGI remain. Direct-relative1.0 pixels
stay UNRESOLVED/未解決 and included; N010 NOT_READY.

Driver: scripts/research/n010_reference_sampling/diagnose_orderstat_uncertainty_c7.py
Analysis: scripts/research/n010_reference_sampling/timing_uncertainty_orderstats.py
Work: out/research/n010-comparison-readiness/orderstat-uncertainty-c7-diagnostic-v1
Result:255-orderstat-uncertainty-c7-calibration-diagnostic.json (absent until run).
No Renderer/default graph/shader/N001–N009 result changes, Actions or N011.
Tests NOT RUN; this is a registered scientific acquisition, not regression validation.
