#include "b002_compute.hpp"
#include "b002_gpu_layout.hpp"
#include "b002_replay.hpp"
#include "b002_scene.hpp"
#include "b002_vulkan.hpp"
#include "b003_macro_bvh8.hpp"
#include "b003_micro_bvh8.hpp"
#include "hierarchical_stratabrick.hpp"
#include "software_bvh.hpp"

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_b {
namespace {

using Clock = std::chrono::steady_clock;

inline constexpr std::string_view kAcceptedA001Commit =
    "8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f";

struct Cli {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    std::filesystem::path lane_a_artifact{
        "out/research/lane-a-split-rc/001-representative-producer/"
        "20260928T143212Z"};
    std::uint32_t iterations{30};
    std::uint32_t build_repeats{3};
    bool validation{};
};

struct PreparedCase {
    std::string name;
    std::uint64_t workload_id{};
    std::vector<Ray> rays;
    std::vector<GpuRay> gpu_rays;
    std::vector<Hit> reference_hits;
    std::uint64_t reference_semantic_checksum{};
    double stream_parse_us{};
    double replay_convert_us{};
};

struct ResultRow {
    std::string workload;
    std::string candidate;
    std::uint64_t workload_id{};
    std::size_t rays{};
    std::uint32_t iterations{};
    std::size_t mismatches{};
    std::size_t runtime_errors{};
    std::uint64_t semantic_checksum{};
    double stream_parse_us{};
    double replay_convert_us{};
    double scene_load_us{};
    double hierarchy_build_cpu_us{};
    double pack_cpu_us{};
    double macro_build_cpu_us{};
    double accel_upload_us{};
    double ray_upload_us{};
    double trace_us{};
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t logical_stack_bytes_per_ray{};
    std::size_t macro_nodes{};
    std::size_t macro_depth{};
};

struct ValidationResult {
    std::size_t mismatches{};
    std::size_t runtime_errors{};
    std::uint64_t semantic_checksum{};
};

struct BinaryMicroPayload {
    std::vector<GpuBvhNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
};

struct HierarchyBuildMeasurement {
    double total_us{};
    double membership_us{};
    double segment_build_us{};
    double occupancy_us{};
};

[[nodiscard]] double elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(
        Clock::now() - start).count();
}

[[nodiscard]] Cli parse_cli(int argc, char** argv) {
    Cli cli;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        const auto value = [&](const char* option) -> std::string {
            if (index + 1 >= argc) {
                throw std::runtime_error(
                    std::string(option) + " requires a value");
            }
            return argv[++index];
        };

        if (argument == "--scene") {
            cli.scene = value("--scene");
        } else if (argument == "--lane-a-artifact") {
            cli.lane_a_artifact = value("--lane-a-artifact");
        } else if (argument == "--iterations") {
            cli.iterations = static_cast<std::uint32_t>(
                std::stoul(value("--iterations")));
        } else if (argument == "--build-repeats") {
            cli.build_repeats = static_cast<std::uint32_t>(
                std::stoul(value("--build-repeats")));
        } else if (argument == "--validation") {
            cli.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-b-b003 "
                   "[--scene path] [--lane-a-artifact path] "
                   "[--iterations N] [--build-repeats N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "Unknown B003 argument: " + argument);
        }
    }

    if (cli.iterations == 0 || cli.iterations > 255 ||
        cli.build_repeats == 0) {
        throw std::runtime_error(
            "B003 iterations must be 1..255 and build-repeats positive");
    }
    return cli;
}

[[nodiscard]] std::uint64_t fnv_add(
    std::uint64_t hash,
    std::uint32_t value) noexcept {
    for (int byte = 0; byte < 4; ++byte) {
        hash ^= static_cast<unsigned char>(
            (value >> (byte * 8)) & 0xffU);
        hash *= 1099511628211ULL;
    }
    return hash;
}

[[nodiscard]] std::uint64_t semantic_checksum(
    std::span<const Hit> hits) noexcept {
    std::uint64_t hash = 14695981039346656037ULL;
    for (const auto& hit : hits) {
        hash = fnv_add(hash, hit.hit ? 1U : 0U);
        hash = fnv_add(hash, hit.primitive_id);
        hash = fnv_add(hash, hit.material_id);
        hash = fnv_add(hash, hit.instance_id);
        if (hit.hit) {
            hash = fnv_add(
                hash,
                std::bit_cast<std::uint32_t>(hit.t));
            hash = fnv_add(
                hash,
                std::bit_cast<std::uint32_t>(hit.normal.x));
            hash = fnv_add(
                hash,
                std::bit_cast<std::uint32_t>(hit.normal.y));
            hash = fnv_add(
                hash,
                std::bit_cast<std::uint32_t>(hit.normal.z));
        }
    }
    return hash;
}

