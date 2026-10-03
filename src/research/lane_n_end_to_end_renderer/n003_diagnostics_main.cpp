#include "n001_runtime.hpp"

#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
namespace lane_n = phos::gi::research::integration;

namespace {

struct ScenarioSpec {
    const char* name;
    lane_n::I001Scenario scenario;
    bool topology;
};

constexpr std::array<ScenarioSpec, 6> kScenarios{{
    {"static", lane_n::I001Scenario::Static, false},
    {"camera-motion", lane_n::I001Scenario::CameraMotion, false},
    {"light-motion", lane_n::I001Scenario::LightMotion, false},
    {"moving-rigid", lane_n::I001Scenario::MovingRigid, false},
    {"stable-topology-deforming", lane_n::I001Scenario::DeformingControl, false},
    {"topology-changing-high-churn", lane_n::I001Scenario::DeformingControl, true},
}};

enum class Role { Current, Vanilla };

struct Evidence {
    lane_n::I001FrameResult measured;
    lane_n::I001N003HostMemory host;
    std::string device_name;
    std::string driver_name;
    std::string driver_info;
    std::uint32_t api_version{};
    float timestamp_period_ns{};
};

[[nodiscard]] lane_n::I001Options options_for(
    const fs::path& scene,
    const ScenarioSpec& spec) {
    lane_n::I001Options options{};
    options.scene = scene;
    options.variant = lane_n::I001Variant::LaneEFinalHwrt;
    options.scenario = spec.scenario;
    options.validation = true;
    return options;
}

[[nodiscard]] Evidence run_role(
    const fs::path& scene,
    const ScenarioSpec& spec,
    Role role,
    std::uint32_t source_warmup_frames) {
    lane_n::I001Runtime runtime(options_for(scene, spec));
    if (role == Role::Vanilla) {
        runtime.configure_n003_vanilla_software_baseline();
    }

    (void)runtime.run_frame(false);
    if (!runtime.validate_last_frame().passed) {
        throw std::runtime_error(
            std::string("N003 diagnostics source correctness failed for ") +
            spec.name);
    }
    for (std::uint32_t index = 1; index < source_warmup_frames; ++index) {
        (void)runtime.run_frame(false);
    }

    lane_n::I001FrameResult measured{};
    if (spec.topology) {
        measured = role == Role::Current
            ? runtime.run_topology_churn_frame()
            : runtime.run_n003_vanilla_topology_churn_frame();
    } else {
        measured = runtime.run_frame(true);
    }
    if (!runtime.validate_last_frame().passed ||
        measured.stats.storage_failures != 0U) {
        throw std::runtime_error(
            std::string("N003 diagnostics target correctness failed for ") +
            spec.name);
    }

    return {
        measured,
        runtime.n003_host_memory(),
        runtime.device_name(),
        runtime.driver_name(),
        runtime.driver_info(),
        runtime.api_version(),
        runtime.timestamp_period_ns(),
    };
}

void require_same_device(const Evidence& a, const Evidence& b) {
    if (a.device_name != b.device_name || a.driver_name != b.driver_name ||
        a.driver_info != b.driver_info || a.api_version != b.api_version ||
        a.timestamp_period_ns != b.timestamp_period_ns) {
        throw std::runtime_error("N003 diagnostics device provenance mismatch");
    }
}

void require_same_workload(
    const ScenarioSpec& spec,
    const Evidence& current,
    const Evidence& vanilla) {
    const auto& a = current.measured.stats;
    const auto& b = vanilla.measured.stats;
    if (a.work_items != b.work_items ||
        a.outputs != b.outputs ||
        a.requested_work_items != b.requested_work_items ||
        a.requested_outputs != b.requested_outputs ||
        a.overflow != b.overflow ||
        a.visible_owners != b.visible_owners) {
        throw std::runtime_error(
            std::string("N003 diagnostics workload mismatch for ") + spec.name);
    }
    if (spec.topology &&
        (a.moved_primitives != b.moved_primitives ||
         a.topology_mutations != b.topology_mutations ||
         a.topology_replaced_primitives != b.topology_replaced_primitives ||
         a.backend_rebuilds != b.backend_rebuilds)) {
        throw std::runtime_error("N003 diagnostics topology workload mismatch");
    }
}

void write_cpu_diagnostics(
    std::ostream& out,
    const lane_n::I001FrameTimings& t,
    int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << std::setprecision(17)
        << pad << "{\n"
        << pad << "  \"dynamic_update_wall\": " << t.dynamic_update_wall_us << ",\n"
        << pad << "  \"geometry_prepare_cpu\": " << t.geometry_prepare_cpu_us << ",\n"
        << pad << "  \"geometry_transfer_wall\": " << t.geometry_transfer_wall_us << ",\n"
        << pad << "  \"instance_transfer_wall\": " << t.instance_transfer_wall_us << ",\n"
        << pad << "  \"membership_update_cpu\": " << t.membership_update_cpu_us << ",\n"
        << pad << "  \"hierarchy_refit_cpu\": " << t.hierarchy_refit_cpu_us << ",\n"
        << pad << "  \"hierarchy_rebuild_cpu\": " << t.hierarchy_rebuild_cpu_us << ",\n"
        << pad << "  \"hierarchy_occupancy_cpu\": " << t.hierarchy_occupancy_cpu_us << ",\n"
        << pad << "  \"packing_cpu\": " << t.packing_cpu_us << ",\n"
        << pad << "  \"software_bvh_rebuild_cpu\": " << t.software_bvh_rebuild_cpu_us << "\n"
        << pad << "}";
}

void write_host_memory(
    std::ostream& out,
    const lane_n::I001N003HostMemory& m,
    int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n"
        << pad << "  \"scene_surface_capacity\": "
        << m.scene_surface_capacity_bytes << ",\n"
        << pad << "  \"scene_triangle_capacity\": "
        << m.scene_triangle_capacity_bytes << ",\n"
        << pad << "  \"dynamic_selection_capacity\": "
        << m.dynamic_selection_capacity_bytes << ",\n"
        << pad << "  \"candidate_structure_capacity\": "
        << m.candidate_structure_capacity_bytes << ",\n"
        << pad << "  \"renderer_owned_total\": "
        << m.renderer_owned_total_bytes << "\n"
        << pad << "}";
}

void write_role(std::ostream& out, const Evidence& value, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << pad << "{\n"
        << pad << "  \"cpu_wall_diagnostic_us\": ";
    write_cpu_diagnostics(out, value.measured.timings, indent + 2);
    out << ",\n" << pad << "  \"host_memory_bytes\": ";
    write_host_memory(out, value.host, indent + 2);
    out << "\n" << pad << "}";
}

} // namespace

