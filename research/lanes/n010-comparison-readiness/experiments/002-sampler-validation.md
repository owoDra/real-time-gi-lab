# N010 sampling-only oracle validation freeze

Frozen before new validation rendering; supplements [001](001-comparison-readiness.md).
Source overlay: initial sampler implementation at cbf9d50. Physics remains
the verbatim N008 integrator. Point lights and centre camera sampling only;
no emitter validation or independent Mitsuba rerun is claimed.

Applicable exact analytic controls: N008 A2 inverse square, A2b soft falloff,
A4 sidedness/shadow, A8 transformed rigid poses. Reuse their unchanged
expected-value code and 1e-9 f64 / 1e-6 PFM thresholds, 64 samples per
replicate, four fixed seeds. Analytic control boundary masks are reported;
these do not authorize exclusion in comparison corpus quality scoring.

Sampling-sensitive controls: A6 off-centre coloured sphere furnace at two
and eight vertices, A10 secondary rays beyond camera far, and A7 nonsymmetric
floor/ceiling quadrature. Resolution remains 128×96. Four fixed seeds,
8192 samples per replicate; retain A6's 256-sample level-5 diagnostic as
diagnostic only. For stochastic indirect: per-channel image/region mean
relative error <=0.2%, whole-region RGB normalised RMS error <=1%, compared
to analytic/quadrature expected values. Furnace tessellation is the original
level-6 mesh. Direct furnace errors use the unchanged explicit geometric
allowance. No iid confidence bounds are used for randomized-net samples.

Additional no-leak control: sealed shared-edge two-room mesh from N008 A9a,
centre camera in the unlit room, 128×96, four seeds ×1024 samples ×8 vertices;
all component first/second moments must be exactly zero. A9b lit room has
strictly positive direct and total on every pixel under the same settings.

Cross-sampler validation: the same A7 and coloured off-centre A6b states
with unchanged iid N008 oracle, four seeds ×8192 samples. Difference of
per-channel whole-image mean <=0.2%, plus <=1% whole-image normalised RMS.
These absolute requirements are frozen before their new images. All failed
controls are retained; reference acquisition requires every applicable gate.
RQMC uncertainty in new acquisitions is estimated across independent
replicate means; per-sample second moments remain descriptive.
