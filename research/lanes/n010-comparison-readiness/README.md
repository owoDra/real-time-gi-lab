# N010 — final comparison preparation

N010 is the final preparation study before **Lane M GI competitiveness**. It
must deliver executable comparisons, eligible references, correctness evidence,
quality matching, calibrated GPU timing and allocation-lifetime memory records.
The historical Lane M topology study retains its existing identity and results.

Protocol: [001](experiments/001-comparison-readiness.md). N001–N009 are immutable
inputs. The default Renderer is not promoted by this study.

Status: active; readiness has not been demonstrated. [Execution evidence and
remaining gates](results/008-interim-execution-and-resume.md). Actual GPU-key
replay passes on all 10 captures; the C7 key-driven counterfactual validation
passes V1–V4 on both backends. Direct shadow-offset diagnosis is post-hoc;
new physical sampler validation and comparison harness work continue.

New executable cohort: native GPU pixel PT and the separately frozen dense
repository RC estimator control. [C7 budget/quality results](results/013-c7-pt-cohort-pilot.json)
include all losses and passing PT levels. [Construction lock](results/016-corpus-state-lock.json)
contains source/target dynamics and local light motion. C7 and C8–C12 references
are eligible in both finite transports. The [dynamic cohort](results/019-controlled-dynamic-cohort.json)
retains all 145 executed source/target/recovery images, all losses and two
explicit software-churn capture limitations; [independent memory replay](results/020-controlled-dynamic-summary.json)
passes for all 29 roles. Sponza C1/C3 T_B2 references now qualify. [C1 quality comparisons](results/033-interim-comparison-findings.md)
show incumbent/dense RC FAIL and pixel PT PASS at 256/1024 spp. Remaining
Sponza reference acquisition and calibrated timing are in progress.
Historical vanilla-software is a traversal control, not a separate GI baseline.

[RTXGI provenance](results/021-ddgi-source-provenance.json) pins the fetched SDK
for the required additional Lane M DDGI comparator. The chosen path is Vulkan
on AMD, without CUDA. The [Vulkan host SDK builds](results/023-ddgi-vulkan-host-build.json)
and the [pinned CPU DXC runs](results/034-dxc-cpu-compiler-provenance.json);
integrated DDGI runtime is not yet demonstrated.

[Post-hoc CPU primary diagnosis](results/053-residual-primary-contract-diagnosis.md)
localizes both residual C1 direct-zero pixels to differing primary primitives
and supports a legacy tie-interval mechanism. No GPU repair is claimed; both
pixels remain unresolved and included in scoring.
