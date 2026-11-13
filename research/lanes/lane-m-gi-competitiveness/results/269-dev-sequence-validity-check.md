# 269 — Development sequence validity check (correction to 267; not evidence)

2026-11-13. Independent CPU-only check of the 049/049a development data that
[267](267-rtcvs-development-summary.md) summarises. No GPU run, no new image,
no gate decision. It reads the generated sequence states and the existing
4×16384 spp development references and asks one question per sequence: does
the reference image actually change over the sequence?

Scripts (added with this record):
`scripts/research/lane_m_gi_competitiveness/dev_sequence_change_check.py`
(reference change against frame 0 and reference noise from seed halves) and
`dev_sequence_state_check.py` (what differs between the first and last state).
The raw sweep logs that 267 cites are now committed under
[rtcv-dev-logs/](rtcv-dev-logs/) (24 files, copied byte-for-byte from
`out/research/lane-m-gi-competitiveness/rtcv-dev-logs/`).

## Findings

Reference noise floor: indirect NRMSE between two independent 2-seed halves is
0.5–0.9%, so two references of an unchanged image differ by about 1%
(`L-S1-static`: 0.96–1.00% against frame 0).

| Sequence | Label in 267 | Indirect change vs frame 0 | Verdict |
|---|---|---:|---|
|`D-SP-light` (Sponza)|light motion|0.65% (= noise)|**static**: all 192 frame-state and geometry-state files are byte-identical|
|`L-S2-rigid`, `L-S2-deform`|rigid / deform|1.0–1.1%|**effectively static**|
|`L-H02-rigid`, `L-H02-deform`|rigid / deform|1.0%|**effectively static**|
|`L-S4-rigid`, `L-S4-deform`|rigid / deform|1.2–2.2%|**effectively static**|
|`D-SP-rigid` (Sponza)|rigid|2.3–3.2% (total 3.7–6.2%)|real, mild|
|`L-S1-rigid`|rigid|55–65%|real|
|`L-S1-deform`|deform|1–11% (periodic)|real|
|`L-H03-rigid`, `L-H03-deform`|rigid / deform|16–95%|real|
|`L-*-light` (small scenes)|light|16–91%|real|
|`L-*-camera`|camera|43–178%|real|

Causes:

- `D-SP-light`: the development Sponza point light sits exactly at the scene
  bounding-box centre (−60.52, 651.49, −38.69). `rtcv_sequences.frame` orbits
  the light around that centre, so the orbit is the identity.
- `L-S2/H02/S4-rigid|deform`: `moving_instance` picks the second-largest
  instance with a stable sort, which is instance 0 (36 triangles). It moves
  (up to 0.95–1.02 units) but has no visible effect on the image from the
  fixed camera. `L-S1-rigid` used an explicitly chosen instance (2), which is
  why it alone shows strong geometric change among the small rigid sequences.

## Consequence for 267

- "D-SP-light: RTCVS k1 6.9 ms vs PTA k4 14.7 ms" is a **static-scene** result.
- "S2/H02/S4 rigid+deform" rows are **static-scene** results.
- With visible geometric motion the candidate passes only `D-SP-rigid` (mild
  change, 11.5 ms vs PTA ≈21 ms) and fails `L-S1-rigid` and
  `L-H03-rigid/deform`. Its verified strengths are static images, small-scene
  light motion and mild Sponza rigid motion.
- The Sponza PTA ladder in sweep14/16 has four configurations only; "best PTA"
  means the cheapest of those four.

267 is not edited. This record does not change any registered outcome; it
narrows what the development picture supports. A sequence generator must
assert that the reference changes by more than the reference noise before a
sequence is labelled dynamic.
