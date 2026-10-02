# Lane N N001 scripts

`n001_contract.py` is the implementation truth for the N001 HDR exchange,
playback identity, radiometric comparison, timing/memory artifact schema, and
target-artifact validation.

`run_n001.py --phase contract` performs a GPU-independent serialization/metric
smoke and emits the frozen playback manifest. The synthetic gradient used by
this phase is not GI evidence.

`run_n001.py --phase validate-target --target-artifact <path>` validates a real
N001 target artifact after the image-producing Vulkan runtime exists.

`test_n001_contract.py` covers deterministic playback hashing, PFM orientation,
metric behavior, the contract smoke, and a complete synthetic target-artifact
validation path.
