# N010 post-hoc inline CPU attribution with an unexecuted debug companion

Date:2026-10-17 JST. Parent:b7e3bde. Prospective build/analysis procedure;
interpretation of already acquired240 profiles is explicitly POST-HOC.
No new oracle/profile/GPU acquisition. Compile exact224 command/source with
only -g and output path changed. Never execute that debug binary. Before using
its line information require original/debug .text address AND bytes identical,
and all text symbol name/address identities equal. Otherwise stop, no mapping.
Preserve binary/source/hash identities and both compiled symbol listings.

Use perf annotate on each retained240 perf.data, executable-only, instruction
sample counts. Save raw annotation/stdout/stderr. Resolve every nonzero sample
address with debug companion addr2line -a -f -i -C. Record every inline frame.
Attribute a sample to slab, triangle intersection, ray setup, remaining BVH
traversal/closest/occlusion, or other functions by its inline frames. Save exact
address/count/category rows and category totals. Coverage denominator is240's
decoded IP samples, not only successfully attributed samples; retain unknowns.
Inlining/line tables, sampling noise/skid, startup and user-only scope remain
limitations. This locates sampled instruction time, not a complete cause or
scientific acceptance/speedup proof. No selective sample discard.

One low-priority CPU,4GiB. Compiler140CPU/180elapsed seconds; each offline
analysis30CPU/45elapsed. Each output<=32MiB,total<=128MiB. Save receipts and
returncode/CPU/elapsed before parsing. Any failure stops, preserving partials.
No changes to original224 binaries or240 inputs/payloads. No native retry,
power/display/app/settings changes, unit/regression tests, default-build or
threshold changes. Original physical11/17,eligible16/24,N010 NOT_READY.

Work:out/research/n010-comparison-readiness/cpu-profile-inline-attribution-v1
Result:results/241-posthoc-cpu-profile-inline-attribution.json
Driver:scripts/research/n010_reference_sampling/attribute_original_cpu_profile.py
