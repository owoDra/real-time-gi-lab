# N010 Amendment 1 — frame-direction precision and initial state lock

Date: 2026-10-14 JST. Prospective for N010 Renderer-state indirect/total
references: none has been acquired yet. N009 archived direct diagnosis and
N010 analytic sampler controls informed this implementation audit.

N008 n008lib.state_scene constructs the camera target with numpy float32
origin + forward, then Camera.forward subtracts the origin in float64. The
first addition loses direction precision for large world coordinates. This
is separate from the direct shadow-offset error. Initial N010 diagnostic
001 reconstructed the intended frame direction; corrected diagnostic 005
reproduces N008's float32 target and edge nudge for archived causation.
Both records remain available; 001 is a preliminary approximation.

New N010 state references preserve the actual exported direction: convert
origin/forward to float64 before constructing target = origin + forward.
All other N008 transport/intersection/falloff/offset/material definitions
remain verbatim. The frame/geometry state bytes stay unchanged; the authored
reference scene gets its own new SHA-256. The unchanged N009 reference
images/classifiers and SC NO GO are not rescored or replaced. This is a
prospective camera-contract precision correction, beyond the sampling-only
change allowed by original N010 section; disclose it separately.

Initial state lock 004 records C1/C2/C4/C5/C6 and C7 from the authoritative
N009 state exports/captures. All cells and both T_B2/T_B8 are retained,
without selection based on candidate quality. C6 is an oracle state until a
new churn-capable GPU acquisition is implemented. Source Sponza state is C1.
Light motion and the additional non-Sponza dynamic states remain required
work; this partial lock does not pass corpus readiness. New light selection
uses geometry/direct evidence only and must be locked before new indirect
acquisition. No N009 C3 rescue is implied.

Sampler physical controls use their unchanged analytic cameras and are
unaffected by this amendment. Eligibility thresholds, four replicate seeds,
8192–262144 levels and two-level support-aware qualification are unchanged.
