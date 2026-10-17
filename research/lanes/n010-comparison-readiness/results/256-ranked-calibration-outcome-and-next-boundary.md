# N010 ranked calibration outcome and next boundary

2026-10-17 JST. [Plan103](../experiments/103-ranked-process-median-calibration.md),
analysis and driver were committed in `d8341e4` before fresh acquisition.
[255](255-orderstat-uncertainty-c7-calibration-diagnostic.json) ran from
`5f5b761957ede1ec4e967154fc05d8f5e9c32558` after both original sealed controls
and CPU prototype254 terminated. One independent acquisition,24 processes,
no retries, no old250 samples pooled, no interim rank/count adjustment.

## Registered result: bounded C7 calibration capability PASS

The loaded/unloaded full Renderer GPU-time ratio interval, including the
registered control allowance and AB/BA hull, is
**[1.1386441286318703,1.242058969553914]**. Its multiplicative width
**1.0908227938138153** is within the unchanged1.20 resolution condition.

| Frozen103 check | Actual result |
| --- | --- |
| Same-role unloaded/loaded control median locations compatible | PASS, both orders |
| Effect intervals compatible after order-specific allowance | PASS |
| Positive effect after allowance | PASS, lower ratio1.138644>1 |
| Interval width<=1.20 | PASS,1.090823 |

This demonstrates detection of the frozen approximately20% neutral-work
target in the static repeated-frame C7 HWRT fixture. The measured increment
is not assumed to equal exactly20%. Raw process-median point ratios are
1.187604 AB and1.184627 BA; the point estimates do not replace the interval.
All24 sorted values enter each frozen rank4/rank21 interval; none is deleted.
For example an unloaded BA process log ratio of-0.264956 remains in the
evidence. No fixed2% stability gate is imposed by103, and a large observation
is not diagnosed as contamination merely because it is extreme.

The six raw median intervals reserve a6x16 family noncoverage bound
0.026607513427734375 under the registered independent-process/common-median
assumptions. Extending them with the control allowance additionally requires
103/100's conditional nuisance model; the calculation is not a universal
guarantee against systematic drift, contention, carryover or dependence.
This is a median capability result, not a tail-latency guarantee.

The JSON explicitly retains `diagnostic_only=true`, `accepted_timing=false`
and `DIAGNOSTIC_COMPLETE_NO_ADMISSION`. A bounded calibration capability PASS
does not accept candidate timings, complete all16 boundaries, or override
the existing N010 preflight. Earlier FAILs and250's inconclusive outcome
remain authoritative for their own registered methods.

## Executed integrity and resource checks

All24 natives exit0;5760 raw frames,1440 four-frame observations, warmups and
pre-native labelled schedules are retained. Every image matches original046
byte for byte. Neutral-work scratch validation and owned-allocation replay
pass in every native. Owned Vulkan true peak is500,371,904bytes in each;
all ledgers return to zero. Driver-private/CPU memory is outside that ledger.
Receipts confirm CPU31,nice15,30CPU/30elapsed limits per native. No other
scientific worker ran concurrently. No power/clock/display/driver/application
settings were changed. Work retained12,323,733,651bytes, below16GiB. The sum
of raw timed GPU intervals is0.936347271seconds, not total campaign GPU work
or wall time. No follow-up or full campaign was queued.

Immutable255 JSON SHA-256:
`e71e9f9c17852fc3399660c79dce370850f7b4e0a90ea3ecab37f921b1cd864d`.

## Concrete next work

Stop generic attempts to satisfy the old stability percentages. Carry103's
registered design into a separately preregistered capability check on the
actual selected full Renderer boundaries and quality budgets, preserving
dynamic semantics and all costs. A static batch fixture cannot automatically
qualify history-dependent dynamic frames, another GI role or another device.
Freeze candidate/state multiplicity and any final proof-intake amendment
before accepted Lane M measurements. Do not pass a diagnostic through an
auditor expecting a different method or frozen identity.

For an eventual candidate/baseline time ratio, the prospective100/103
practical margin is1.20: a win requires the entire uncertainty/bias interval
below1/1.20; a loss requires it above1.20; equivalence requires it inside
[1/1.20,1.20]; otherwise inconclusive. Quality parity, true peak and dynamic
requirements remain separate. Calibration success is not a GI superiority
result. Valid quality losses remain reportable when timing is inconclusive.

The independent CPU [254 prototype](254-wide8-cpu-bvh-prototype.json) also
terminated PASS:53,415,447 full-query pairs,10,456,548,434 acquired box and
1,933,448,022 cached box comparisons, original223 entire payload and all21
original236 A6a payload/audit identities pass. Its uncontrolled single-run
CPU cost21.626573/42.641725=0.507169 meets102's operational<=0.75 condition.
It is a promising execution backend, not accepted full physical/state/prefix
proof or a scientific GI speedup. Its next step is bounded backend coverage
and full-count resource planning before the remaining original artifacts;
no long control or reference campaign was dispatched here.

Original sealed-dark252 and sealed-lit253 both physical PASS; original full
inventory is13/17, references16/24. Four sphere/range artifacts, A6b IID,
numerical-bias/all-state/prefix/feasibility and missing qualification/pilots
remain. Full-corpus quality/dynamics/truepeak and DDGI scene GI still need
their required evidence. Direct maximum-relative-error1.0 pixels stay
**UNRESOLVED / 未解決**, included. N010 remains **NOT_READY**; no N011.

Build/unit/regression tests: **NOT RUN**. Scientific acquisition and its
registered image/scratch/ledger/numerical identity checks above were executed.
Renderer/shader/default build graph and N001–N009 results remain unchanged.
Metadata-only `python scripts/research/verify.py`: OK,8 configured lane
indexes/256 declared result links. `git diff --check`: clean. Neither check
is runtime validation or a substitute for the outstanding readiness gates.
