#!/usr/bin/env python3
"""N010-only allocation/free instrumentation; original context sources untouched."""
import argparse
from pathlib import Path
from generate_capture import once


def b002(s):
    s = once(s, '#include "b002_vulkan.hpp"', '#include "b002_vulkan.hpp"\n#include "allocation_ledger.hpp"')
    anchor = """    if (dispatch_.bindBufferMemory(
            output.buffer,"""
    s = once(s, anchor,
             "    phos::gi::research::n010::AllocationLedger::instance().allocate(\n"
             "        device(), output.memory, allocation_info.allocationSize,\n"
             "        allocation_info.memoryTypeIndex, properties, usage);\n" + anchor)
    s = once(s, "        dispatch_.freeMemory(buffer.memory, nullptr);",
             "        dispatch_.freeMemory(buffer.memory, nullptr);\n"
             "        phos::gi::research::n010::AllocationLedger::instance().release(device(), buffer.memory);")
    return s


def vk(s):
    s = once(s, '#include "vk_context.hpp"', '#include "vk_context.hpp"\n#include "allocation_ledger.hpp"')
    s = once(s, "    if (dispatch_.bindBufferMemory(out.buffer, out.memory, 0)",
             "    phos::gi::research::n010::AllocationLedger::instance().allocate(\n"
             "        device(), out.memory, ai.allocationSize, ai.memoryTypeIndex, properties, usage);\n"
             "    if (dispatch_.bindBufferMemory(out.buffer, out.memory, 0)")
    s = once(s, "    if (buffer.memory) dispatch_.freeMemory(buffer.memory, nullptr);",
             "    if (buffer.memory) {\n"
             "        dispatch_.freeMemory(buffer.memory, nullptr);\n"
             "        phos::gi::research::n010::AllocationLedger::instance().release(device(), buffer.memory);\n"
             "    }")
    return s


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rel = "src/research/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_vulkan.cpp"
    (a.out / "n010_b002_vulkan.cpp").write_text(b002((a.root / rel).read_text()))
    (a.out / "n010_vk_context.cpp").write_text(vk((a.root / "src/vk_context.cpp").read_text()))
