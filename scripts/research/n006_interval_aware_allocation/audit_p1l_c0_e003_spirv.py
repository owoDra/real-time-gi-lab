#!/usr/bin/env python3
"""N006 P1l-C0: E003 secondary wide-node SPIR-V source/compiler audit.

Static compiler data only; no physical GPU timing or workload profiling.
B0 GPU work-counts live in accepted result 021, not in this audit.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from audit_p1l_b1c_spirv import ROOT, compiler_info, parse_spirv

PROTOCOL = "n006-p1l-c0-e003-spirv-static-audit-v1"
VARIANTS = {
    "accepted_e003_rebuilt": (
        "shaders/research/lane_n_end_to_end_renderer/imported/lane_e_dynamic_geometry/e003_instance_quantized.comp.glsl",
        "n006_p1l_c0_e003_source_rebuild.spv",
    ),
    "b0_count_only": (
        "shaders/research/n006_interval_aware_allocation/n006_p1l_e003_count.comp.glsl",
        "n006_p1l_e003_count.spv",
    ),
}
FAMILY = {
    61: "OpLoad", 62: "OpStore", 65: "OpAccessChain",
    129: "OpFAdd", 131: "OpFSub", 133: "OpFMul", 136: "OpFDiv",
    148: "OpDot", 246: "OpLoopMerge", 247: "OpSelectionMerge",
    249: "OpBranch", 250: "OpBranchConditional",
}

def source_contract(s: str) -> dict:
    # A source-level structural check, NOT a proof of executed operations.
    return {
        "eight_child_iteration": bool(re.search(
            r"ordinal\s*<\s*8u", s)),
        "child_decode": "decode_child(" in s,
        "child_aabb": "ray_aabb_bounds(" in s,
        "direction_axis_sort": "direction[int(axis)] >= 0.0" in s,
        "per_axis_division_source": "float a = (mn - o) / d;" in s
                                    and "float b = (mx - o) / d;" in s,
        "stack_entry_pruning": "token_enter >" in s,
        "invalid_child_skip": "child_token == INVALID_ID" in s,
    }

def audit(build_dir: Path) -> dict:
    doc = {
        "protocol_version": PROTOCOL,
        "kind": "STATIC_SPIRV_AUDIT_ONLY",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "toolchain": compiler_info(build_dir / "CMakeCache.txt"),
        "unmeasured": ["dynamic_GPU_instruction_counts", "GPU_registers",
                       "GPU_occupancy", "SIMT_divergence", "GPU_cache_misses",
                       "SSBO_transactions", "secondary_GPU_time",
                       "CPU_refit_and_rebuild_cost"],
        "variants": {},
        "conclusion": "STATIC_COUNTS_ONLY_COMPILER_HOISTING_NOT_ESTABLISHED",
        "active_shader_binary_match_required": True,
    }
    for name, (source, spv) in VARIANTS.items():
        raw = (build_dir / "shaders" / spv).read_bytes()
        src = (ROOT / source).read_bytes()
        blob = parse_spirv(raw)
        counts = blob["opcode_counts"]
        doc["variants"][name] = {
            "source": source, "source_sha256": hashlib.sha256(src).hexdigest(),
            "spv_file": spv, **blob,
            "opcode_families": {v: counts.get(str(k), 0) for k, v in FAMILY.items()},
            "source_contract": source_contract(src.decode("utf-8")),
        }
    baseline = doc["variants"]["accepted_e003_rebuilt"]
    # CMake currently does NOT register generation of the runtime's
    # e003_instance_quantized.spv. Recompile *separately*, then verify it
    # against the artifact actually loaded by the accepted runtime.
    active_path = build_dir / "shaders" / "e003_instance_quantized.spv"
    if not active_path.is_file():
        raise RuntimeError(
            "C0 active E003 SPIR-V absent: baseline runtime artifact provenance missing")
    actual = parse_spirv(active_path.read_bytes())
    doc["runtime_e003_binary"] = {
        "file": "e003_instance_quantized.spv",
        "sha256": actual["sha256"],
        "binary_bytes": actual["binary_bytes"],
        "matches_fresh_source_rebuild": actual["sha256"] == baseline["sha256"],
    }
    if actual["sha256"] != baseline["sha256"]:
        raise ValueError(
            "C0 active E003 SPIR-V differs from freshly rebuilt shader; "
            "do not interpret static audit until provenance reconciled")
    if not all(baseline["source_contract"].values()):
        raise ValueError("C0 accepted E003 shader source contract changed")
    # Static OpFDiv count is intentionally NOT interpreted as how many
    # divisions are executed per ray or whether compiler hoisted loop invariants.
    counted = doc["variants"]["b0_count_only"]
    doc["difference_vs_count_instrumentation"] = {
        "binary_bytes": counted["binary_bytes"] - baseline["binary_bytes"],
        "static_instructions": counted["instruction_count"] - baseline["instruction_count"],
        "static_division_opcodes": (
            counted["opcode_families"]["OpFDiv"] -
            baseline["opcode_families"]["OpFDiv"]),
    }
    return doc

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path,
                        default=ROOT / os.environ.get("PHOS_GI_BUILD_DIR", "build/release"))
    parser.add_argument("--out", type=Path,
                        default=ROOT / "out/research/n006-interval-aware-allocation/p1l-c0-e003-static-audit.json")
    args = parser.parse_args()
    if not (args.build_dir / "CMakeCache.txt").is_file():
        raise RuntimeError("C0 missing configured CMake build; run mise run build first")
    result = audit(args.build_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"status": "static-only", "report": str(args.out),
                      "variants": {k: {"bytes": v["binary_bytes"],
                                       "OpFDiv": v["opcode_families"]["OpFDiv"]}
                                   for k, v in result["variants"].items()}},
                     indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"N006 E003 C0 static audit failed: {error}", file=sys.stderr)
        raise SystemExit(1)
