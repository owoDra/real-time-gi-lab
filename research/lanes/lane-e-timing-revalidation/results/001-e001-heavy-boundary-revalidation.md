# E001 — Lane E heavy-boundary timing revalidation

Status: **accepted; Lane E rigid and stable-topology-deforming timing revalidated**

## Decision

The existing Lane E object-local ownership/update architecture remains the
accepted incumbent for the two formal dynamic classes covered by this follow-up.

Under the prospectively frozen Lane-L heavy-boundary protocol:

- moving-rigid is revalidated for both HWRT and software fallback;
- stable-topology deforming is revalidated for both HWRT and software fallback;
- no static/camera/light guard track shows a detected >=20% regression;
- all frozen correctness, provenance, allocation-lifetime, and hard memory gates
  pass;
- fresh same-run evidence does **not** falsify the previous Lane E performance
  claim.

This result does not make a topology-changing performance claim.

## Frozen measurement contract

Measured source commit:

`816b0b68fa416422eab1451c7929b6fc0ff93dc4`

Frozen plan:

`lane-e-timing-revalidation-e001-v8`

Imported measurement capability:

- Lane L dual-context environment;
- GPU timestamp primary;
- complete CPU wall diagnostic/health/provenance only;
- 20% demonstrated heavy-boundary effect floor;
- 4 warmup + 12 measured pairs per process;
- 8 fresh-process blocks;
- 16 complete reversible transitions per timed role sample;
- frozen AB/BA counterbalancing;
- 1 second process settle;
- no sample exclusion;
- no instability rerun;
- no completed-campaign rerun.

The Lane-K 5% floor was not transferred to this heavier recurring boundary.

## Target and retained evidence

Target:

- GPU: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- driver: RADV / Mesa 26.1.2;
- scene: Sponza01.gltf;
- scene SHA-256:
  `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`.

Retained campaign:

- validation processes: **20**;
- validation rows: **80**;
- timing processes: **160/160**;
- timing rows: **5,120**;
- warmup rows: **1,280**;
- measured rows: **3,840**;
- all samples retained.

Validation passed exact Hit/tie, visibility, producer semantics, traversal
runtime, storage, static/unrelated owner mutation, workload identity,
resolved-output identity, geometry identity, allocation lifetime, and
device/driver/API/timestamp provenance gates.

## Formal dynamic performance

All ratios are candidate/control on complete GPU time. Lower is better.

| Class | Track | Candidate/control | Improvement | Fresh-control noise envelope | Direction gate | Frozen classification |
| --- | --- | ---: | ---: | ---: | --- | --- |
| moving-rigid | HWRT | 0.330894x | 66.91% | 1.035249x | PASS; all measured pairs directional | >=20% detected improvement |
| moving-rigid | software | 0.519178x | 48.08% | 1.032987x | PASS; all measured pairs directional | >=20% detected improvement |
| stable-topology-deforming | HWRT | 0.331625x | 66.84% | 1.036182x | PASS; all measured pairs directional | >=20% detected improvement |
| stable-topology-deforming | software | 0.525108x | 47.49% | 1.033022x | PASS; all measured pairs directional | >=20% detected improvement |

For every formal dynamic track:

- all eight process medians are in the improvement direction;
- both AB and BA strata are in the improvement direction;
- minimum directional measured-pair fraction is **1.0**, above the frozen 0.75
  requirement;
- the detected effect strictly exceeds the run-local control noise envelope.

Therefore both formal classes satisfy the frozen 20% revalidation rule on both
traversal tracks.

## Stable guard classes

These classes are guard evidence, not promotion targets.

