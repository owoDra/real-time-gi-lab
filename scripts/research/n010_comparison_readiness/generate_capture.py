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
    s = once(s, '"n007_hwrt_composite.spv"', '(std::getenv("PHOS_N010_DIRECT_PROFILE") ? "n010_hwrt_corrected_composite.spv" : "n010_hwrt_composite.spv")')
    s = once(s, '"n007_software_composite.spv"', '(std::getenv("PHOS_N010_DIRECT_PROFILE") ? "n010_software_corrected_composite.spv" : "n010_software_composite.spv")')
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
             "const std::array<I001Binding, 7> composite_bindings{{")
    marker = """                {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
            }};
            composite_stage"""
    s = once(s, marker, """                {4, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &uniform},
                {5, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &n010_lookup_audit},
                {6, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &hwrt->triangle_buffer()},
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


def corrected(s, hardware):
    pt = (ROOT / "shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl").read_text()
    helper = pt[pt.index("vec3 offset_position("):pt.index("bool trace(")]
    s = once(s, "bool visible_to_light(", helper + "bool visible_to_light(")
    s = once(s, "float distance_to_light)", "float distance_to_light, uint self)")
    s = once(s, "vec3 origin = position + normal * max(RAY_T_MIN * 8.0, p.camera_pos_near.w * 0.02);",
             "vec3 origin = offset_position(position, normal);\n"
             "    vec3 shifted_light = p.light_pos_interval.xyz - origin;\n"
             "    distance_to_light = length(shifted_light);\n"
             "    to_light = shifted_light / distance_to_light;")
    s = once(s, "float tmax = distance_to_light - max(RAY_T_MIN * 16.0, p.camera_pos_near.w * 0.04);",
             "float tmax = distance_to_light * (1.0 - 2.0e-7);")
    s = s.replace("const float RAY_T_MIN = 1.0e-4;", "const float RAY_T_MIN = 0.0;")
    if hardware:
        s = once(s, "struct HitData", "struct TriangleData { vec4 v0; vec4 v1; vec4 v2; uvec4 metadata; };\n"
                 "layout(std430,binding=6) readonly buffer Triangles { TriangleData triangles[]; };\nstruct HitData")
        s = once(s, "            return false;",
                 "            uint index = uint(rayQueryGetIntersectionInstanceCustomIndexEXT(query, false)) +\n"
                 "                         uint(rayQueryGetIntersectionPrimitiveIndexEXT(query, false));\n"
                 "            if (triangles[index].metadata.x != self) return false;")
        s = once(s, "position, normal, light_direction, distance_to_light)",
                 "position, normal, light_direction, distance_to_light, hit.metadata.x)")
    else:
        s = once(s, "                if (intersects_shadow_triangle(",
                 "                if (triangles[primitive_index].metadata.x != self && intersects_shadow_triangle(")
        s = once(s, "position, normal, light_direction, distance_to_light))",
                 "position, normal, light_direction, distance_to_light, hit.metadata.x))")
    return s


def generate(root, out):
    out.mkdir(parents=True, exist_ok=True)
    src = root / "src/research/lane_n_end_to_end_renderer/n001_runtime.cpp"
    sh = root / "shaders/research/lane_n_end_to_end_renderer"
    nroot = src.parent
    n2 = once((nroot / "n002_runtime.cpp").read_text(), '#include "n001_runtime.cpp"', "")
    n3 = once((nroot / "n003_comparison_runtime.cpp").read_text(), '#include "n002_runtime.cpp"', "")
    n3 = once(n3, "const std::array<I001Binding, 7> composite_bindings{{", "const std::array<I001Binding, 8> composite_bindings{{")
    n3 = once(n3, "        {6, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl_->uniform},", "        {6, VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, &impl_->uniform},\n"
              "        {7, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, &impl_->n010_lookup_audit},")
    n3 = once(n3, '"n003_composite_software.spv"', '(std::getenv("PHOS_N010_DIRECT_PROFILE") ? "n010_software_corrected_composite.spv" : "n010_software_composite.spv")')
    (out / "n010_runtime.cpp").write_text(runtime(src.read_text()) + "\n" + n2 + "\n" + n3)
    main = (root / "src/research/n007_reference_validity/n007_capture_main.cpp").read_text()
    main = once(main, '#include "n001_runtime.hpp"',
                '#include "n001_runtime.hpp"\n#include "allocation_ledger.hpp"')
    main = once(main, "int main(int argc,char** argv) {",
                "int main(int argc,char** argv) {\n"
                "    const char* ledger_path = std::getenv(\"PHOS_N010_MEMORY_LEDGER\");\n"
                "    phos::gi::research::n010::LedgerOutput ledger(ledger_path ? ledger_path : \"\");")
    main = once(main, "        bool target=false;", "        bool target=false, topology=false;\n        std::string profile=\"legacy\";")
    main = once(main, '            else if(arg=="--target-state")target=true;',
                '            else if(arg=="--target-state")target=true;\n'
                '            else if(arg=="--topology-churn")topology=true;\n'
                '            else if(arg=="--direct-profile")profile=arg_value(argc,argv,i);')
    main = once(main, '(backend!="software"&&backend!="hwrt")', '(backend!="software"&&backend!="hwrt"&&backend!="vanilla")')
    main = once(main, '        fs::create_directories(out/"gpu");',
                '        if(fs::exists(out/"capture.json"))throw std::runtime_error("refuse to overwrite capture");\n'
                '        if(profile!="legacy"&&profile!="ulp4")throw std::runtime_error("unknown direct profile");\n'
                '        if(profile=="ulp4")setenv("PHOS_N010_DIRECT_PROFILE","ulp4",1);\n'
                '        else unsetenv("PHOS_N010_DIRECT_PROFILE");\n'
                '        if(topology&&(!target||backend=="software"))throw std::runtime_error("topology requires target hwrt or vanilla");\n'
                '        fs::create_directories(out/"gpu");')
    main = once(main, "        r::I001Runtime runtime(opt);", "        r::I001Runtime runtime(opt);\n"
                "        if(backend==\"vanilla\")runtime.configure_n003_vanilla_software_baseline();")
    main = once(main, '#include <bit>', '#include <bit>\n#include <chrono>\n#include <iomanip>')
    main = once(main, "        auto gpu_frame=runtime.run_frame(false);",
                """        std::ofstream timings(out/"renderer-timings.jsonl");
        timings << std::setprecision(17);
        auto start = std::chrono::steady_clock::now();
        const auto emit_timing = [&](const char* state, const r::I001FrameResult& f) {
            const auto& t=f.timings;
            timings << "{\\\"state\\\":\\\"" << state << "\\\",\\\"classification\\\":\\\"DIAGNOSTIC_UNCALIBRATED\\\","
                << "\\\"complete_renderer_gpu_us\\\":" << t.complete_renderer_gpu_us
                << ",\\\"wall_us\\\":" << std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()
                << ",\\\"primary_visibility_us\\\":" << t.primary_visibility_us
                << ",\\\"composite_us\\\":" << t.composite_us
                << ",\\\"maintenance_gpu_us\\\":" << t.traversal_maintenance_gpu_us
                << ",\\\"blas_us\\\":" << t.blas_update_us << ",\\\"tlas_us\\\":" << t.tlas_update_us
                << ",\\\"work_items\\\":" << f.stats.work_items << ",\\\"overflow\\\":" << f.stats.overflow
                << ",\\\"moved_primitives\\\":" << f.stats.moved_primitives
                << ",\\\"topology_mutations\\\":" << f.stats.topology_mutations << "}\\n";
            if(!timings) throw std::runtime_error("timing output failed");
        };
        auto gpu_frame=runtime.run_frame(false);
        emit_timing("source",gpu_frame);
        start=std::chrono::steady_clock::now();""")
    main = once(main, "        auto gpu_frame=runtime.run_frame(false);",
                "        phos::gi::research::n010::AllocationLedger::instance().phase(\"source-frame\");\n"
                "        auto gpu_frame=runtime.run_frame(false);")
    main = once(main, "        if(target)gpu_frame=runtime.run_frame(true);",
                "        phos::gi::research::n010::AllocationLedger::instance().phase(\"target-frame\");\n"
                "        if(target)gpu_frame=topology ? (backend==\"vanilla\" ? runtime.run_n003_vanilla_topology_churn_frame() : runtime.run_topology_churn_frame()) : runtime.run_frame(true);\n"
                "        if(target)emit_timing(\"first-target\",gpu_frame);\n"
                "        phos::gi::research::n010::AllocationLedger::instance().phase(\"diagnostic-readback\");")
    main = once(main, "        n::FrameParams p{};",
                '        std::cout << "N010 GPU diagnostics captured; legacy N007 CPU audit not run.\\n";\n'
                "        return 0;\n        n::FrameParams p{};")
    (out / "n010_capture_main.cpp").write_text(main)
    for name, source, binding in (("hwrt", "n001_composite.comp.glsl", 5),
                                  ("software", "n003_composite_software.comp.glsl", 7)):
        value=shader((sh / source).read_text(), binding)
        (out / f"n010_{name}_composite.comp.glsl").write_text(value)
        (out / f"n010_{name}_corrected_composite.comp.glsl").write_text(corrected(value,name=="hwrt"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    generate(a.root, a.out)
