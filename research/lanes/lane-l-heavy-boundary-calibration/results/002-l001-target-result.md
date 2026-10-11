# L001 — target heavy-boundary calibration result

## Formal outcome

**measurement-limited**

L001 completed on `AMD Radeon 8060S Graphics (RADV STRIX_HALO)` at
`a542ea4f2cd8219b76f069f552435b492e163b9c`.

The campaign completed:

- 20/20 correctness/provenance validations;
- 160/160 fresh timing processes;
- 5,120 retained raw sample rows;
- zero sample exclusion;
- zero instability rerun;
- zero completed-campaign rerun;
- consistent device provenance;
- no architecture ranking.

Both measurement environments failed the unchanged J004 GPU control-health gate
for every required profile/control pair. Therefore L001 yields no reusable
heavy-boundary timing environment and L002 is required.

## Frozen gate

Per profile and control family:

- max absolute process-median ratio <= 1.02;
- process-median span ratio <= 1.03;
- max within-process order-bias ratio <= 1.02.

All three limits had to pass independently. All five profiles in both primary
and software controls had to pass for an environment to be reusable.

## GPU-primary observations

| Environment | Profile | Track | Max abs median ratio | Median span | Max order bias | Gate |
| --- | --- | --- | ---: | ---: | ---: | --- |
| dual-context | small-global-high | primary | 1.049403 | 1.053752 | 1.098723 | FAIL |
| dual-context | small-global-high | software | 1.091583 | 1.060097 | 1.147120 | FAIL |
| dual-context | medium-global-representative | primary | 1.095666 | 1.078143 | 1.085371 | FAIL |
| dual-context | medium-global-representative | software | 1.128611 | 1.186322 | 1.129121 | FAIL |
| dual-context | medium-local-high | primary | 1.049142 | 1.067297 | 1.144182 | FAIL |
| dual-context | medium-local-high | software | 1.106848 | 1.147141 | 1.112338 | FAIL |
| dual-context | large-global-high | primary | 1.099996 | 1.096765 | 1.045963 | FAIL |
| dual-context | large-global-high | software | 1.061867 | 1.081390 | 1.064165 | FAIL |
| dual-context | large-local-high | primary | 1.115482 | 1.116978 | 1.129172 | FAIL |
| dual-context | large-local-high | software | 1.022157 | 1.039269 | 1.061475 | FAIL |
| single-context-independent-runtime | small-global-high | primary | 1.056950 | 1.053441 | 1.063142 | FAIL |
| single-context-independent-runtime | small-global-high | software | 1.090337 | 1.101571 | 1.112370 | FAIL |
| single-context-independent-runtime | medium-global-representative | primary | 1.103402 | 1.077784 | 1.098079 | FAIL |
| single-context-independent-runtime | medium-global-representative | software | 1.197678 | 1.240232 | 1.107429 | FAIL |
| single-context-independent-runtime | medium-local-high | primary | 1.078429 | 1.115698 | 1.065342 | FAIL |
| single-context-independent-runtime | medium-local-high | software | 1.081046 | 1.123780 | 1.151671 | FAIL |
| single-context-independent-runtime | large-global-high | primary | 1.080477 | 1.064637 | 1.074653 | FAIL |
| single-context-independent-runtime | large-global-high | software | 1.063704 | 1.086729 | 1.051578 | FAIL |
| single-context-independent-runtime | large-local-high | primary | 1.122113 | 1.097255 | 1.054054 | FAIL |
| single-context-independent-runtime | large-local-high | software | 1.036411 | 1.072190 | 1.083591 | FAIL |

The single-context hypothesis is therefore not accepted as the explanation for
J004 control-health failure. It changed the noise pattern, but did not produce a
reusable environment.

No speed comparison between environments is used for this decision.

## Correctness and provenance

Every L001 validation row passed:

- resolved output identity matched;
- allocation lifetime accounting was consistent;
- role A/B resolved digests matched;
- required correctness-error counters were zero.

The outer experiment returned 0 from a clean worktree. The source provenance
matches the frozen L001 config and imported J004 source/shader identities.

## Artifact manifest

The target artifact set supplied for this result is anchored by
`003-l001-target-artifact-manifest.json`.

The 2.1 MiB raw CSV is identified there by SHA-256 and row count. It is not
duplicated into this branch by the GitHub connector session.

## Decision

Under the prospectively frozen L001 mapping:

- `dual-context`: FAIL;
- `single-context-independent-runtime`: FAIL;
- usable environments: none;
- outcome: `measurement-limited`;
- `l002_required=true`.

J004 remains immutable and J005 remains forbidden.

L002 must be a new prospective experiment. It may calibrate a detectable-effect
floor using known synthetic effects on fresh measurements of the same heavy
recurring boundary, but must not relax or reinterpret the L001/J004 1.02 / 1.03 /
1.02 gate.