[[nodiscard]] ValidationResult validate_gpu_hits(
    std::span<const Hit> expected,
    std::span<const GpuHit> actual) {
    if (expected.size() != actual.size()) {
        throw std::runtime_error(
            "B003 GPU hit count differs from reference");
    }

    ValidationResult result;
    std::vector<Hit> canonical;
    canonical.reserve(actual.size());
    for (std::size_t index = 0;
         index < actual.size();
         ++index) {
        if (actual[index].metadata[3] > 1U) {
            ++result.runtime_errors;
            ++result.mismatches;
            canonical.push_back({});
            continue;
        }
        const auto hit = from_gpu_hit(actual[index]);
        if (!equivalent_hit(expected[index], hit)) {
            ++result.mismatches;
            canonical.push_back(hit);
        } else {
            canonical.push_back(expected[index]);
        }
    }
    result.semantic_checksum =
        semantic_checksum(canonical);
    return result;
}

void verify_reference_sample(
    const B002Scene& scene,
    const SoftwareBvh& reference,
    std::span<const Ray> rays) {
    const std::size_t samples =
        std::min<std::size_t>(64, rays.size());
    for (std::size_t sample = 0;
         sample < samples;
         ++sample) {
        const auto index =
            sample * rays.size() / samples;
        const auto brute =
            trace_reference(
                scene.triangles,
                rays[index]);
        const auto accelerated =
            reference.trace(rays[index]);
        if (!equivalent_hit(brute, accelerated)) {
            throw std::runtime_error(
                "B003 CPU reference BVH diverged from brute-force contract");
        }
    }
}

[[nodiscard]] PreparedCase prepare_case(
    const std::filesystem::path& artifact_root,
    std::string_view name,
    const B002Scene& scene,
    const SoftwareBvh& reference) {
    const auto path =
        artifact_root /
        std::string(name) /
        "stream-v1.bin";

    auto start = Clock::now();
    auto stream = load_lane_a_stream_v1(path);
    const auto parse_us = elapsed_us(start);

    for (const auto& item : stream.items) {
        if (item.surface_id >= scene.triangles.size() ||
            scene.triangles[item.surface_id].primitive_id !=
                item.surface_id) {
            throw std::runtime_error(
                "B003 scene primitive order is not aligned with Lane A surface_id");
        }
    }

    start = Clock::now();
    auto rays = lane_a_replay_rays(stream);
    std::vector<GpuRay> gpu_rays;
    gpu_rays.reserve(rays.size());
    for (const auto ray : rays) {
        gpu_rays.push_back(to_gpu_ray(ray));
    }
    const auto convert_us = elapsed_us(start);

    verify_reference_sample(
        scene,
        reference,
        rays);

    std::vector<Hit> reference_hits;
    reference_hits.reserve(rays.size());
    for (const auto ray : rays) {
        reference_hits.push_back(
            reference.trace(ray));
    }

    const auto checksum =
        semantic_checksum(reference_hits);
    return {
        std::string(name),
        stream.header.workload_id,
        std::move(rays),
        std::move(gpu_rays),
        std::move(reference_hits),
        checksum,
        parse_us,
        convert_us,
    };
}

[[nodiscard]] HierarchyBuildMeasurement
measure_hierarchy_build(
    const std::vector<Triangle>& triangles,
    float segment_size,
    std::uint32_t repeats) {
    std::vector<double> total;
    std::vector<double> membership;
    std::vector<double> segment;
    std::vector<double> occupancy;
    total.reserve(repeats);
    membership.reserve(repeats);
    segment.reserve(repeats);
    occupancy.reserve(repeats);

    for (std::uint32_t repeat = 0;
         repeat < repeats;
         ++repeat) {
        const auto start = Clock::now();
        HierarchicalStrataBrick build(
            triangles,
            segment_size);
        total.push_back(elapsed_us(start));
        membership.push_back(
            build.build_stats().membership_generation_us);
        segment.push_back(
            build.build_stats().segment_construction_us);
        occupancy.push_back(
            build.build_stats().occupancy_bounds_us);
    }

    return {
        median_us(std::move(total)),
        median_us(std::move(membership)),
        median_us(std::move(segment)),
        median_us(std::move(occupancy)),
    };
}

[[nodiscard]] BinaryMicroPayload
make_binary_micro_payload(
    const HierarchicalFlatPayload& flat) {
    BinaryMicroPayload payload;
    payload.ordered_primitives =
        flat.ordered_primitives;
    payload.nodes.reserve(flat.nodes.size());

    for (const auto& node : flat.nodes) {
        payload.nodes.push_back(
            to_gpu_node(
                node.bounds,
                node.left,
                node.right,
                node.begin,
                node.count));
    }
    return payload;
}

[[nodiscard]] std::vector<GpuTriangle>
make_gpu_triangles(
    const B002Scene& scene) {
    std::vector<GpuTriangle> output;
    output.reserve(scene.triangles.size());
    for (const auto& triangle : scene.triangles) {
        output.push_back(
            to_gpu_triangle(triangle));
    }
    return output;
}

[[nodiscard]] std::string json_escape(
    std::string_view value) {
    std::string output;
    output.reserve(value.size());
    for (const char ch : value) {
        switch (ch) {
        case '\\': output += "\\\\"; break;
        case '"': output += "\\\""; break;
        case '\n': output += "\\n"; break;
        case '\r': output += "\\r"; break;
        case '\t': output += "\\t"; break;
        default:
            if (static_cast<unsigned char>(ch) < 0x20U) {
                output += '?';
            } else {
                output += ch;
            }
        }
    }
    return output;
}

