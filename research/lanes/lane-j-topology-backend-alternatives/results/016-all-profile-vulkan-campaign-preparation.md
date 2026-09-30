# J003 all-profile persistent-Vulkan campaign checkpoint

Status: **READY — final GPU correctness/memory campaign pending**

Prerequisites now passed on the v1.6 exact-intersection implementation:

- representative persistent-Vulkan replay;
- large-global 256 -> 512 persistent resize path;
- exact-Hit zero-error gate across both;
- actual Vulkan old/new overlap accounting.

The final J003 GPU correctness/memory gate is one unchanged-build replay over
all five frozen profiles:

- small-global-high;
- medium-global-representative;
- medium-local-high;
- large-global-high;
- large-local-high.

Run:

```bash
mise run research:j003:persistent-gpu-all
```

The task builds `phos-lane-j-j003-persistent-gpu-replay` once, then reuses
that same executable and shader build for every profile with 4096 validation
rays per snapshot and Vulkan validation enabled.

Acceptance requires every profile to report:

- total_hit_mismatch_count = 0;
- total_traversal_runtime_error_count = 0.

Memory evidence must retain:

- persistent candidate allocation;
- dirty-upload logical bytes;
- staging allocation;
- resize old/new overlap where applicable;
- true peak resident bytes.

Diagnostic traversal timestamps remain non-ranking evidence.
