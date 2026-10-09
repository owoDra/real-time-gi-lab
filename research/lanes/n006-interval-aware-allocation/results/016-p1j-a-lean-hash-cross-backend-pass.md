# N006 P1j-A — lean hash cross-backend parity and scratch reduction PASS

Issue #42. Source: user-uploaded `n006-p1j-lean-hash-summary.json`, `n006-p1j-lean-hash-v1`, AMD Radeon 8060S (RADV STRIX_HALO), clean HEAD `946921f74ebe53dad31193de270a5d2b19d1811f`. Non-formal; frozen 5 Lane-E-final scenarios × HWRT / software = **10 cases**. Report status `complete`, `all_cases_byte_identical=true`, `failures=[]`, `cases_complete=10`; no independent reference rendered.

## Results and what is actually demonstrated

| Item | Prior P1g/P1i canonical | P1j-A lean |
| --- | ---: | ---: |
| GPU hash slots | 524,288 | **32,768** |
| Hash keys + owner-count arrays | 4,194,304 B | **262,144 B** |
| Total N006 reported scratch (including compact work) | 8,421,464 B | **4,489,304 B** |
| Scratch difference | — | **−3,932,160 B (−46.6921%)** |
| Original/canonical images | byte-identical | **10/10 byte-identical** |
| Actual ray-count reduction | 80.97–81.95% | **80.97–81.95% retained** |

Each of the ten source-vs-lean-canonical pairs passed the strict prior P1i gates: same HDR PFM SHA by scenario, original owner count reweighted exactly, canonical output count 3,008–3,220 and ray count 24,064–25,760, zero GPU key-insert/invalid-key/storage/hit failures. No capacity overflow despite the smaller hash. Original and canonical paths remained separated by opt-in `--canonical-lean-hash`.

- **Observed total hash collision steps per canonical target:** HWRT 576/549/503/590/591 and Software 564/538/540/596/671 across the frozen scenario order. These are aggregate probe steps across ~16–17k owner/cascade outputs, not per-operation maximum probe length. Do not confuse aggregate with the 128-probe per-insertion bound.
- **Canonical build-stage GPU timing (descriptive, nonpaired):** HWRT 53.46/53.62/50.18/52.30/55.55 µs; Software 54.94/56.59/55.14/50.38/54.70 µs. All values are from cold, single target frames, so don't claim statistically proven faster hashing than P1i's original table.
- Storage owner-weight GPU stage remained integrated into `storage_update`, approximately 5–6 µs, preserved without compromising bitwise output.
- **Scratch measurement scope:** 4,489,304 B is N006 allocation byte accounting, not an independently measured Vulkan driver resident heap, and not a full renderer memory peak (including baseline, backend acceleration structures or allocation fragmentation).

## Decision and follow-up

**P1j-A PASS (10/10 correctness and bounded memory accounting), GO to P1j-B separately opt-in.** Next study should eliminate `compact_work → original work` GPU copyback and its compute/barrier overhead, by binding the accepted ray/radiance/storage/resolve stages directly to the compact work stream and adjusting readback validation. Preserve the old copyback path for regression. Important: eliminating a GPU copy dispatch does **not automatically free** the ~4 MiB compact staging buffer, because the legacy owner producer still emits full original work. P1j-B should measure this honestly, not claim reduced scratch until direct canonical producer replaces the owner-local work stream in a future separately frozen phase.

Freeze P1j-B before implementation or measurements and require both HWRT/software 10-case image parity plus controlled matched-state net-GI timing under both backends. No old accepted result rewrites, N004/N005 semantic changes or GH Actions.
