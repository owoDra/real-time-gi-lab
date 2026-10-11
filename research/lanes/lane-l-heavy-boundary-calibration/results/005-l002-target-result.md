# L002 — target detectable-effect floor result

## Formal outcome

**measurement-floor-established**

L002 completed at measurement commit
`b8bb76f728ee329cf4daef5855a05972757072f6` on
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

Accepted heavy-boundary measurement environment:

- `dual-context`

Accepted detectable-effect floor:

- **20%**

This is a measurement-method capability result only. No architecture candidate
was ranked.

## Campaign completeness

The frozen L002 campaign completed:

- 20/20 correctness/provenance validations;
- 160/160 fresh timing processes;
- 5,120 retained raw timing rows;
- zero sample exclusion;
- zero instability rerun;
- zero completed-campaign rerun;
- consistent device/driver/API/timestamp provenance.

All validation rows passed output identity and allocation-lifetime checks.

## Frozen detector

For every environment × profile × control family, the injected factor had to:

1. strictly exceed the fresh same-variant combined control-noise envelope;
2. keep all eight fresh-process median B/A ratios above 1;
3. keep both AB and BA stratum medians above 1 in every process;
4. keep the minimum positive-pair fraction at or above 0.75.

All five profiles × both incumbent controls had to pass independently. No
profile averaging was allowed.

Detection was required to be contiguous in the order +20% -> +10% -> +5%.

## Environment results

### dual-context

- +20%: **10/10 controls PASS**
- +10%: **4/10 controls PASS**
- +5%: **1/10 controls PASS**
- smallest contiguous environment-wide passing effect: **20%**

The +10% failures are primarily explained by the synthetic factor not exceeding
the fresh control-noise envelope. Several controls also fail the directional
positive-pair requirement.

### single-context-independent-runtime

- +20%: **9/10 controls PASS**
- +10%: **3/10 controls PASS**
- +5%: **0/10 controls PASS**
- accepted floor: **none**

The sole +20% failure is
`medium-global-representative/software`. Its +20% factor does exceed the fresh
control-noise envelope, and all process/AB/BA medians remain positive, but the
minimum positive-pair fraction is 0.666667, below the frozen 0.75 requirement.

Therefore the single-context environment is not reusable under the frozen L002
decision rule.

## Decision

The predeclared decision mapping yields:

- outcome: `measurement-floor-established`;
- accepted environment: `dual-context`;
- accepted heavy-boundary floor: **20%**;
- `single-context-independent-runtime`: rejected for formal downstream use;
- architecture ranking performed: false.

A downstream architecture experiment may use this result only if it prospectively:

- uses `dual-context` pairing;
- imports the exact heavy recurring-boundary protocol;
- sets any promotion threshold to **no smaller than 20%**;
- retains fresh run-local same-variant controls;
- retains correctness, memory/lifetime, and provenance gates;
- retains zero sample exclusion and zero favorable rerun.

Lane K's 5% calibration remains valid for its own calibration workload, but does
not override this heavy-boundary-specific 20% floor.

J004 remains `measurement-limited` and J005 remains forbidden.

Lane E / Issue #22 now satisfies its Lane-L entry dependency and may begin a new
prospective timing revalidation under this 20% heavy-boundary floor.
