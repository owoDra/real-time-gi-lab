#!/usr/bin/env python3
"""N006 B1c reproducible *static* SPIR-V audit; NOT GPU execution profiling."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[3]
VARIANTS = {
    "accepted_original": (
        "shaders/research/lane_n_end_to_end_renderer/n003_primary_software.comp.glsl",
        "n003_primary_software.spv"),
    "rejected_b1a": (
        "shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl",
        "n006_p1l_b1_primary_near_first.spv"),
    "candidate_b1c": (
        "shaders/research/n006_interval_aware_allocation/n006_p1l_b1c_primary_axis_proxy.comp.glsl",
        "n006_p1l_b1c_primary_axis_proxy.spv"),
}
FAMILIES = {
    61: "OpLoad", 62: "OpStore", 65: "OpAccessChain", 66: "OpInBoundsAccessChain",
    71: "OpDecorate", 129: "OpFAdd", 131: "OpFSub", 133: "OpFMul",
    136: "OpFDiv", 148: "OpDot", 249: "OpBranch",
    250: "OpBranchConditional", 247: "OpSelectionMerge",
    253: "OpReturn", 254: "OpReturnValue",
}

def parse_spirv(data: bytes) -> dict:
    if len(data) < 20 or len(data) % 4:
        raise ValueError("invalid SPIR-V size")
    words = struct.unpack("<" + "I" * (len(data) // 4), data)
    if words[0] != 0x07230203 or words[4] != 0:
        raise ValueError("invalid SPIR-V header")
    instructions: Counter[int] = Counter()
    i = 5
    while i < len(words):
        word_count = words[i] >> 16
        opcode = words[i] & 0xFFFF
        if word_count == 0 or i + word_count > len(words):
            raise ValueError("invalid SPIR-V instruction word count")
        instructions[opcode] += 1
        i += word_count
    if i != len(words):
        raise ValueError("trailing SPIR-V words")
    return {
        "binary_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "spirv_version_hex": f"0x{words[1]:08x}",
        "instruction_count": sum(instructions.values()),
        "instruction_words": len(words) - 5,
        "opcode_counts": {str(k): v for k, v in sorted(instructions.items())},
        "selected_opcode_counts": {
            name: instructions[k] for k, name in FAMILIES.items()},
    }

def compiler_info(cache: Path) -> dict:
    config = cache.read_text(encoding="utf-8") if cache.is_file() else ""
    values = dict(re.findall(r"^([^#:/\n]+):[^=\n]*=(.*)$", config, re.M))
    compiler = next((values[k] for k in ("GLSLC", "GLSLANG_VALIDATOR")
                     if values.get(k) and not values[k].endswith("-NOTFOUND")), None)
    if compiler is None:
        # Vendored glslang-standalone, if neither configured compiler exists.
        executable = str(cache.parent / "_deps/glslang-build/StandAlone/glslang")
        compiler = executable if Path(executable).is_file() else None
    version = "unavailable"
    if compiler and (Path(compiler).is_file() or shutil.which(compiler)):
        try:
            version = subprocess.run([compiler, "--version"], check=True,
                                     capture_output=True, text=True, timeout=8).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            version = "unavailable"
    return {
        "compiler": compiler, "compiler_version": version,
        "cmake_cache_sha256": hashlib.sha256(config.encode()).hexdigest() if config else None,
        "project_compilation_flags": (
            "glslc --target-env=vulkan1.3 -O" if values.get("GLSLC") and
            not values["GLSLC"].endswith("-NOTFOUND") else
            "glslangValidator -V --target-env vulkan1.3 -S comp"),
    }

def audit(build_dir: Path) -> dict:
    result = {
        "protocol": "n006-p1l-b1c-spirv-static-audit-v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "static_compiler_artifact_only",
        "not_measured": ["dynamic_instruction_count", "ssbo_transactions",
                         "GPU_cache_misses", "VGPR_SGPR", "occupancy",
                         "SIMT_divergence", "GPU_execution_time"],
        "toolchain": compiler_info(build_dir / "CMakeCache.txt"),
        "variants": {},
    }
    for name, (source, target) in VARIANTS.items():
        raw = (build_dir / "shaders" / target).read_bytes()
        source_bytes = (ROOT / source).read_bytes()
        result["variants"][name] = {
            "source": source, "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "spv_file": target, **parse_spirv(raw),
        }
    base = result["variants"]["accepted_original"]
    result["comparison"] = {
        name: {
            "binary_byte_delta": val["binary_bytes"] - base["binary_bytes"],
            "static_instruction_delta": val["instruction_count"] - base["instruction_count"],
            "static_opload_delta": (val["selected_opcode_counts"]["OpLoad"] -
                                    base["selected_opcode_counts"]["OpLoad"]),
            "static_conditional_branch_delta": (
                val["selected_opcode_counts"]["OpBranchConditional"] -
                base["selected_opcode_counts"]["OpBranchConditional"]),
        } for name, val in result["variants"].items() if name != "accepted_original"
    }
    return result

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", type=Path, default=ROOT / os.environ.get(
        "PHOS_GI_BUILD_DIR", "build/release"))
    parser.add_argument("--out", type=Path, default=ROOT /
                        "out/research/n006-interval-aware-allocation/b1c-spv-audit.json")
    args = parser.parse_args()
    obj = audit(args.build_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"status": "static-only", "report": str(args.out),
                      "comparison": obj["comparison"]}, indent=2))

if __name__ == "__main__":
    main()
