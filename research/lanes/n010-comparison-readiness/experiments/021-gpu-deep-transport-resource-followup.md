# Deep-transport bounded resource follow-up

Prospective after 075 is terminal. C1 T_B2/C7 T_B2/C7 T_B8 pass all four
seeds (twelve completed cases). First C1 T_B8 seed exceeds 900 seconds and
produces no f64/component result. 075 remains failed; no numerical or cap
failure is inferred for an unfinished calculation. GPU reference admission
is still withheld. CPU reference qualification continues independently.

Run the remaining four fixed C1 T_B8 cases with an explicit 1800-second
wall guard, unchanged 4 GiB memory/90 CPU-second guard, host binary, shader,
batch 16, original 8192 samples/seeds/scenes and all numerical thresholds.
Retain the ordered twelve completed cases from 075, preserving result and
payload hashes and independently rechecking original CPU reference provenance.
There is no choice between values or quality-based selection. Never reuse
the unfinished thirteenth case or overwrite its empty/partial attempt.
Retain every new attempt and stop at first failure. This changes only an
execution resource guard, not convergence/correctness/quality acceptance.

New full-case diagnostic is 082. For plans 019/020, replace the required
full-case evidence dependency 075 with complete/PASS 082; retain failed 075
and the no-dispatch record 081 for the old conditional workers. Every
physical-control/all-state/nested-prefix condition is otherwise unchanged.
Use fresh control/prefix work directories for their conditional execution.
These controls still need runtime proof. No qualified reference, accepted
GPU timing, default Renderer behavior or historical result is changed.
