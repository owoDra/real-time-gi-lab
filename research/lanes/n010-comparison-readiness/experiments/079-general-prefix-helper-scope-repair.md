# N010 prospective helper-scope repair before generic equivalence

Date:2026-10-17 JST. Parent:acb288e. Before new compile/native.
222 retains a compile failure: generated prefix helper was inserted before
the previous function's closing brace. No native ran; no equivalence or
physical result. Preserve222 sources/compiler log and exact bytes.

Move that closing brace before the helper, removing its old position after
the helper. Prove these are the ONLY two inclusion edits. No arithmetic,
sampler, material, sidedness, prefix, geometry or threshold change. New223,
work `all-split-general-transport-v2`, uses all078 scopes/resources/controls:
one compiler/native, C1 fixed8pixels/8192/fourseeds, per-sample legacy bits
and retained218 accumulated bits exact. One CPU nice15,4GiB/220CPU/300elapsed,
no retry/concurrent worker/GPU. Original17 physical controls still required;
no new output admission. Keep all original failure/statistical records.
Unit/regression tests NOT RUN; isolated scientific equivalence only.