[[nodiscard]] std::filesystem::path
artifact_root() {
    if (const char* value =
            std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return
        "out/research/lane-b-traversal/"
        "003-wide-software-traversal/manual";
}

void write_rows(
    const std::filesystem::path& path,
    std::span<const ResultRow> rows) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B003 result CSV: " +
            path.string());
    }

    output
        << "workload,candidate,workload_id,rays,iterations,mismatches,"
           "runtime_errors,semantic_checksum,stream_parse_us,replay_convert_us,"
           "scene_load_us,hierarchy_build_cpu_us,pack_cpu_us,"
           "candidate_build_cpu_us,accel_upload_us,ray_upload_us,trace_us,"
           "persistent_bytes,transient_bytes,logical_stack_bytes_per_ray,"
           "structure_nodes,structure_depth\n";
    output << std::fixed << std::setprecision(3);

    for (const auto& row : rows) {
        output
            << row.workload << ','
            << row.candidate << ','
            << row.workload_id << ','
            << row.rays << ','
            << row.iterations << ','
            << row.mismatches << ','
            << row.runtime_errors << ','
            << row.semantic_checksum << ','
            << row.stream_parse_us << ','
            << row.replay_convert_us << ','
            << row.scene_load_us << ','
            << row.hierarchy_build_cpu_us << ','
            << row.pack_cpu_us << ','
            << row.macro_build_cpu_us << ','
            << row.accel_upload_us << ','
            << row.ray_upload_us << ','
            << row.trace_us << ','
            << row.persistent_bytes << ','
            << row.transient_bytes << ','
            << row.logical_stack_bytes_per_ray << ','
            << row.macro_nodes << ','
            << row.macro_depth
            << '\n';
    }
}

void write_correctness_json(
    const std::filesystem::path& path,
    std::span<const PreparedCase> cases,
    std::span<const ResultRow> rows) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B003 correctness JSON");
    }

    std::size_t mismatches = 0;
    std::size_t runtime_errors = 0;
    for (const auto& row : rows) {
        mismatches += row.mismatches;
        runtime_errors += row.runtime_errors;
    }

    output
        << "{\n"
        << "  \"shared_hit_contract\": \"B001\",\n"
        << "  \"reference_sample\": \"brute-force parity checked\",\n"
        << "  \"total_mismatches\": "
        << mismatches << ",\n"
        << "  \"total_runtime_errors\": "
        << runtime_errors << ",\n"
        << "  \"cases\": {\n";

    for (std::size_t index = 0;
         index < cases.size();
         ++index) {
        const auto& current = cases[index];
        output
            << "    \"" << current.name << "\": {"
            << "\"workload_id\": "
            << current.workload_id << ", "
            << "\"rays\": "
            << current.rays.size() << ", "
            << "\"reference_semantic_checksum\": "
            << current.reference_semantic_checksum
            << "}";
        if (index + 1 != cases.size()) {
            output << ',';
        }
        output << '\n';
    }

    output
        << "  }\n"
        << "}\n";
}

void write_stage_a_summary(
    const std::filesystem::path& path,
    std::span<const ResultRow> rows) {
    double baseline_sum = 0.0;
    double macro_sum = 0.0;
    std::size_t baseline_count = 0;
    std::size_t macro_count = 0;
    std::size_t baseline_memory = 0;
    std::size_t macro_memory = 0;
    std::size_t errors = 0;

    for (const auto& row : rows) {
        if (row.candidate ==
            "hierarchical-stratabrick") {
            errors += row.mismatches +
                row.runtime_errors;
            baseline_sum += row.trace_us;
            ++baseline_count;
            baseline_memory =
                row.persistent_bytes;
        } else if (row.candidate ==
                   "macro-bvh8-binary-micro") {
            errors += row.mismatches +
                row.runtime_errors;
            macro_sum += row.trace_us;
            ++macro_count;
            macro_memory =
                row.persistent_bytes;
        }
    }

    if (baseline_count != kB002Cases.size() ||
        macro_count != kB002Cases.size()) {
        throw std::runtime_error(
            "B003 Stage A summary missing required candidate rows");
    }

    const auto baseline_mean =
        baseline_sum /
        static_cast<double>(baseline_count);
    const auto macro_mean =
        macro_sum /
        static_cast<double>(macro_count);
    const auto improvement =
        baseline_mean > 0.0
        ? 1.0 - macro_mean / baseline_mean
        : 0.0;
    const auto memory_ratio =
        baseline_memory != 0
        ? static_cast<double>(macro_memory) /
            static_cast<double>(baseline_memory)
        : std::numeric_limits<double>::infinity();

    const bool advance =
        errors == 0 &&
        improvement >= 0.20 &&
        memory_ratio <= 1.15;

    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B003 Stage A summary");
    }
    output
        << std::fixed << std::setprecision(6)
        << "{\n"
        << "  \"baseline_mean_trace_us\": "
        << baseline_mean << ",\n"
        << "  \"macro_mean_trace_us\": "
        << macro_mean << ",\n"
        << "  \"trace_improvement_fraction\": "
        << improvement << ",\n"
        << "  \"baseline_persistent_bytes\": "
        << baseline_memory << ",\n"
        << "  \"macro_persistent_bytes\": "
        << macro_memory << ",\n"
        << "  \"memory_ratio\": "
        << memory_ratio << ",\n"
        << "  \"correctness_errors\": "
        << errors << ",\n"
        << "  \"advance_to_stage_b\": "
        << (advance ? "true" : "false")
        << "\n"
        << "}\n";
}


