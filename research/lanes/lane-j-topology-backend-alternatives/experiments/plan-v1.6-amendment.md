# Lane J plan v1.6 amendment — strict source-order fp32 exact intersection

Status: **frozen after shader watch diagnosis and before rerun evidence**

The watched-primitive replay localizes the retained correctness failure to the
exact triangle arithmetic / tie decision layer.

For step 3 / ray 3252:

- primitive 262389 reached its leaf;
- GPU triangle intersection accepted it;
- GPU `prefer_hit` accepted it;
- it replaced the prior current Hit;
- later primitive 262932 replaced it;
- CPU single-triangle t for 262389: 1533.32068;
- GPU watched t for 262389: 1533.32092;
- CPU/GPU t for 262932: approximately 1533.29016;
- CPU classifies the pair inside the frozen B001 tie window;
- the GPU t drift for primitive 262389 is enough to move the later comparison
  across that tie boundary.

This rejects traversal-state/AABB pruning as the active cause.

## Frozen correction

Do **not** change:

- B001 absolute/relative Hit tolerance;
- lower-primitive-ID tie rule;
- workload, rays, topology or cluster structure.

Instead make the GLSL exact triangle path follow strict source-order fp32
arithmetic:

1. replace GLSL built-in `dot` / `cross` in the Moller-Trumbore path with
   explicit scalar helpers;
2. mark intermediate values contributing to determinant, barycentrics and t as
   `precise`;
3. preserve the existing operation grouping used by the CPU reference;
4. keep normal normalization outside the tie decision;
5. keep the validation-only watched-primitive payload until the representative
   zero-error gate passes.

When targeting Vulkan, GLSL `precise` maps to SPIR-V `NoContraction`, which
prevents reassociation/FMA contraction for the contributing operations. This is
a reproducibility correction to the exact arithmetic, not a widening of the
correctness contract.

If this correction still fails, inspect generated SPIR-V NoContraction
decorations and CPU compiler contraction behavior before modifying any
correctness threshold.
