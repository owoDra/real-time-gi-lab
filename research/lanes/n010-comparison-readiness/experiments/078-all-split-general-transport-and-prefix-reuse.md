# N010 prospective all-split general transport and prefix reuse

Date:2026-10-17 JST. Parent:6826fe1. Before new compile/acquisition.
218 small promising PASS and220 bounded derived rho1 furnace PASS remain
limited evidence. This implements the adapter needed for original17 controls;
it does not substitute those controls with the prior eight-pixel studies.

## Physical target and proposal separation

Keep original193 physical sample/direct/BVH/nudge/offset source verbatim and
218's point-proposal maps, uniform splits, raw targets and numerical audits.
Support centre cameras, exactly one point source, no emission,1..8 vertices,
nonnegative RGB Lambert materials, both original sidedness flags and either
original point falloff. Reject other scopes before rendering. Do not link
any new code into default Renderer/CMake. No transport law changes.

At a k-vertex indirect path, original per-channel integrand is q_0 times
rho_primary * product(rho_xi,i=1..k-1) * R_k, where R_k is original direct
at x_k including its own rho/pi. Multiply by zero if ANY forward hit is a
one-sided back face. That forward decision uses original dot(ng,w)<0.
The proposal may continue through a back-face/black vertex, but its physical
contribution is zero, never reflection from that face. q_j remain geometric
proposal densities; do not incorrectly remove reverse proposal support based
on the physical forward sidedness. At a primary back face or black material,
return original zero before requiring a direct-cache value that original
sample never populated. Max depth uses actual scene.max_bounces, so B2 is
exactly k=1, not an eight-bounce sum. Primary direct remains original bytes.
On coincident matching additionally require identical forward-front flags
for one-sided materials; different winding cannot interchange front/back.
All072/074 numerical approximation caveats remain; no spatial-bias proof.

## Derived prefix reuse, same proposal/output

For a fixed joined path, ordered E(prefix length i) depends only on that
prefix; L(reverse suffix length j) similarly. Traverse each order ONCE,
record each cumulative log density, then q_j=E[k-j]+L[j]. Subsequent support
zeros make all longer densities zero. Preserve exact ordered floating sums,
canonical states, area formulas, bounds and actual alternative-self checks.
This removes repeated prefix traversal, not any proposal or scored sample.
Compute the forward material product during the E pass, prior to endpoint
R. Multiplications by1 preserve old rho1 contribution ordering. Keep the
unchanged218 sampler as a separate legacy method in the isolated header.

## One build and C1 exact-equivalence diagnosis222

Work `all-split-general-transport-v1`; result
`222-all-split-general-transport-equivalence.json`. Same C1 eight fixed pixels,
8192/four original seeds. One compiler/native, one CPU nice15,4GiB/220CPU/
300elapsed each, no retry/GPU/concurrent research worker. For EVERY sample
compare old/new component RGB and all eight depth values bit-for-bit; any
difference stops. All32 accumulated means/second moments must match218 bits;
original193 controls and all prior numerical/own-density/strategy/weight
checks remain. Record hashes/inverses and actual process limits/termination.
This exact-equivalence check establishes only the unchanged C1 rho1 D8 case;
it is NOT validation of added material/back-face/depth cases or all17 controls.
A future bounded/general full-control acquisition must validate those before
any all-state/prefix, whole-frame feasibility and original qualification.
No new promising cutoff or selection based on this equivalence run. Keep all
original failures and scientific thresholds/seeds/slots/levels/cap. References
16/24; timing208FAIL; direct1.0 pixelsUNRESOLVED/未解決 included. No settings/
Actions/N011/default build/N001–N009 result changes. Unit/regression tests
NOT RUN; isolated research implementation and scientific equivalence only.
