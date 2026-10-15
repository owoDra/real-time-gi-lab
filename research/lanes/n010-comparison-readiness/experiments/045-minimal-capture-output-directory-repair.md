# Minimal calibration fixture: output-directory build repair

Date: 2026-10-15 JST. Parent checkpoint: `44922b2`.
Registered before the corrected fixture build or any plan-044 GPU acquisition.

CPU source review after build 156 found that pixel PT's old per-frame state
copy also created its frame directory. Suppressing that copy without creating
the directory would make the retained scratch/image writes fail. This is a
source-identified implementation defect, **not an observed GPU/runtime failure**.
Build 156 remains an actual compilation/source-inverse PASS, without runtime
validation. Preserve its exact bytes, binaries and scope; do not promote it.

Build 159 uses an explicitly guarded copy of the frozen 156 builder, adding
only `fs::create_directories(frame_out)` in the calibration branch where the
state-file copy was suppressed. Its inverse overlay still reproduces the
original active sources exactly. Use a fresh `minimal-calibration-build-v2`
root; overwrite no old object, binary or result. Preserve the same dependency
identities, serial compiler/link commands, resource guards and unchanged-active-
input checks. Any failure stops with outputs retained, without automatic retry.

All plan-044 GPU work remains unexecuted. Its prepared wrapper must require
complete build 159 and use v2 binaries before fresh sizing 157 / calibration
158. The original sixteen boundaries, full image-producing GPU work, exact
046 image comparison, scratch witnesses, memory replay, sample schedule and
all seven timing gates remain unchanged. No native rerun of 156 is needed.

This repairs filesystem output plumbing, not GI behavior or measurement
statistics. It admits no reference or calibrated timing and leaves every final
N010 gate intact. No GPU acquisition overlaps the running CPU proposal work.
