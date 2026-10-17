# N010 prospective original-iid constructor repair for bounded furnace

Date:2026-10-17 JST. Parent:5996a93. Before new compile/acquisition.
219 preserves a compile failure: the original Xoshiro256 API requires
(seed,pixel,index), while076's driver incorrectly supplied seed alone. No
native control ran and no physical PASS/FAIL is inferred. Retain219 payloads.

New220/work `all-split-furnace-control-v2` uses the unchanged218 header and
identical076 scene/pixels/seeds/net8192/iid16384, bounds and all acceptance
rules. Only fix invocation to original API: priming at(seed,pixel,0), iid RNG
constructed inside the n loop at(seed,pixel,n), exactly the original N008
per-pixel/per-index stream boundary. Dark prime uses(seed,pixel,0). This
corrects a non-compiling driver; no scored data selected this repair.
Hash219's failed source/partials and original076 driver/plan. One compile/
native, same one CPU nice15,4GiB/220CPU/300elapsed, no retry or concurrent
worker/GPU. All076 scope limitations and remaining full physical/state/prefix/
feasibility/admission gates remain. No thresholds/settings/history changes.
Unit/regression tests NOT RUN; independent bounded scientific control only.
