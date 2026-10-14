# N010 GPU numerical-port resource-budget follow-up

Prospective follow-up after result 074. Its four C7 T_B2 fixed seeds pass at
8192 spp. The first C1 T_B2 seed exceeds the 120-second process guard, leaving
no reference payload or numerical comparison. 074 remains a failed diagnostic.
The adapter remains ineligible. No numerical disagreement is inferred from
an unfinished calculation.

Run the same frozen sixteen Amendment 7 cases in a new work directory with
an explicit 900-second wall guard per process, unchanged 4 GiB address-space
and 90-second CPU guards. Retain every attempt. Batch remains 16; shader,
host binary, samples, seeds, scenes and numerical gates are unchanged. This
extends an execution resource guard, not a reference acceptance threshold.
Retain the existing first C7 seed without rerunning it; the other full cases
are independently acquired under the new recorded guard. Stop at the first
runtime or numerical failure. No accepted GI timings or qualified reference
acquisitions are retried. Full physical/all-state/prefix gates still apply
before any reference admission or scheduling change.
