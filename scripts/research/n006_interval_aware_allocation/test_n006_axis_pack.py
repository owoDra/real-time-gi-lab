"""Compile and execute header-only axis metadata packing on CPU; no Vulkan/GPU."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HEADER_PARENT = ROOT / "src/research/n006_interval_aware_allocation"
SOURCE = r"""
#include "n006_primary_axis_proxy.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <vector>
struct Node {
    float bounds_min[4]{}, bounds_max[4]{};
    std::uint32_t data[4]{};
};
using phos::gi::research::integration::n006_pack_primary_axis_proxy;
int main() {
    std::vector<Node> nodes(3);
    // Parent child 1 is left (low X), 2 is right (high X).
    nodes[0].data[0]=1; nodes[0].data[1]=2;
    nodes[1].data[0]=0xffffffffu; nodes[1].data[2]=7; nodes[1].bounds_min[0]=-4; nodes[1].bounds_max[0]=-2;
    nodes[2].data[0]=0xffffffffu; nodes[2].data[2]=8; nodes[2].bounds_min[0]=2; nodes[2].bounds_max[0]=4;
    assert(n006_pack_primary_axis_proxy(nodes)==1);
    assert(nodes[0].data[2]==1u && nodes[1].data[2]==7u && nodes[2].data[2]==8u);
    // Reverse child centers; no topology change required.
    nodes[1].bounds_min[0]=8; nodes[1].bounds_max[0]=10;
    assert(n006_pack_primary_axis_proxy(nodes)==1);
    assert(nodes[0].data[2]==4u);
    // Exact coincidence means original right-first.
    nodes[1].bounds_min[0]=2; nodes[1].bounds_max[0]=4;
    assert(n006_pack_primary_axis_proxy(nodes)==1);
    assert(nodes[0].data[2]==0u);
    // Y separation dominates X separation.
    nodes[1].bounds_min[1]=-10; nodes[1].bounds_max[1]=-8;
    assert(n006_pack_primary_axis_proxy(nodes)==1);
    assert(nodes[0].data[2]==2u);
    // Fail closed on malformed child pointers.
    nodes[0].data[0]=100;
    bool threw=false;
    try { (void)n006_pack_primary_axis_proxy(nodes); }
    catch (const std::runtime_error&) { threw=true; }
    assert(threw);
}
"""

class TestN006PackedAxis(unittest.TestCase):
    @unittest.skipUnless(shutil.which(os.environ.get("CXX", "c++")), "C++ compiler unavailable")
    def test_cpu_metadata_packing(self):
        compiler = os.environ.get("CXX", "c++")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "test.cpp"
            out = Path(tmp) / "axis-test"
            src.write_text(SOURCE)
            subprocess.run([compiler, "-std=c++20", "-Wall", "-Wextra",
                            "-Werror", "-I", str(HEADER_PARENT),
                            str(src), "-o", str(out)],
                           check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([str(out)], check=True, timeout=5)

if __name__ == "__main__":
    unittest.main()
