# Streamed-hybrid all-state and exact-prefix validation

Build a separate prefix-capable host from the unchanged 095 source/kernel.
Use the same parser, independent CPU transport, ambiguity guard, component
order, GPU per-path values and CPU fallback. Add only restoration of complete
previous binary64 means/moments and per-pixel integer counters. Validate the
frame/seed/SPP headers, exact lengths, finite values and dyadic levels.
Require each restored mean/moment times previous SPP to reproduce its saved
raw sum bits exactly; reject incompatible or lossy prefixes.

Only after complete numerical 098 and physical 099 pass, execute every locked
state/transport (24) and all four original seeds. Compare fresh 16-spp hybrid
outputs with original CPU controls 078 using all unchanged Amendment 7 gates.
For each case run prefix-host fresh 8 then 8→16 and require every output
component/moment/primary payload and exact counters to equal fresh 16 byte
exactly. Every full-frame pixel remains scored. Compare actual canonical
geometry and memory ledgers on each run; no selected scene omissions.

Also execute C7 T_B2 and T_B8, all four seeds, fresh 16384 against 8192→16384
restored from the identical 095 build's completed 098 case. Require exact
payload/counter equality and complete prefix/input provenance. The original
port's earlier passing files are not used as hybrid prefixes.

Use plan 025 resource limits, batches <=16 and 16 CPU workers. Stop on the
first failure, retain it, and perform no automatic retry within this suite.
Build alone, a partial state set, or numerical/physical proof alone cannot
admit references. Keep original CPU qualifiers and frozen waiting driver;
any scheduling transition needs its own completed-boundary provenance record.
No CUDA, power changes, default Renderer adoption, or N011.
