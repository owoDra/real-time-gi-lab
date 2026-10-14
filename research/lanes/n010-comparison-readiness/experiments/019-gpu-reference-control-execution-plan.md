# GPU reference physical-control execution plan

Prospective detailed execution of Amendment 7's physical admission gates.
Require complete/PASS result 075 first. This is an adapter diagnostic, not a
qualified reference or GI comparison. Every failed/partial attempt is retained.

Use all 17 original point-light scenes from sampler-validation-v1/rqmc,
whose exact metadata, scene and four-seed component/f64 bytes are attested
by completed CPU equivalence 022. Keep their original counts (64, 256, 1024
or 8192), original four seeds and fixed independent physical expectations.
No scene/emission/box-camera capability is invented for the point-only adapter.

Run every scene/seed on the unchanged base host binary and SPIR-V with batch
16 and process guards 4 GiB address space, 90 CPU seconds, 900 wall seconds.
Require finite all-component mean/moments; identical primary records, direct
and emission means; exact geometry hashes and integer counters; no fault
flags; original mean/moment max absolute discrepancy <=1e-10 and indirect
NRMSE <=1e-8 over all pixels, without exclusions; complete owned memory
ledger replay to zero. Zero CPU indirect support requires exact zero GPU
indirect support. Stop at the first runtime or numerical failure.

After all 68 acquisitions pass, rerun the unchanged independent analytic/
geometric/support checks using those GPU replicate means in place of the
CPU means: A2/A2b lit/occluded point-light cases; A4 sidedness/back-facing
occluder; A8 frozen rigid/posed geometry; sealed dark/lit rooms; finite-depth
rho-grey and coloured furnace A6; scaled A10; quadrature A7. Their declared
geometric analytic masks/allowances are unchanged; whole-frame numerical
conformance additionally scores every pixel. Preserve these two distinct
checks and all outcomes. All-state and nested-prefix admission gates remain
required separately. The new prefix host executable's build 076 proves
neither numerical equivalence nor determinism by itself.
