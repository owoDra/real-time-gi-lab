# Lane N renderer source ownership

The image-producing Vulkan runtime will live here. N001 GPU-independent work
intentionally does not register an executable yet: the current `research`
checkpoint contains architecture decisions but not the concluded A/E/M lane
implementation trees, so accepted mechanisms must be ported deliberately with
source/blob provenance rather than by merging lane branches wholesale.

Do not substitute Integration #13's deterministic integer radiance control for
real direct + indirect diffuse rendering.
