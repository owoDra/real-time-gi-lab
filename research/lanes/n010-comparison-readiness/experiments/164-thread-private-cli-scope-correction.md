# Thread-private exporter CLI scope correction

2026-10-19 JST. Prospective correction before any162 compilation or163 native.
Source review found621's unchanged full and prefix CLI files still reject
threads!=1, although their private headers allow1..4. Thus621 alone cannot
execute the proposed four-thread pilot. This is a source defect, not an
observed native failure or scientific result. Preserve621 and unrun622.

`prepare_thread_private_cli.py --prepare` creates fresh626/source-v2 by
verifying all621 input/payload identities, copying both exact private headers,
and changing only the two CLI scope predicates from threads!=1 to
(threads<1||threads>4), with corresponding diagnostic wording. Prove whole
CLI inverses and retain each exact edit. No sampling, scene restriction,
floating arithmetic, audit, random stream, threshold or resource change.
Compiler/flags remain621's exact commands except source/output paths.
Preparation120CPU/180elapsed/2GiB, CPU31/nice15/BLAS1; no native/compiler.

`--build` creates627 using the unchanged162 isolated serial-build function,
bound to626 and fresh build-v2 paths. Retain original per-compiler220CPU/
300elapsed/4GiB, exact compiler, owned process/resource/partial receipts and
quiescence requirement. No retry/queue or scientific acquisition.622 remains
NOT RUN and is superseded for prospective163 by626/627, not rewritten.

163 now uses original452 as baseline and626/627 as candidate. Its same-CPU31
four-thread pilot, all original binary/audit/primary/deterministic/numerical
conditions and623–625 outputs remain. Actual490 must first be terminal.
Further full physical/state/prefix and approved-load feasibility qualification
remain required before reference use; no automatic transfer of13/17 evidence.
N010 NOT_READY, refs16/24, direct-relative1.0 UNRESOLVED/未解決, no speed claim.
Tests NOT RUN. No settings/default-build/N001–N009/Actions changes.
