# N010 operand witness: correct the source selector before compilation

2026-10-18 JST. Parentd54eee33. Preserve failed437 exactly.137's prepare
stopped before writing any generated payload or launching a compiler:
`nonunique diagnostic source anchor`. Its selector `// Plan078:` matched an
earlier struct comment, so the selected region included both legacy and
current strategy loops (two anchors). Read-only source inspection verifies
that the full marker `// Plan078: same proposal, ordered-prefix reuse and
general physical target.` selects exactly the current function and one
strategy anchor. This is a source-generation bug, not another numerical run.

Register v2 driver now: the source-selector correction, separate v2 paths
and this plan identity are the only preparation-method changes. Preserve
the exact old137 driver and failed437 record. The corrected driver pins
that failure and its old source, and still requires whole-header and caller
inverse equality. All137's permitted operand-only edits, exact sample3265,
original435 witness agreement, original1e-6 threshold, CPU31/nice15/
120CPU/180elapsed/4GiB, per-stage review, no retry/queue/GPU/admission
and unchanged physics remain. No extra BVH calls or arithmetic changes.

Manually invoke v2 `--stage prepare`442, review terminal source proof,
then separately `--stage build`443 and review, then separately `--stage
probe`444. No stage launches another.445 is137's post-hoc CPU arithmetic
on the retained operands;446 records outcome/current docs. Old438–441
were not executed. Keep all old failure/provenance and no automatic retry.
No unit/regression/default-build/GPU smoke tests or system/app changes.
