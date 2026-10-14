#!/usr/bin/env python3
"""N010 diagnostic overlay: capture keys inside the actual composite shader."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/research/n007_reference_validity"))
import generate_capture as N7


def once(s, old, new):
    n = s.count(old)
    if n != 1:
        raise ValueError(f"N010 pinned-source drift ({n} matches): {old[:90]}")
    return s.replace(old, new)


def shader(s, binding):
    s = N7.composite(s)
    s = once(s, "void main() {",
             "struct LookupAudit { vec4 position; ivec4 keys[4]; };\n"
             f"layout(std430, binding = {binding}) writeonly buffer Audit {{ LookupAudit records[]; }} audit;\n"
             "void main() {")
    s = once(s, "    HitData hit = hits[id];",
             "    audit.records[id].position = vec4(0.0);\n"
             "    for (int c = 0; c < 4; ++c) audit.records[id].keys[c] = ivec4(-1);\n"
             "    HitData hit = hits[id];")
    s = once(s, "    vec3 normal = normalize(hit.normal_t.xyz);",
             "    audit.records[id].position = vec4(position, 1.0);\n"
             "    vec3 normal = normalize(hit.normal_t.xyz);")
    s = once(s, "        indirect += lookup_probe(probe, cascade);",
             "        audit.records[id].keys[cascade] = ivec4(probe, int(cascade));\n"
             "        indirect += lookup_probe(probe, cascade);")
    return s


def runtime(s):
    s = N7.runtime(s)
    s = once(s, '"n007_hwrt_composite.spv"', '"n010_hwrt_composite.spv"')
    s = once(s, '"n007_software_composite.spv"', '"n010_software_composite.spv"')
    s = once(s, "    B002Buffer primary_hits{}, image{};",
             "    B002Buffer primary_hits{}, image{}, n010_lookup_audit{};")
    s = once(s, "        depth = context.create_device_buffer(",
             "        n010_lookup_audit = context.create_device_buffer(\n"
             "            VkDeviceSize(tile_count) * 80U, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);\n"
             "        depth = context.create_device_buffer(")
    s = once(s, "&storage_stats, &storage_slots, &uniform, &image, &primary_hits,",
             "&n010_lookup_audit, &storage_stats, &storage_slots, &uniform, &image, &primary_hits,")
    marker = "            const std::array<I001Binding, 7> bindings{{\n                {0, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &primary_hits},"
    s = once(s, marker, marker.replace("<I001Binding, 7>", "<I001Binding, 8>"))
    marker = """                {6, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
            }};
            composite_stage"""
    s = once(s, marker, """                {6, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
                {7, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &n010_lookup_audit},
            }};
            composite_stage""")
    s = once(s, "const std::array<I001Binding, 5> composite_bindings{{",
             "const std::array<I001Binding, 6> composite_bindings{{")
    marker = """                {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
            }};
            composite_stage"""
    s = once(s, marker, """                {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
                {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &n010_lookup_audit},
            }};
            composite_stage""")
    s = once(s, '        save("probe-work.bin", items.data(), count * sizeof(LaneAWorkItemV1));',
             """        std::vector<std::uint8_t> audit_bytes(std::size_t(out.width) * out.height * 80U);
        impl_->context.download_device_buffer(impl_->n010_lookup_audit, audit_bytes.data(), audit_bytes.size());
        save("composite-lookup.bin", audit_bytes.data(), audit_bytes.size());
        save("probe-work.bin", items.data(), count * sizeof(LaneAWorkItemV1));""")
    s = once(s, "        memory_stats.stream_capacity_bytes =",
             "        memory_stats.transient_bytes += allocation(n010_lookup_audit);\n"
             "        memory_stats.stream_capacity_bytes =")
    return s


def generate(root, out):
    out.mkdir(parents=True, exist_ok=True)
    src = root / "src/research/lane_n_end_to_end_renderer/n001_runtime.cpp"
    sh = root / "shaders/research/lane_n_end_to_end_renderer"
    (out / "n010_runtime.cpp").write_text(runtime(src.read_text()))
    for name, source, binding in (("hwrt", "n001_composite.comp.glsl", 5),
                                  ("software", "n003_composite_software.comp.glsl", 7)):
        (out / f"n010_{name}_composite.comp.glsl").write_text(shader((sh / source).read_text(), binding))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    generate(a.root, a.out)