| Guard class | Track | Candidate/control | Fresh-control noise envelope | Frozen classification |
| --- | --- | ---: | ---: | --- |
| static | HWRT | 0.926757x | 1.140447x | <20% difference / measurement-limited |
| static | software | 1.100951x | 1.106408x | <20% difference / measurement-limited |
| camera-motion | HWRT | 0.938982x | 1.192828x | <20% difference / measurement-limited |
| camera-motion | software | 1.081134x | 1.128345x | <20% difference / measurement-limited |
| light-motion | HWRT | 0.983406x | 1.216874x | <20% difference / measurement-limited |
| light-motion | software | 1.091202x | 1.101427x | <20% difference / measurement-limited |

No guard track crosses the frozen >=20% regression threshold. Sub-20% movement
is deliberately not promoted into an architecture conclusion.

## Memory

The frozen hard guard requires, in every same-run measured pair:

- persistent candidate/control <= 1.25x;
- true-peak candidate/control <= 1.25x;
- complete allocation-lifetime accounting.

Formal dynamic maxima:

| Class | Track | Persistent max | True-peak max | Allocation lifetime | Classification |
| --- | --- | ---: | ---: | --- | --- |
| moving-rigid | HWRT | 1.000006x | 0.972049x | complete | neutral |
| moving-rigid | software | 1.004510x | 0.939092x | complete | neutral |
| stable-topology-deforming | HWRT | 1.000006x | 0.972298x | complete | neutral |
| stable-topology-deforming | software | 1.004516x | 0.940502x | complete | neutral |

All hard memory guards pass. The classification remains neutral because the
frozen memory-improvement rule requires pairwise non-worsening on both decision
axes, not merely a lower true peak.

## Post-measurement finalization recovery

The 160-process timing campaign completed before the original runner stopped at
its final validation/timing provenance comparison.

The only reported difference was timestamp-period string rendering:

- validation writer: `10.019`;
- timing writer: `10.019036293029785`.

The runtime source value is the same Vulkan `float timestampPeriod`. Timing
rows inherited `std::setprecision(17)`, while validation rows used the default
ostream precision. Device name, driver name, driver info, and API version were
exact matches.

No process was rerun and no measured sample was excluded. A post-measurement
finalizer was added after the frozen measured commit. It verifies:

- the original v8 source commit and frozen blob manifest;
- the original scene digest;
- exactly 20 validation process IDs and accepted validation PASS;
- exactly 160 frozen timing process IDs;
- exactly 32 rows per timing process and 5,120 total rows;
- all original timing health checks;
- exact non-timestamp provenance;
- only the known timestamp serialization equivalence.

The user then finalized the retained artifact successfully with
`measurement_rerun = false`.

This recovery changes post-processing only; it does not change or recreate the
accepted timing evidence.

## Architecture interpretation

The revalidated mechanisms remain:

### Moving-rigid

HWRT:

- immutable object-local BLAS;
- rigid motion represented by instance transform;
- TLAS UPDATE;
- no recurrent rigid vertex upload or BLAS geometry update.

Software fallback:

- immutable object-local StrataBrick;
- conservative quantized Micro BVH8;
- explicit instance state;
- rigid motion updates instance state only.

### Stable-topology deforming

HWRT:

- update only changed object geometry;
- UPDATE only that object's BLAS;
- update TLAS after bounds/geometry change.

Software fallback:

- maintain only the changed object's local hierarchy;
- repack/upload only that object's payload and instance bounds;
- unrelated static ownership remains immutable.

## Limits

This conclusion is specific to the measured target, scene, recurring boundary,
and >=20% heavy-boundary capability demonstrated by Lane L.

It does not establish:

- cross-GPU generality;
- sub-20% performance differences;
- primitive-count-changing/topology-changing performance;
- a winner among future topology-changing object-local rebuild backends.

Those remain separate research questions.

## Final disposition

**Accept the E001 revalidation.**

Lane E's object-local ownership/update architecture remains the current
evidence-backed incumbent for rigid and stable-topology-deforming geometry.
The remaining decision-relevant architecture question is the
topology-changing/high-churn object-local rebuild backend under a qualified
same-boundary crossover.
