# Memory evidence scopes and qualified-reference quiescence watch

2026-10-15 JST; source checkpoint `af268f4`. N010 remains **NOT READY**.
No new Renderer build, GPU acquisition, calibration or unit test was performed
by the audits described here. Reference acquisitions 121/128 continue separately.

## Actual linked-source and retained-ledger audit

[132](132-comparison-owned-memory-boundary-audit.json) is retained **FAIL**.
It confirms both current Ninja link closures contain instrumented allocation
contexts, then refuses its first historical pilot because that pilot's binary
SHA differs from the currently frozen comparison executable. The strict
all-historical-rows-equal-current-binary assertion is false. No result is rewritten.

Post-hoc [133](133-current-and-historical-memory-evidence-audit.json) explicitly
audits distinct evidence scopes:

| Scope | Actual result |
| --- | --- |
| Current comparison link/dependency closure | Capture: 13 linked objects / 44 project dependencies, two allocation contexts. PT/dense RC: five objects / 21 project dependencies, one allocation context. All three direct allocation/free sites have paired ledger hooks. Legacy uninstrumented context objects remaining on disk are absent from the actual link recipes. |
| Retained comparison ledgers | All 76 executed pilot rows from 013/019/024/025/031/037 match their raw on-disk ledgers and replay to zero, with exact peaks under the original 8-GiB gate. One C12 software-churn unsupported row remains explicit. |
| Binary identities of those pilots | Eleven rows match the current PT binary; 65 retain different historical binary identities. They are not attested as current-binary runtime measurements. |
| Current-binary diagnostic boundaries | All 16 retained 035 diagnostic sizing boundaries match the current frozen capture/PT binaries and shader set. Their raw ledgers match the recorded ledgers and replay to zero. Largest observed owned Vulkan peak is 416,778,960 bytes. C6 HWRT includes nine device contexts; C12 HWRT includes five, aggregated through context/allocation identities. |

All 188 read identities remain unchanged after 133. The current linked objects,
dependency records, generated/owned source files, binaries, ledger payloads and
original result bytes are identified in that result. The audit ran Ninja's
read-only dependency inspection; it did not rebuild or relink either executable.
It is direct application call-site/dependency coverage, with explicit limits on
arbitrary dynamically loaded code, driver-private allocations and CPU heap scope.
It does not independently reproduce the binaries from source.

A further CPU-only Git ancestry check compares all 43 tracked project
dependencies/comparison generators with 035's recorded source commit
`d97826f6b73c19af87d158bec1ab8ea37b18ef78`: **all unchanged**. Exact commands,
per-file hashes and results are retained at
`out/research/n010-comparison-readiness/comparison-memory-boundary-audit-v2/source-ancestry.json`,
SHA256 `318924801ca076ea6ea4707a6c7c14db8c7a1b210521548816e571bdb9385fd7`.
New isolated reference/DDGI files are outside the audited comparison link closure.

035 remains loaded **diagnostic** sizing. Its memory evidence does not establish
accepted timing precision, a normal-workload peak for every future campaign,
or same-quality GI superiority. Quiet sizing 046, accepted calibration 029,
complete remaining pilots and final 047 remain required with original gates.
No scientific threshold or quality classification changed in either audit.

## Actual wait for complete selected references before scoped retirement

[Plan 038](../experiments/038-qualified-reference-quiescence-transition.md)
implements the redundant-work retirement allowed by plan 037. A separate
`retire_qualified_redundant_hybrid.py` watcher is actually running in
`out/research/n010-comparison-readiness/qualified-reference-quiescence-transition-v1/`.
Its initial live PID is 1370691; the owned process and start identity were
inspected. It freezes 3,218 existing proof/source/view identities and waits
for terminal complete/PASS 128. It then verifies all 24 actual selected reference
chains before signalling any process. Selected qualification failure stops
the watcher without retiring the hybrid acquisition.

After full proof, it may terminate only the verified redundant hybrid queue,
qualifier and native child. It preserves exact status bytes and all complete/
partial files, checks UID/command/work/PID/start/descendants, refuses unexpected
identities, and confirms termination. Natural prior hybrid completion is a
verified no-op. It never signals the point-guided acquisition or comparison
driver and never relabels interrupted 121 as complete or cap FAIL. Terminal
record 135 is pending; no retirement is claimed by this snapshot.

The watcher uses an `n010_` process name, so the comparison driver's existing
quiescence check also waits for its own completion. There is no wait on the
comparison driver from the watcher: the dependency is selected qualification
→ full provenance → redundant-work retirement → actual quiescence → original
comparison/calibration sequence. This avoids leaving unrelated unfinished
reference work as a permanent wait after selected references are ready.

## Current completion boundary

128 is executing its fresh C1 B8 8192 level; a completed individual seed is
not a qualified four-seed level. The existing complete 125/126 method proofs
do not establish corpus convergence. New comparison map 127, original four
seeds/six levels/screens/cap, and final six-gate preflight are unchanged.
Sponza direct max-relative-error-1.0 pixels remain **UNRESOLVED / 未解決** and
included. Keep all quality failures, historical outcomes, partial acquisitions
and unsupported roles. N010 remains the last preparation; no N011, power/clock
settings, CUDA, Actions or default architecture promotion.

Publication checks: eight configured indexes / 145 declared result links pass
`mise run research:check`; all 133 relative Markdown links in changed summaries
resolve. All 90/188 audit inputs and four active queue/driver/watcher frozen
maps (19/20/90/3218 inputs) were rechecked unchanged. `git diff --check` passes;
native source, default build definitions and Actions have no worktree changes.
These are scoped provenance/link checks, not runtime regression validation.
