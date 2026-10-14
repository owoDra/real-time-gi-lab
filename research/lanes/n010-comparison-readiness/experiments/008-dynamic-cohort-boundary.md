# N010 dynamic cohort execution boundary

Before the first dynamic PT/dense-RC capture, freeze a source frame, first
changed frame and three following recovery frames. No warmup or changed-frame
exclusion. Same source/target snapshots are the locked corpus. Preserve every
frame image, state bytes, seed, error map and allocation event.

Native PT and dense RC use a conventional single-BLAS/TLAS implementation.
Compare full GPU triangle records to determine changed slots; upload their
vertices/metadata and UPDATE the full BLAS plus TLAS. Camera/light transitions
upload the full uniform. Geometry UPDATE, TLAS UPDATE, each GPU upload and
the complete image-producing dispatch are included in each changed-frame GPU
sample; CPU diff/preparation/submit/wait wall costs are reported separately.
All preparation of the target snapshot is outside the rendering campaign;
the actual per-frame diff, upload and AS maintenance remain inside it.

The frozen churn changes primitive identities/geometry with constant triangle
slot count; Vulkan single-BLAS UPDATE supports that fixed-slot operation.
This baseline therefore does not need the incumbent's replacement object-local
BLAS for this particular regime. Record this semantic/update-method difference
explicitly; do not imply arbitrary count-changing topology is supported.
Reject changed resolution or primitive slot count. Allocation lifetimes include
all actual staging and AS scratch, with startup/readback separated and zero
teardown. Incumbent replacement overlap remains measured by its own ledger.

Pilot sequences use PT 256 spp for T_B2 /1024 for T_B8, dense RC's fixed 4×8
budget. These are pilot settings, not universally quality-matched settings;
any failing cell remains FAIL. All GPU timing remains diagnostic until the
fixed complete Renderer calibration passes. Per-frame diagnostic readback
lies outside both the image GPU timestamps and the reported frame CPU wall.