void write_stage_b_summary(
    const std::filesystem::path& path,
    std::span<const ResultRow> rows) {
    double baseline_sum = 0.0;
    double wide_sum = 0.0;
    std::size_t baseline_count = 0;
    std::size_t wide_count = 0;
    std::size_t baseline_memory = 0;
    std::size_t wide_memory = 0;
    std::size_t errors = 0;

    for (const auto& row : rows) {
        if (row.candidate ==
            "hierarchical-stratabrick") {
            errors += row.mismatches +
                row.runtime_errors;
            baseline_sum += row.trace_us;
            ++baseline_count;
            baseline_memory =
                row.persistent_bytes;
        } else if (row.candidate ==
                   "dda-wide-micro-bvh8") {
            errors += row.mismatches +
                row.runtime_errors;
            wide_sum += row.trace_us;
            ++wide_count;
            wide_memory =
                row.persistent_bytes;
        }
    }

    if (baseline_count != kB002Cases.size() ||
        wide_count != kB002Cases.size()) {
        throw std::runtime_error(
            "B003 Stage B summary missing required candidate rows");
    }

    const auto baseline_mean =
        baseline_sum /
        static_cast<double>(baseline_count);
    const auto wide_mean =
        wide_sum /
        static_cast<double>(wide_count);
    const auto trace_ratio =
        baseline_mean > 0.0
        ? wide_mean / baseline_mean
        : std::numeric_limits<double>::infinity();
    const auto improvement =
        baseline_mean > 0.0
        ? 1.0 - trace_ratio
        : 0.0;
    const auto memory_ratio =
        baseline_memory != 0
        ? static_cast<double>(wide_memory) /
            static_cast<double>(baseline_memory)
        : std::numeric_limits<double>::infinity();

    // An uncompressed float BVH8 only needs to stay close enough to the
    // binary baseline to justify testing the compression mechanism that wide
    // GPU BVHs normally rely on. A catastrophic slowdown rejects the branch.
    const bool advance =
        errors == 0 &&
        trace_ratio <= 1.15 &&
        memory_ratio <= 1.50;

    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error(
            "Could not create B003 Stage B summary");
    }
    output
        << std::fixed << std::setprecision(6)
        << "{\n"
        << "  \"baseline_mean_trace_us\": "
        << baseline_mean << ",\n"
        << "  \"wide_micro_mean_trace_us\": "
        << wide_mean << ",\n"
        << "  \"trace_ratio\": "
        << trace_ratio << ",\n"
        << "  \"trace_improvement_fraction\": "
        << improvement << ",\n"
        << "  \"baseline_persistent_bytes\": "
        << baseline_memory << ",\n"
        << "  \"wide_micro_persistent_bytes\": "
        << wide_memory << ",\n"
        << "  \"memory_ratio\": "
        << memory_ratio << ",\n"
        << "  \"correctness_errors\": "
        << errors << ",\n"
        << "  \"advance_to_quantization\": "
        << (advance ? "true" : "false")
        << "\n"
        << "}\n";
}

} // namespace
} // namespace phos::gi::research::lane_b

