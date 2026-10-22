# M001 H02 independent state audit and H03 first-capture handoff

Date: 2026-10-22 JST. Branch `research-lane-m-gi-competitiveness`. Current user-supplied evidence: original private H01 state tar, H02 receipt/diagnostic files, follow-up H02 six-file tar; no raw full HDR images transferred.

## Independent CPU H02 integrity results

[Result 007](results/007-h02-independent-state-audit.json) is a retained *metadata/state* audit. 214/214 scoped checks PASS, including every ledger event (the check count is not a statistical sample), byte-identical ordered 1224/1224 glTF triangles vs captured GPU `geometry-state.bin`, 1224 valid nondegenerate/two-sided triangles, finite 320×180 camera/UBO, expected static/hwrt/ulp4 source and zero overflows, and exact H01/H02 SHA chain. H02 geometry SHA `9d7c434202d2c9d14a7b3c4fb024b13cbd5240fc5251c22d3b533f719f968b5c`, frame SHA `70745baa8ebeabe9ffe20a8ba284261bfc7ea060eda1d318bc2ad338f1b8e7e4`. Owned Vulkan allocation replay: 74 events, independently computed true peak 266,937,920 bytes (254.57 MiB) with teardown-zero; 8 GiB cap satisfied.

Only **4/13 H02 raw capture payloads** were transferred and hash-verified; remaining 9 (HDR images, probes, timings) remain at owner's host. The other 9 are **UNVERIFIED**, not admitted. H01 retains identical 4/13 caveat from result 003. Both original GPU native calls reported returncode 0. Legacy N007 CPU physical audit NOT RUN. No new GPU execution occurred during this H02 audit.

## N008 finite-depth physical input hashes (not oracle references)

On CPU, reconstructed N008 `read_state/state_scene` construction and independently verified it reproduces the *previously frozen H01 T_B2/T_B8 hashes*. The same construction on H02 gave exact prospective source hashes:

- H02 canonical geometry f64/material SHA `b40574ad76dbcc8f80250a0b1a1be0313176983b7140e96fdee18f4970ecb6e7`
- `T_B2`: full `.n008` scene SHA `0db4c7d6616bf14edd0e5f2378bf9f4e7f95353a6c4b9ee7f2eba2df64ae0bed` (143,266 bytes)
- `T_B8`: full `.n008` scene SHA `c572d6f55726aa8898e23f5e03e8ddcc9b9696c64e012102bc48cb74f1416b31` (143,266 bytes)

The fail-closed `prepare_h02_reference_scene.py` reconstructs these from the exact **host** N008 canonical module and refuses any changed byte/geometry SHA. This freezes source inputs only: **neither transport has an eligible, independently converged HDR reference**. The original four replicate seeds, two consecutive levels and finite physical/support tests remain required before scoring any pixels.

## Next GPU boundary: H03 static state only

`scripts/research/lane_m_gi_competitiveness/capture_h03.py` is the next **single named GPU** action. Before native dispatch it independently rechecks **all 13 raw H01 payload SHA hashes and all 13 raw H02 payload SHA hashes locally on owner machine** with existing standalone audit code. Original H02 receipt must equal SHA `5562656fad898b07ac91903affd7d0f00423b1813f2a59dc67941fc22e23f765`; H03 pre-registered geometry `enclosed` thickness 0.127, 1248 triangles, glTF SHA `23b1a96560c405dfc645f8de51afef4fb4cbdca4e06d75ee32097bde034c9424` and BIN SHA `bab24715916c2a62a02f55aab4a9d0c1f43ca860600cb0529ca70e8b41d643f4`. It refuses existing output or tar, changed manifest, missing assets, active research workers, less than 8GiB disk, and different branch.

Successful capture produces native results under the existing local `out/research/lane-m-gi-competitiveness/m001-first-heldout-v1` without editing earlier captures, then **automatically creates `out/m001-h03-state.tar` at repository root** containing 10 small capture state/receipt/asset inputs. No HDR PFM images included. It prints its own compact receipt. On failure it leaves all partial evidence/diagnostic logs and must not be retried/overwritten without review. No H03 reference qualifier, scoring, historical edits, timing, DDGI, GPU queue, Actions or clock/power changes.

H03 status before owner execution: **NOT RUN**. Lane M first cohort remains `STATE_INPUTS_INTEGRITY_ONLY_REFERENCES_INELIGIBLE`, full GPU quality comparison NOT RUN, accepted speed advantage NOT ESTABLISHED. Do not infer broader Sponza/dynamic scene generalization.
