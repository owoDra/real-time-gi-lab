# Signed residual correction030: six quality rejections, no GPU

**SIX_TARGETS_COMPLETE_0_JOINT_PASS_6_QUALITY_REJECTIONS_NO_GPU.** All six
ordered cases and independent numeric audits are valid. All six empirical variance
ratios exceed1.20; all six signed AND clipped estimates fail the original10%
indirect NRMSE gate. Zero joint passes, six scientific quality rejections, zero
pending. Variance reduction at failed quality is not an accepted speed advantage.
Lane M remains incomplete.

[Registration030](../experiments/030-signed-residual-scoring-and-provenance-correction.md)
was committed9749ac96 before implementationf05bb2f2 and any new tests/scores.
[Contracts195](195-signed-residual-correction-cpu-contracts.json),
[full summary196](196-signed-residual-correction-six-target-summary.json),
[preservation198](198-signed-residual-correction-six-target-verification.json).

| Target | Groups | Empirical E | Baseline indirect NRMSE | Signed indirect NRMSE | Clipped indirect NRMSE | Signed total NRMSE | Signed indirect bias | Joint |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| H01/B2 | 190 | 2.29239 | 19.6985% | 12.8144% | 12.7924% | 2.5000% | -0.0923% | FAIL |
| H01/B8 | 190 | 1.73511 | 22.3102% | 16.5542% | 16.5376% | 4.2762% | -0.2401% | FAIL |
| H02/B2 | 185 | 2.50822 | 18.8055% | 12.1384% | 12.1318% | 2.0116% | -0.2627% | FAIL |
| H02/B8 | 185 | 1.64173 | 22.5247% | 17.9644% | 17.9103% | 3.6333% | -0.2284% | FAIL |
| H03/B2 | 212 | 1.95438 | 20.5219% | 14.7564% | 14.7088% | 3.1825% | 0.1434% | FAIL |
| H03/B8 | 212 | 1.56524 | 22.2698% | 17.6354% | 17.5463% | 4.3212% | -0.1920% | FAIL |

All candidates use the identical64 physical paths/pixel including eight raw
training contributions and56 held-apart physical residuals. Actual026 n1 inputs,
all pixels, original16384spp/four-seed references, normal/owner/material/world-axis
8^3 cells, nine features, trace ridge and original gates remain unchanged. All
candidate total/direct/bias gates pass; the indirect10% gate rejects every case.
This is a static64-path batch estimator, not a passing1spp temporal image.

New15 actual CPU contracts pass, including signed analytic bias/support/clipping,
physical-scorer agreement, invalid/zero references, role-specific direct guards,
independent metrics and thresholds, injected-failure input durability,
reference-manifest-before-decode and exclusive/order/no-GPU safeguards. The old15
contracts are rehashed/reused, not repeated; their missing signed integration
coverage and the stopped029 failure remain visible. Only candidate signed
indirect/total permit negatives; all physical/direct/reference guards remain.
Both scorers count candidate<=0 at positive reference support consistently.

H01/B2 reuses all five EXACT029 frozen artifacts without production refit,
correction or replacement image. Its original native manifest remains missing;
030 identifies the published post-failure reconstructed inventory and original
026 source, without inventing native chronology. The other five production fits
run once in new outputs, retaining expected identities before each frame read,
verified intake/training/evaluation and reference-before-decode manifests. Each
terminal receipt keeps inputs even on errors. Six independent audits recompute
all group coefficients via augmented SVD, all56 corrected full fields, all images
and moment drift, then fsum variances/HDR metrics and full error maps at original
tolerances. Actual saved signed values retain support near zero. All scientific
decisions match. Independent first-secondary intersection coverage remains only
original026 frames0/1/63; no new intersections/all64 intersection claim.

Full signed frame samples/images/errors, coefficient errors, per-pixel variance,
all phase/source/consumed-input manifests and clipping/moment-drift diagnostics
remain in repository out/. CPU wall/RSS/field/array bytes and operation counts
are diagnostic, not GPU time, hardware query counts, full-system cost or memory
superiority. E is an observed deterministic saved-seed variance proxy; all
training paths are included but additional arithmetic/fit/storage costs still
need measurement. It is not a confidence interval or exact finite-RNG/float32
unbiasedness proof. Display clipping is not claimed unbiased.

030 ends with no additional fit, extra samples, changed grid/ridge/split, retry,
setting sweep or GPU continuation. This fixed64-path component fails its
feasibility gate despite useful observed residual correlation. A different
architecture or budget/representation requires a separate falsifiable study;
these outcomes cannot select an unregistered rescue. Control variates,
regressions and incident-radiance caching are prior art; novelty is unproven.
Complete calibrated quality-matched representative-family comparisons, actual
novel competitive Renderer transport, independent new heldouts, dynamic camera/
light/rigid/deforming/topology/churn, Sponza/other scenes, multiple GPU classes,
full persistent/true-peak memory and deployability remain required.022 forbids
accepted raw-PT-only speed ranking. Incumbent SRC/default build/main unchanged.

New GPU acquisitions0; audited assistant total184. No new reference/path samples,
SDK/native compilation, CI/Actions or power/clock/desktop changes. Default Renderer
build/runtime NOT_RERUN; validation layers NOT_RUN. Lane M and Issue7 remain OPEN.
