# Full-frame hybrid execution candidate: unchanged admission gates

093 passes the fixed selected-pixel numerical gates using the general 64-epsilon
ambiguity guard of plan 024 and original CPU whole-path recomputation. This
is only selected feasibility. Keep the guard and every Amendment 7 admission
threshold unchanged for a separately retained full-frame implementation.

Stream a maximum of 16 samples per pixel per dispatch, recording GPU sample
components, exact counters and path ambiguity flags. CPU workers accumulate
samples in their original order per pixel and independently recompute complete
flagged paths with the original sampler. Preserve every path. Use no stored
reference radiance, hit override, normal canonicalization, or scene-specific
primitive list. Keep the original CPU/GPU binaries and all failed outputs.

Before admission require all sixteen frozen 8192-spp/four-seed C1 T_B2/T_B8
and C7 T_B2/T_B8 cases, applicable original independent physical controls,
all-24-state/four-seed 16-spp controls, and exact deterministic fresh-versus-
continued prefix proof. A first failure is terminal for that attempt, with no
accepted threshold adjustment or reference scheduling transition.

The prototype's first full-frame execution is C1 T_B8 seed 0 at 8192 spp,
the retained failed deep case. This is a feasibility diagnostic before the
complete fixed admission suite, not a selected case replacing that suite.
Stop on a failed fixed numerical/counter/finite/primary/memory check. A pass
alone does not admit references or permit replacing live CPU acquisitions.

Use an independent source/binary/shader outside the default build. Bound each
runtime subprocess to 4 GiB address space, 21600 CPU seconds and 3600 elapsed
seconds, with at most 16 CPU fallback workers. This explicitly allows the
new CPU fallback work; it changes execution resource guards only. Build guards
remain 90 CPU / 300 elapsed seconds. Capture CPU fallback fraction and all
binary/source/shader/input/payload identities. No GPU competitiveness result,
power changes or historical N001–N009 revisions follow.
