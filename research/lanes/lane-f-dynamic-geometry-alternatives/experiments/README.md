# Lane F experiment records

Issue #16 is the frozen protocol and decision-gate source of truth.

Concluded experiments are recorded under `../results/` as
`NNN-short-name.md`. Raw artifacts stay under `out/research/`.

F002's committed structural/tuning freeze is
`002-transient-lbvh-builder-config.json`. The target artifact copies that
file to `f002-config.json`; accepted timing must not change those parameters
after the first target run.
