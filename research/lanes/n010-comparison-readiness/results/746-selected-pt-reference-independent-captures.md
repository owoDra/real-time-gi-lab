# Selected PT captures not needing missing references (746)

2026-10-20 JST. Plan132 adapter over130 runner, unchanged committed drivers; one
native per invocation, next only after the previous terminal record; CPU31/nice15,
Radeon 8060S RADV. Records: [continuation-quality-cases/](continuation-quality-cases/).

- **18 cases VALID_SINGLE_CASE_QUALITY_RESULTS_RETAINED**: static C1-B2, C7-B2,
  C8-B2/B8, C9-B2/B8; dynamic C2-B2, C3-B2, C8–C12 × B2/B8 (all n1024). Every frame
  meets the pilot quality targets (PASS); owned Vulkan true peak3.29MB (non-Sponza)
  /107.4MB (Sponza), zero teardown, ≤8GiB cap. Timing is valid-but-uncalibrated
  (accepted_timing=false), i.e. TIMING_INCONCLUSIVE under120/147.
- **dynamic-C4-B2-n1024: native returncode0, record `NATIVE_TERMINAL_PROOF_PENDING`.**
  The python proof stage was killed by the runner's own RLIMIT_CPU120s while
  hash-verifying the hybrid C4_T_B2 reference (frame0 scoring had started); no
  failure string was recorded. Capture bytes retained; no rerun. A separate CPU-only
  proof replay on the retained bytes is registered in175.
- Selected PT scope now20/28 valid (with402/403); remaining C4-B2 proof and the
  seven slots awaiting R1 references (dynamic C2/C3/C4-B8, C5/C6-B2/B8).
- An R1 reference acquisition started in `r1-reference-ladders-v1` was stopped by me
  after ~2min (its C5_T_B2 8192 native had only written `n8192.attempt.json`), because
  `quiet()` forbids GPU captures while an `n010_` worker runs. Retained, not reused;
  acquisition restarts in a fresh root `r1-reference-ladders-v2`. Tests NOT RUN.