int main(int argc, char** argv) {
    using namespace phos::gi::research::lane_b;

    try {
        const auto cli = parse_cli(argc, argv);
        if (!std::filesystem::exists(cli.scene)) {
            throw std::runtime_error(
                "B003 scene not found; run 'mise run assets' first: " +
                cli.scene.string());
        }
        for (const auto name : kB002Cases) {
            const auto path =
                cli.lane_a_artifact /
                std::string(name) /
                "stream-v1.bin";
            if (!std::filesystem::exists(path)) {
                throw std::runtime_error(
                    "B003 accepted Lane A stream not found: " +
                    path.string());
            }
        }

        const auto output_root = artifact_root();
        std::filesystem::create_directories(
            output_root);

        auto start = Clock::now();
        const auto scene =
            load_b002_scene(cli.scene);
        const auto scene_load_us =
            elapsed_us(start);
        const auto segment_size =
            b002_segment_size(scene);

        SoftwareBvh reference(scene.triangles);
        std::vector<PreparedCase> cases;
        cases.reserve(kB002Cases.size());
        for (const auto name : kB002Cases) {
            cases.push_back(
                prepare_case(
                    cli.lane_a_artifact,
                    name,
                    scene,
                    reference));
        }

        const auto hierarchy_measurement =
            measure_hierarchy_build(
                scene.triangles,
                segment_size,
                cli.build_repeats);
        HierarchicalStrataBrick hierarchy(
            scene.triangles,
            segment_size);

        start = Clock::now();
        const auto flat = hierarchy.flatten();
        const auto baseline_payload =
            make_hierarchical_gpu_payload(flat);
        const auto baseline_pack_us =
            elapsed_us(start);

        start = Clock::now();
        const auto micro_payload =
            make_binary_micro_payload(flat);
        const auto micro_pack_us =
            elapsed_us(start);

        std::vector<double> macro_build_samples;
        macro_build_samples.reserve(
            cli.build_repeats);
        for (std::uint32_t repeat = 0;
             repeat < cli.build_repeats;
             ++repeat) {
            start = Clock::now();
            auto candidate =
                make_b003_macro_bvh8(flat, segment_size);
            volatile auto root =
                candidate.root;
            (void)root;
            macro_build_samples.push_back(
                elapsed_us(start));
        }
        const auto macro_build_us =
            median_us(
                std::move(macro_build_samples));
        const auto macro_payload =
            make_b003_macro_bvh8(flat, segment_size);

        std::vector<double> wide_build_samples;
        wide_build_samples.reserve(
            cli.build_repeats);
        for (std::uint32_t repeat = 0;
             repeat < cli.build_repeats;
             ++repeat) {
            start = Clock::now();
            auto candidate =
                make_b003_wide_micro_payload(flat);
            volatile auto nodes =
                candidate.nodes.size();
            (void)nodes;
            wide_build_samples.push_back(
                elapsed_us(start));
        }
        const auto wide_build_us =
            median_us(
                std::move(wide_build_samples));
        const auto wide_payload =
            make_b003_wide_micro_payload(flat);

        if (wide_payload.segment_count !=
                flat.segments.size() ||
            wide_payload.max_stack_entries > 64U) {
            throw std::runtime_error(
                "B003 wide micro payload failed structural gate");
        }

        if (macro_payload.root == kInvalidId ||
            macro_payload.segment_count !=
                flat.segments.size()) {
            throw std::runtime_error(
                "B003 macro BVH did not retain every occupied segment");
        }
        if (macro_payload.max_stack_entries > 32U) {
            throw std::runtime_error(
                "B003 macro BVH exceeds the shader macro stack capacity");
        }

        const auto gpu_triangles =
            make_gpu_triangles(scene);

        {
            std::ofstream config(
                output_root / "b003-config.json");
            if (!config) {
                throw std::runtime_error(
                    "Could not create B003 config JSON");
            }
            config
                << "{\n"
                << "  \"schema_version\": 1,\n"
                << "  \"experiment\": "
                   "\"003-wide-software-traversal\",\n"
                << "  \"stage\": \"A\",\n"
                << "  \"lane_a_measurement_commit\": \""
                << kAcceptedA001Commit << "\",\n"
                << "  \"lane_a_artifact\": \""
                << json_escape(
                    cli.lane_a_artifact.string())
                << "\",\n"
                << "  \"scene\": \""
                << json_escape(cli.scene.string())
                << "\",\n"
                << "  \"scene_triangles\": "
                << scene.triangles.size() << ",\n"
                << "  \"hierarchy_segment_size\": "
                << std::setprecision(9)
                << segment_size << ",\n"
                << "  \"segments\": "
                << flat.segments.size() << ",\n"
                << "  \"memberships\": "
                << hierarchy.membership_count()
                << ",\n"
                << "  \"binary_micro_nodes\": "
                << micro_payload.nodes.size()
                << ",\n"
                << "  \"macro_nodes\": "
                << macro_payload.nodes.size()
                << ",\n"
                << "  \"macro_depth\": "
                << macro_payload.max_depth
                << ",\n"
                << "  \"macro_max_stack_entries\": "
                << macro_payload.max_stack_entries
                << ",\n"
                << "  \"macro_fanout\": 8,\n"
                << "  \"wide_micro_nodes\": "
                << wide_payload.nodes.size()
                << ",\n"
                << "  \"wide_micro_depth\": "
                << wide_payload.max_depth
                << ",\n"
                << "  \"wide_micro_max_stack_entries\": "
                << wide_payload.max_stack_entries
                << ",\n"
                << "  \"wide_micro_hash_slots\": "
                << wide_payload.hash_table.size()
                << ",\n"
                << "  \"wide_micro_hash_max_probe\": "
                << wide_payload.hash_max_probe
                << ",\n"
                << "  \"iterations\": "
                << cli.iterations << ",\n"
                << "  \"build_repeats\": "
                << cli.build_repeats << ",\n"
                << "  \"validation\": "
                << (cli.validation
                        ? "true"
                        : "false")
                << "\n"
                << "}\n";
        }

        std::vector<ResultRow> rows;

        B002VulkanContext context(
            cli.validation);
        if (context.device_name() !=
            kB002TargetDeviceName) {
            throw std::runtime_error(
                "B003 exact target device mismatch");
        }

        {
            std::ofstream device(
                output_root / "b003-device.json");
            if (!device) {
                throw std::runtime_error(
                    "Could not create B003 device JSON");
            }
            device
                << "{\n"
                << "  \"target_device\": \""
                << kB002TargetDeviceName
                << "\",\n"
                << "  \"selected_device\": \""
                << json_escape(
                    context.device_name())
                << "\",\n"
                << "  \"driver_name\": \""
                << json_escape(
                    context.driver_name())
                << "\",\n"
                << "  \"driver_info\": \""
                << json_escape(
                    context.driver_info())
                << "\",\n"
                << "  \"api_version\": "
                << context.api_version() << ",\n"
                << "  \"exact_device_match\": true\n"
                << "}\n";
        }

        start = Clock::now();
        auto triangle_buffer =
            context.upload_device_buffer(
                gpu_triangles.data(),
                gpu_triangles.size() *
                    sizeof(GpuTriangle),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const auto triangle_upload_us =
            elapsed_us(start);

        start = Clock::now();
        auto baseline_node_buffer =
            context.upload_device_buffer(
                baseline_payload.nodes.data(),
                baseline_payload.nodes.size() *
                    sizeof(GpuBvhNode),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto baseline_order_buffer =
            context.upload_device_buffer(
                baseline_payload
                    .ordered_primitives.data(),
                baseline_payload
                    .ordered_primitives.size() *
                    sizeof(std::uint32_t),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto baseline_hash_buffer =
            context.upload_device_buffer(
                baseline_payload.hash_table.data(),
                baseline_payload.hash_table.size() *
                    sizeof(GpuSegmentHashEntry),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const auto baseline_upload_us =
            elapsed_us(start) +
            triangle_upload_us;

        start = Clock::now();
        auto macro_node_buffer =
            context.upload_device_buffer(
                micro_payload.nodes.data(),
                micro_payload.nodes.size() *
                    sizeof(GpuBvhNode),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto macro_order_buffer =
            context.upload_device_buffer(
                micro_payload
                    .ordered_primitives.data(),
                micro_payload
                    .ordered_primitives.size() *
                    sizeof(std::uint32_t),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto macro_top_buffer =
            context.upload_device_buffer(
                macro_payload.nodes.data(),
                macro_payload.nodes.size() *
                    sizeof(B003GpuMacroNode),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const auto macro_upload_us =
            elapsed_us(start) +
            triangle_upload_us;

        start = Clock::now();
        auto wide_node_buffer =
            context.upload_device_buffer(
                wide_payload.nodes.data(),
                wide_payload.nodes.size() *
                    sizeof(B003GpuWideNode),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto wide_order_buffer =
            context.upload_device_buffer(
                wide_payload
                    .ordered_primitives.data(),
                wide_payload
                    .ordered_primitives.size() *
                    sizeof(std::uint32_t),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        auto wide_hash_buffer =
            context.upload_device_buffer(
                wide_payload.hash_table.data(),
                wide_payload.hash_table.size() *
                    sizeof(GpuSegmentHashEntry),
                VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        const auto wide_upload_us =
            elapsed_us(start) +
            triangle_upload_us;

        const auto baseline_persistent =
            static_cast<std::size_t>(
                triangle_buffer.allocation_size +
                baseline_node_buffer.allocation_size +
                baseline_order_buffer.allocation_size +
                baseline_hash_buffer.allocation_size);
        const auto macro_persistent =
            static_cast<std::size_t>(
                triangle_buffer.allocation_size +
                macro_node_buffer.allocation_size +
                macro_order_buffer.allocation_size +
                macro_top_buffer.allocation_size);
        const auto wide_persistent =
            static_cast<std::size_t>(
                triangle_buffer.allocation_size +
                wide_node_buffer.allocation_size +
                wide_order_buffer.allocation_size +
                wide_hash_buffer.allocation_size);

        for (const auto& replay : cases) {
            const auto ray_bytes =
                VkDeviceSize(
                    replay.gpu_rays.size() *
                    sizeof(GpuRay));
            const auto hit_bytes =
                VkDeviceSize(
                    replay.gpu_rays.size() *
                    sizeof(GpuHit));

            start = Clock::now();
            auto ray_buffer =
                context.upload_device_buffer(
                    replay.gpu_rays.data(),
                    ray_bytes,
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            const auto ray_upload_us =
                elapsed_us(start);

            auto baseline_hit_buffer =
                context.create_device_buffer(
                    hit_bytes,
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            std::array<const B002Buffer*, 6>
                baseline_bindings{
                    &ray_buffer,
                    &triangle_buffer,
                    &baseline_node_buffer,
                    &baseline_order_buffer,
                    &baseline_hash_buffer,
                    &baseline_hit_buffer,
                };
            B002ComputeTraversal baseline_runner(
                context,
                (std::filesystem::path(
                    PHOS_GI_LANE_B_SHADER_DIR) /
                    "lane_b_b002_hierarchical.spv")
                    .string(),
                baseline_bindings,
                sizeof(HierarchicalTraversalPush));

            HierarchicalTraversalPush
                baseline_push{};
            baseline_push.values[0] =
                static_cast<std::uint32_t>(
                    replay.gpu_rays.size());
            baseline_push.values[1] =
                baseline_payload.hash_mask;
            baseline_push.values[2] =
                baseline_payload.hash_max_probe;
            const auto max_steps =
                std::max<std::uint64_t>(
                    64,
                    std::uint64_t(
                        flat.segments.size()) *
                        16U +
                    64U);
            baseline_push.values[3] =
                static_cast<std::uint32_t>(
                    std::min<std::uint64_t>(
                        max_steps,
                        std::numeric_limits<
                            std::uint32_t>::max()));
            baseline_push
                .occupied_min_segment_size[0] =
                baseline_payload
                    .occupied_bounds.min.x;
            baseline_push
                .occupied_min_segment_size[1] =
                baseline_payload
                    .occupied_bounds.min.y;
            baseline_push
                .occupied_min_segment_size[2] =
                baseline_payload
                    .occupied_bounds.min.z;
            baseline_push
                .occupied_min_segment_size[3] =
                segment_size;
            baseline_push
                .occupied_max_pad[0] =
                baseline_payload
                    .occupied_bounds.max.x;
            baseline_push
                .occupied_max_pad[1] =
                baseline_payload
                    .occupied_bounds.max.y;
            baseline_push
                .occupied_max_pad[2] =
                baseline_payload
                    .occupied_bounds.max.z;

            const auto baseline_trace_us =
                baseline_runner.measure(
                    baseline_push.values[0],
                    cli.iterations,
                    &baseline_push,
                    sizeof(baseline_push));

            std::vector<GpuHit> baseline_hits(
                replay.gpu_rays.size());
            context.download_device_buffer(
                baseline_hit_buffer,
                baseline_hits.data(),
                hit_bytes);
            const auto baseline_validation =
                validate_gpu_hits(
                    replay.reference_hits,
                    baseline_hits);

            rows.push_back({
                replay.name,
                "hierarchical-stratabrick",
                replay.workload_id,
                replay.rays.size(),
                cli.iterations,
                baseline_validation.mismatches,
                baseline_validation.runtime_errors,
                baseline_validation.semantic_checksum,
                replay.stream_parse_us,
                replay.replay_convert_us,
                scene_load_us,
                hierarchy_measurement.total_us,
                baseline_pack_us,
                0.0,
                baseline_upload_us,
                ray_upload_us,
                baseline_trace_us,
                baseline_persistent,
                static_cast<std::size_t>(
                    ray_buffer.allocation_size +
                    baseline_hit_buffer
                        .allocation_size),
                128U *
                    sizeof(std::uint32_t),
                0,
                0,
            });

            auto macro_hit_buffer =
                context.create_device_buffer(
                    hit_bytes,
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            std::array<const B002Buffer*, 6>
                macro_bindings{
                    &ray_buffer,
                    &triangle_buffer,
                    &macro_node_buffer,
                    &macro_order_buffer,
                    &macro_top_buffer,
                    &macro_hit_buffer,
                };
            B002ComputeTraversal macro_runner(
                context,
                (std::filesystem::path(
                    PHOS_GI_LANE_B_SHADER_DIR) /
                    "lane_b_b003_macro_bvh8.spv")
                    .string(),
                macro_bindings,
                sizeof(SoftwareTraversalPush));

            SoftwareTraversalPush macro_push{
                static_cast<std::uint32_t>(
                    replay.gpu_rays.size()),
                macro_payload.root,
                0U,
                0U,
            };

            const auto macro_trace_us =
                macro_runner.measure(
                    macro_push.ray_count,
                    cli.iterations,
                    &macro_push,
                    sizeof(macro_push));

            std::vector<GpuHit> macro_hits(
                replay.gpu_rays.size());
            context.download_device_buffer(
                macro_hit_buffer,
                macro_hits.data(),
                hit_bytes);
            const auto macro_validation =
                validate_gpu_hits(
                    replay.reference_hits,
                    macro_hits);

            rows.push_back({
                replay.name,
                "macro-bvh8-binary-micro",
                replay.workload_id,
                replay.rays.size(),
                cli.iterations,
                macro_validation.mismatches,
                macro_validation.runtime_errors,
                macro_validation.semantic_checksum,
                replay.stream_parse_us,
                replay.replay_convert_us,
                scene_load_us,
                hierarchy_measurement.total_us,
                micro_pack_us,
                macro_build_us,
                macro_upload_us,
                ray_upload_us,
                macro_trace_us,
                macro_persistent,
                static_cast<std::size_t>(
                    ray_buffer.allocation_size +
                    macro_hit_buffer
                        .allocation_size),
                (128U + 32U) *
                    sizeof(std::uint32_t),
                macro_payload.nodes.size(),
                macro_payload.max_depth,
            });

            auto wide_hit_buffer =
                context.create_device_buffer(
                    hit_bytes,
                    VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
            std::array<const B002Buffer*, 6>
                wide_bindings{
                    &ray_buffer,
                    &triangle_buffer,
                    &wide_node_buffer,
                    &wide_order_buffer,
                    &wide_hash_buffer,
                    &wide_hit_buffer,
                };
            B002ComputeTraversal wide_runner(
                context,
                (std::filesystem::path(
                    PHOS_GI_LANE_B_SHADER_DIR) /
                    "lane_b_b003_micro_bvh8.spv")
                    .string(),
                wide_bindings,
                sizeof(HierarchicalTraversalPush));

            HierarchicalTraversalPush wide_push{};
            wide_push.values[0] =
                static_cast<std::uint32_t>(
                    replay.gpu_rays.size());
            wide_push.values[1] =
                wide_payload.hash_mask;
            wide_push.values[2] =
                wide_payload.hash_max_probe;
            wide_push.values[3] =
                static_cast<std::uint32_t>(
                    std::min<std::uint64_t>(
                        max_steps,
                        std::numeric_limits<
                            std::uint32_t>::max()));
            wide_push
                .occupied_min_segment_size[0] =
                wide_payload.occupied_bounds.min.x;
            wide_push
                .occupied_min_segment_size[1] =
                wide_payload.occupied_bounds.min.y;
            wide_push
                .occupied_min_segment_size[2] =
                wide_payload.occupied_bounds.min.z;
            wide_push
                .occupied_min_segment_size[3] =
                segment_size;
            wide_push
                .occupied_max_pad[0] =
                wide_payload.occupied_bounds.max.x;
            wide_push
                .occupied_max_pad[1] =
                wide_payload.occupied_bounds.max.y;
            wide_push
                .occupied_max_pad[2] =
                wide_payload.occupied_bounds.max.z;

            const auto wide_trace_us =
                wide_runner.measure(
                    wide_push.values[0],
                    cli.iterations,
                    &wide_push,
                    sizeof(wide_push));

            std::vector<GpuHit> wide_hits(
                replay.gpu_rays.size());
            context.download_device_buffer(
                wide_hit_buffer,
                wide_hits.data(),
                hit_bytes);
            const auto wide_validation =
                validate_gpu_hits(
                    replay.reference_hits,
                    wide_hits);

            rows.push_back({
                replay.name,
                "dda-wide-micro-bvh8",
                replay.workload_id,
                replay.rays.size(),
                cli.iterations,
                wide_validation.mismatches,
                wide_validation.runtime_errors,
                wide_validation.semantic_checksum,
                replay.stream_parse_us,
                replay.replay_convert_us,
                scene_load_us,
                hierarchy_measurement.total_us,
                0.0,
                wide_build_us,
                wide_upload_us,
                ray_upload_us,
                wide_trace_us,
                wide_persistent,
                static_cast<std::size_t>(
                    ray_buffer.allocation_size +
                    wide_hit_buffer
                        .allocation_size),
                64U *
                    sizeof(std::uint32_t),
                wide_payload.nodes.size(),
                wide_payload.max_depth,
            });

            context.destroy_buffer(
                wide_hit_buffer);
            context.destroy_buffer(
                macro_hit_buffer);
            context.destroy_buffer(
                baseline_hit_buffer);
            context.destroy_buffer(ray_buffer);
        }

        context.destroy_buffer(
            wide_hash_buffer);
        context.destroy_buffer(
            wide_order_buffer);
        context.destroy_buffer(
            wide_node_buffer);
        context.destroy_buffer(
            macro_top_buffer);
        context.destroy_buffer(
            macro_order_buffer);
        context.destroy_buffer(
            macro_node_buffer);
        context.destroy_buffer(
            baseline_hash_buffer);
        context.destroy_buffer(
            baseline_order_buffer);
        context.destroy_buffer(
            baseline_node_buffer);
        context.destroy_buffer(
            triangle_buffer);

        write_rows(
            output_root / "b003-stage-a.csv",
            rows);
        write_correctness_json(
            output_root /
                "b003-correctness.json",
            cases,
            rows);
        write_stage_a_summary(
            output_root /
                "b003-stage-a-summary.json",
            rows);
        write_stage_b_summary(
            output_root /
                "b003-stage-b-summary.json",
            rows);

        std::size_t mismatches = 0;
        std::size_t runtime_errors = 0;
        for (const auto& row : rows) {
            mismatches += row.mismatches;
            runtime_errors +=
                row.runtime_errors;
            std::cout
                << std::fixed
                << std::setprecision(3)
                << "case=" << row.workload
                << " candidate="
                << row.candidate
                << " trace_us="
                << row.trace_us
                << " mismatches="
                << row.mismatches
                << " persistent_bytes="
                << row.persistent_bytes
                << '\n';
        }

        constexpr std::size_t kExpectedRows =
            kB002Cases.size() * 3U;
        if (rows.size() != kExpectedRows) {
            std::cerr
                << "B003 candidate gate: FAIL rows="
                << rows.size()
                << " expected="
                << kExpectedRows << '\n';
            return 3;
        }
        if (mismatches != 0 ||
            runtime_errors != 0) {
            std::cerr
                << "B003 correctness: FAIL mismatches="
                << mismatches
                << " runtime_errors="
                << runtime_errors
                << '\n';
            return 2;
        }

        std::cout
            << "B003 correctness: PASS"
            << " macro_nodes="
            << macro_payload.nodes.size()
            << " macro_depth="
            << macro_payload.max_depth
            << " wide_micro_nodes="
            << wide_payload.nodes.size()
            << " wide_micro_depth="
            << wide_payload.max_depth
            << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "B003 error: "
            << error.what()
            << '\n';
        return 1;
    }
}
