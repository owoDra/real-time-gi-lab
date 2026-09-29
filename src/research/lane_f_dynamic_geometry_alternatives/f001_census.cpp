#include "../lane_a_split_rc/a001_analysis.hpp"
#include "../lane_a_split_rc/a001_runtime.hpp"
#include "../lane_a_split_rc/a001_scene.hpp"
#include "../lane_b_traversal/b002_scene.hpp"
#include "../lane_b_traversal/hierarchical_stratabrick.hpp"
#include "../lane_b_traversal/lane_a_stream_v1.hpp"
#include "../lane_b_traversal/software_bvh.hpp"
#include "vk_context.hpp"

#include <algorithm>
#include <array>
#include <cmath>
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
#include <vector>

namespace lane_a = phos::gi::lane_a;
namespace lane_b = phos::gi::research::lane_b;

namespace {

struct Cli {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    bool validation{};
};

struct MovingSelection {
    std::uint32_t instance_id{};
    std::vector<std::uint32_t> primitives;
    float delta_x{};
    std::uint32_t membership_changes{};
};

struct Distribution {
    double min{};
    double median{};
    double p95{};
    double max{};
    double mean{};
};

Cli parse_cli(int argc, char** argv) {
    Cli cli;
    for (int index = 1; index < argc; ++index) {
        const std::string argument = argv[index];
        if (argument == "--scene") {
            if (index + 1 >= argc) throw std::runtime_error("--scene requires a value");
            cli.scene = argv[++index];
        } else if (argument == "--validation") {
            cli.validation = true;
        } else if (argument == "--help") {
            std::cout << "phos-lane-f-f001-census [--scene path] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error("unknown F001 census argument: " + argument);
        }
    }
    return cli;
}

std::filesystem::path artifact_root() {
    if (const char* value = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
        value != nullptr && *value != '\0') {
        return value;
    }
    return "out/research/lane-f-dynamic-geometry-alternatives/"
           "001-workload-census-baseline-replay/manual-census";
}

std::vector<lane_b::Triangle> translated_geometry(
    const std::vector<lane_b::Triangle>& source,
    std::span<const std::uint32_t> moved,
    float delta_x) {
    auto output = source;
    const lane_b::Vec3 delta{delta_x, 0.0F, 0.0F};
    for (const auto primitive : moved) {
        auto& triangle = output.at(primitive);
        triangle.v0 = triangle.v0 + delta;
        triangle.v1 = triangle.v1 + delta;
        triangle.v2 = triangle.v2 + delta;
    }
    return output;
}

MovingSelection choose_moving_selection(const lane_b::B002Scene& scene) {
    std::uint32_t max_instance = 0U;
    for (const auto& triangle : scene.triangles) {
        if (triangle.instance_id != lane_b::kInvalidId) {
            max_instance = std::max(max_instance, triangle.instance_id);
        }
    }

    std::vector<std::vector<std::uint32_t>> groups(
        std::size_t(max_instance) + 1U);
    for (std::uint32_t primitive = 0U;
         primitive < scene.triangles.size();
         ++primitive) {
        const auto instance = scene.triangles[primitive].instance_id;
        if (instance != lane_b::kInvalidId) {
            groups.at(instance).push_back(primitive);
        }
    }

    std::vector<std::uint32_t> candidates;
    for (std::uint32_t instance = 0U; instance < groups.size(); ++instance) {
        const auto count = groups[instance].size();
        if (count >= 32U && count <= 2048U) candidates.push_back(instance);
    }
    for (std::uint32_t instance = 0U; instance < groups.size(); ++instance) {
        if (!groups[instance].empty() &&
            std::find(candidates.begin(), candidates.end(), instance) ==
                candidates.end()) {
            candidates.push_back(instance);
        }
    }

    const auto segment_size = lane_b::b002_segment_size(scene);
    constexpr std::array<float, 5> multipliers{
        1.25F, 2.5F, 5.0F, 10.0F, 20.0F};
    for (const auto instance : candidates) {
        for (const auto multiplier : multipliers) {
            const auto delta = segment_size * multiplier;
            auto target = translated_geometry(
                scene.triangles, groups[instance], delta);
            lane_b::HierarchicalStrataBrick probe(
                scene.triangles, segment_size);
            const auto stats = probe.update(target, groups[instance]);
            if (stats.membership_changes != 0U) {
                return {
                    instance,
                    groups[instance],
                    delta,
                    static_cast<std::uint32_t>(stats.membership_changes),
                };
            }
        }
    }
    throw std::runtime_error(
        "F001 could not reproduce I001 topology-changing moving selection");
}

Distribution summarize(std::vector<double> values) {
    if (values.empty()) throw std::runtime_error("cannot summarize empty distribution");
    std::sort(values.begin(), values.end());
    const auto n = values.size();
    const auto mid = n / 2U;
    const double median = n % 2U
        ? values[mid]
        : (values[mid - 1U] + values[mid]) * 0.5;
    const auto p95_index = static_cast<std::size_t>(
        std::floor(0.95 * static_cast<double>(n - 1U)));
    const double mean =
        std::accumulate(values.begin(), values.end(), 0.0) /
        static_cast<double>(n);
    return {values.front(), median, values[p95_index], values.back(), mean};
}

double triangle_aspect_ratio(const lane_b::Triangle& triangle) {
    const auto e0 = lane_b::length(triangle.v1 - triangle.v0);
    const auto e1 = lane_b::length(triangle.v2 - triangle.v1);
    const auto e2 = lane_b::length(triangle.v0 - triangle.v2);
    const auto longest = std::max({e0, e1, e2});
    const auto twice_area =
        lane_b::length(lane_b::cross(
            triangle.v1 - triangle.v0,
            triangle.v2 - triangle.v0));
    if (!(twice_area > 1.0e-12F) || !(longest > 0.0F)) {
        return std::numeric_limits<double>::infinity();
    }
    return static_cast<double>(longest) * static_cast<double>(longest) /
           static_cast<double>(twice_area);
}

lane_b::Ray work_item_to_ray(const lane_a::SplitRcWorkItemV1& item) {
    const lane_b::Vec3 raw{item.dir_x, item.dir_y, item.dir_z};
    const auto len = lane_b::length(raw);
    if (!std::isfinite(len) || len <= 1.0e-8F ||
        !std::isfinite(item.interval_min) ||
        !std::isfinite(item.interval_max) ||
        item.interval_min < 0.0F ||
        item.interval_max <= item.interval_min) {
        throw std::runtime_error("F001 encountered invalid A001 ray interval");
    }
    const auto direction = raw / len;
    const lane_b::Vec3 probe{
        item.probe_px, item.probe_py, item.probe_pz};
    return {
        probe + direction * item.interval_min,
        direction,
        item.interval_max - item.interval_min,
    };
}

void write_distribution(std::ostream& out, const Distribution& d, int indent) {
    const std::string pad(static_cast<std::size_t>(indent), ' ');
    out << "{\n"
        << pad << "  \"min\": " << d.min << ",\n"
        << pad << "  \"median\": " << d.median << ",\n"
        << pad << "  \"p95\": " << d.p95 << ",\n"
        << pad << "  \"max\": " << d.max << ",\n"
        << pad << "  \"mean\": " << d.mean << "\n"
        << pad << "}";
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        if (!std::filesystem::exists(cli.scene)) {
            throw std::runtime_error("F001 scene not found: " + cli.scene.string());
        }

        const auto a_scene = lane_a::load_scene_surface_samples(cli.scene);
        const auto b_scene = lane_b::load_b002_scene(cli.scene);
        if (a_scene.samples.size() != b_scene.triangles.size()) {
            throw std::runtime_error("A001/B002 primitive identity count mismatch");
        }

        const auto moving = choose_moving_selection(b_scene);
        const auto target_geometry = translated_geometry(
            b_scene.triangles, moving.primitives, moving.delta_x);

        std::vector<double> aabb_diagonals;
        std::vector<double> aspect_ratios;
        aabb_diagonals.reserve(moving.primitives.size());
        aspect_ratios.reserve(moving.primitives.size());
        lane_b::Aabb dynamic_union{};
        for (const auto primitive : moving.primitives) {
            const auto& triangle = b_scene.triangles.at(primitive);
            const auto bounds = lane_b::triangle_bounds(triangle);
            dynamic_union = lane_b::merge(dynamic_union, bounds);
            aabb_diagonals.push_back(
                static_cast<double>(lane_b::length(bounds.max - bounds.min)));
            aspect_ratios.push_back(triangle_aspect_ratio(triangle));
        }

        lane_a::A001Settings settings;
        settings.case_id = lane_a::A001Case::Static;
        settings.tile_width = 128U;
        settings.tile_height = 72U;
        settings.cascade_count = 4U;
        settings.rays_per_probe = 8U;
        settings.frame_id = 0U;
        const auto params = lane_a::build_a001_params(a_scene, settings);

        phos::gi::VulkanContext vk(cli.validation);
        std::cout << "GPU: " << vk.device_name() << '\n';
        lane_a::A001Runtime runtime(vk, a_scene, params);
        (void)runtime.measure(1U);
        const auto readback = runtime.readback();
        const auto analysis = lane_a::analyze_a001(
            a_scene, settings, params, readback);
        if (!analysis.correct()) {
            throw std::runtime_error("F001 A001 census stream failed producer correctness");
        }

        const auto workload_id = lane_b::lane_a_workload_id(
            readback.work_items.data(),
            readback.work_items.size() * sizeof(lane_a::SplitRcWorkItemV1));

        std::vector<double> tmax_values;
        tmax_values.reserve(readback.work_items.size());
        std::vector<lane_b::Ray> rays;
        rays.reserve(readback.work_items.size());
        for (const auto& item : readback.work_items) {
            auto ray = work_item_to_ray(item);
            tmax_values.push_back(ray.t_max);
            rays.push_back(ray);
        }

        lane_b::SoftwareBvh source_bvh(b_scene.triangles);
        lane_b::SoftwareBvh target_bvh(target_geometry);
        std::vector<std::uint8_t> moved_mask(b_scene.triangles.size(), 0U);
        for (const auto primitive : moving.primitives) moved_mask.at(primitive) = 1U;

        std::size_t source_dynamic_hits = 0U;
        std::size_t target_dynamic_hits = 0U;
        std::size_t source_hits = 0U;
        std::size_t target_hits = 0U;
        for (const auto& ray : rays) {
            const auto source_hit = source_bvh.trace(ray);
            if (source_hit.hit) {
                ++source_hits;
                if (moved_mask.at(source_hit.primitive_id) != 0U) ++source_dynamic_hits;
            }
            const auto target_hit = target_bvh.trace(ray);
            if (target_hit.hit) {
                ++target_hits;
                if (moved_mask.at(target_hit.primitive_id) != 0U) ++target_dynamic_hits;
            }
        }

        const auto aabb_stats = summarize(std::move(aabb_diagonals));
        const auto aspect_stats = summarize(std::move(aspect_ratios));
        const auto tmax_stats = summarize(std::move(tmax_values));
        const auto dynamic_extent = dynamic_union.max - dynamic_union.min;

        const auto root = artifact_root();
        std::filesystem::create_directories(root);
        std::ofstream out(root / "f001-census.json");
        if (!out) throw std::runtime_error("cannot create f001-census.json");
        out << std::fixed << std::setprecision(9)
            << "{\n"
            << "  \"schema_version\": 1,\n"
            << "  \"plan_version\": \"lane-f-plan-v1\",\n"
            << "  \"scene\": \"" << cli.scene.string() << "\",\n"
            << "  \"device\": \"" << vk.device_name() << "\",\n"
            << "  \"validation\": " << (cli.validation ? "true" : "false") << ",\n"
            << "  \"triangle_count\": " << b_scene.triangles.size() << ",\n"
            << "  \"dynamic_object_count\": 1,\n"
            << "  \"dynamic_instance_id\": " << moving.instance_id << ",\n"
            << "  \"dynamic_primitive_count\": " << moving.primitives.size() << ",\n"
            << "  \"moved_primitive_count\": " << moving.primitives.size() << ",\n"
            << "  \"deformed_primitive_count\": 0,\n"
            << "  \"topology_delta_count\": 0,\n"
            << "  \"membership_changes\": " << moving.membership_changes << ",\n"
            << "  \"displacement_magnitude\": " << std::abs(moving.delta_x) << ",\n"
            << "  \"dynamic_union_extent\": ["
            << dynamic_extent.x << ", " << dynamic_extent.y << ", " << dynamic_extent.z << "],\n"
            << "  \"dynamic_triangle_aabb_diagonal\": ";
        write_distribution(out, aabb_stats, 2);
        out << ",\n  \"triangle_aspect_ratio\": ";
        write_distribution(out, aspect_stats, 2);
        out << ",\n"
            << "  \"ray_count\": " << rays.size() << ",\n"
            << "  \"source_workload_id\": " << workload_id << ",\n"
            << "  \"ray_t_max\": ";
        write_distribution(out, tmax_stats, 2);
        out << ",\n"
            << "  \"source_hit_rays\": " << source_hits << ",\n"
            << "  \"source_dynamic_hit_rays\": " << source_dynamic_hits << ",\n"
            << "  \"source_dynamic_hit_fraction\": "
            << (rays.empty() ? 0.0 : static_cast<double>(source_dynamic_hits) / rays.size()) << ",\n"
            << "  \"target_hit_rays\": " << target_hits << ",\n"
            << "  \"target_dynamic_hit_rays\": " << target_dynamic_hits << ",\n"
            << "  \"target_dynamic_hit_fraction\": "
            << (rays.empty() ? 0.0 : static_cast<double>(target_dynamic_hits) / rays.size()) << ",\n"
            << "  \"visible_probe_count\": " << analysis.visible_probe_count << "\n"
            << "}\n";

        std::cout
            << "F001 census: primitives=" << moving.primitives.size()
            << " instance=" << moving.instance_id
            << " displacement=" << moving.delta_x
            << " membership_changes=" << moving.membership_changes
            << " rays=" << rays.size()
            << " target_dynamic_hit_fraction="
            << (rays.empty() ? 0.0 : static_cast<double>(target_dynamic_hits) / rays.size())
            << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "F001 census error: " << error.what() << '\n';
        return 1;
    }
}