int main(int argc, char** argv) {
    fs::path scene =
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
    fs::path artifact_dir;
    std::uint32_t source_warmup_frames = 32U;

    for (int index = 1; index < argc; ++index) {
        const std::string_view arg = argv[index];
        if (arg == "--scene" && index + 1 < argc) {
            scene = argv[++index];
        } else if (arg == "--artifact-dir" && index + 1 < argc) {
            artifact_dir = argv[++index];
        } else if (arg == "--source-warmup-frames" && index + 1 < argc) {
            source_warmup_frames =
                static_cast<std::uint32_t>(std::stoul(argv[++index]));
        } else {
            std::cerr << "usage: phos-n003-diagnostics --artifact-dir PATH "
                         "[--scene PATH] [--source-warmup-frames N]\n";
            return 2;
        }
    }
    if (artifact_dir.empty() || source_warmup_frames == 0U) {
        std::cerr << "invalid N003 diagnostics arguments\n";
        return 2;
    }

    try {
        fs::create_directories(artifact_dir);
        struct Row {
            const ScenarioSpec* spec{};
            Evidence current;
            Evidence vanilla;
        };
        std::vector<Row> rows;
        rows.reserve(kScenarios.size());

        for (const auto& spec : kScenarios) {
            auto current = run_role(
                scene, spec, Role::Current, source_warmup_frames);
            auto vanilla = run_role(
                scene, spec, Role::Vanilla, source_warmup_frames);
            require_same_device(current, vanilla);
            require_same_workload(spec, current, vanilla);
            rows.push_back({&spec, std::move(current), std::move(vanilla)});
        }

        const auto& device = rows.front().current;
        for (const auto& row : rows) {
            require_same_device(device, row.current);
            require_same_device(device, row.vanilla);
        }

        std::ofstream out(artifact_dir / "n003-diagnostics.json");
        if (!out) {
            throw std::runtime_error("could not open N003 diagnostics artifact");
        }
        out << std::setprecision(17)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"protocol_version\": \"current-vs-vanilla-diagnostics-v1\",\n"
            << "  \"formal_decision_axis\": false,\n"
            << "  \"source_warmup_frames\": " << source_warmup_frames << ",\n"
            << "  \"host_memory_scope\": \"renderer-owned-vector-and-BVH-capacity-only; allocator-bookkeeping-and-opaque-driver-host-memory-excluded\",\n"
            << "  \"device\": {\n"
            << "    \"name\": \"" << device.device_name << "\",\n"
            << "    \"driver_name\": \"" << device.driver_name << "\",\n"
            << "    \"driver_info\": \"" << device.driver_info << "\",\n"
            << "    \"api_version\": " << device.api_version << ",\n"
            << "    \"timestamp_period_ns\": " << device.timestamp_period_ns << "\n"
            << "  },\n"
            << "  \"scenarios\": {\n";
        for (std::size_t index = 0; index < rows.size(); ++index) {
            const auto& row = rows[index];
            out << "    \"" << row.spec->name << "\": {\n"
                << "      \"A\": ";
            write_role(out, row.current, 6);
            out << ",\n      \"B\": ";
            write_role(out, row.vanilla, 6);
            out << "\n    }";
            if (index + 1U != rows.size()) out << ',';
            out << '\n';
        }
        out << "  }\n}\n";
        if (!out) {
            throw std::runtime_error("N003 diagnostics artifact write failed");
        }
        std::cout << "N003 diagnostics: "
                  << (artifact_dir / "n003-diagnostics.json") << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "N003 diagnostics failure: " << error.what() << '\n';
        return 1;
    }
}
