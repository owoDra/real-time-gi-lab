#include "f002_lbvh_runtime.hpp"

#include "../lane_b_traversal/b002_scene.hpp"
#include "../lane_b_traversal/hierarchical_stratabrick.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <span>
#include <stdexcept>
#include <string>
#include <vector>

namespace lane_b = phos::gi::research::lane_b;
namespace lane_f = phos::gi::research::lane_f;

namespace {

struct Cli {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    std::filesystem::path output{"f002-process.csv"};
    std::filesystem::path device_output{"f002-device.json"};
    std::uint32_t warmup_builds{10U};
    std::uint32_t measured_builds{100U};
    bool validation{};
};

struct MovingSelection {
    std::uint32_t instance_id{};
    std::vector<std::uint32_t> primitives;
    float delta_x{};
    std::uint32_t membership_changes{};
};

Cli parse_cli(int argc, char** argv) {
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
        } else if (argument == "--output") {
            cli.output = value("--output");
        } else if (argument == "--device-output") {
            cli.device_output = value("--device-output");
        } else if (argument == "--warmup-builds") {
            cli.warmup_builds = static_cast<std::uint32_t>(
                std::stoul(value("--warmup-builds")));
        } else if (argument == "--measured-builds") {
            cli.measured_builds = static_cast<std::uint32_t>(
                std::stoul(value("--measured-builds")));
        } else if (argument == "--validation") {
            cli.validation = true;
        } else if (argument == "--help") {
            std::cout
                << "phos-lane-f-f002-lbvh "
                   "[--scene path] [--output csv] [--device-output json] "
                   "[--warmup-builds N] [--measured-builds N] [--validation]\n";
            std::exit(0);
        } else {
            throw std::runtime_error(
                "unknown F002 argument: " + argument);
        }
    }
    if (cli.warmup_builds == 0U || cli.measured_builds == 0U) {
        throw std::runtime_error(
            "F002 warmup/measured build counts must be positive");
    }
    return cli;
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
        if (count >= 32U && count <= 2048U) {
            candidates.push_back(instance);
        }
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
                scene.triangles,
                groups[instance],
                delta);
            lane_b::HierarchicalStrataBrick probe(
                scene.triangles,
                segment_size);
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
        "F002 could not reproduce F001/I001 moving selection");
}

std::string json_escape(const std::string& value) {
    std::string result;
    result.reserve(value.size());
    for (const char c : value) {
        switch (c) {
        case '\\': result += "\\\\"; break;
        case '"': result += "\\\""; break;
        case '\n': result += "\\n"; break;
        case '\r': result += "\\r"; break;
        case '\t': result += "\\t"; break;
        default: result += c; break;
        }
    }
    return result;
}

double sample_median(
    const std::vector<lane_f::F002BuildSample>& samples,
    double lane_f::F002BuildSample::*field) {
    std::vector<double> values;
    values.reserve(samples.size());
    for (const auto& sample : samples) {
        values.push_back(sample.*field);
    }
    return lane_f::f002_median(std::move(values));
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto cli = parse_cli(argc, argv);
        if (!std::filesystem::exists(cli.scene)) {
            throw std::runtime_error(
                "F002 scene not found: " + cli.scene.string());
        }

        const auto scene = lane_b::load_b002_scene(cli.scene);
        const auto moving = choose_moving_selection(scene);
        const auto target = translated_geometry(
            scene.triangles,
            moving.primitives,
            moving.delta_x);

        std::vector<lane_b::GpuTriangle> template_triangles;
        template_triangles.reserve(moving.primitives.size());
        lane_b::Aabb template_bounds{};
        for (const auto primitive : moving.primitives) {
            const auto& triangle = target.at(primitive);
            template_triangles.push_back(
                lane_b::to_gpu_triangle(triangle));
            template_bounds = lane_b::merge(
                template_bounds,
                lane_b::triangle_bounds(triangle));
        }
        if (template_triangles.size() < 2U) {
            throw std::runtime_error(
                "F002 representative dynamic subset is too small");
        }

        const auto nrep =
            static_cast<std::uint32_t>(template_triangles.size());
        std::set<std::uint32_t> sizes{
            1000U,
            4000U,
            16000U,
            64000U,
            256000U,
            1000000U,
            nrep,
        };

        const float page_extent = lane_b::b002_segment_size(scene);
        const lane_b::Vec3 origin{
            template_bounds.min.x - 2.0F * page_extent,
            template_bounds.min.y - 2.0F * page_extent,
            template_bounds.min.z - 2.0F * page_extent,
        };

        lane_b::B002VulkanContext context(
            cli.validation,
            lane_b::kB002TargetDeviceName,
            false);
        std::cout << "GPU: " << context.device_name() << '\n';
        std::cout
            << "F002 Nrep=" << nrep
            << " instance=" << moving.instance_id
            << " displacement=" << moving.delta_x
            << " membership_changes=" << moving.membership_changes
            << " page_extent=" << page_extent << '\n';

#ifndef PHOS_GI_LANE_F_SHADER_DIR
#error PHOS_GI_LANE_F_SHADER_DIR must be defined
#endif
        const std::filesystem::path shader =
            std::filesystem::path(PHOS_GI_LANE_F_SHADER_DIR) /
            "lane_f_f002_lbvh.spv";

        std::filesystem::create_directories(
            cli.output.parent_path().empty()
                ? std::filesystem::path(".")
                : cli.output.parent_path());
        std::ofstream out(cli.output);
        if (!out) {
            throw std::runtime_error(
                "cannot create F002 process CSV");
        }
        out << std::fixed << std::setprecision(6);
        out
            << "primitive_count,is_nrep,warmup_builds,measured_builds,"
               "reset_us,input_us,aabb_us,morton_us,sort_us,topology_us,"
               "bounds_us,builder_gpu_us,builder_min_us,builder_max_us,"
               "template_bytes,working_geometry_bytes,aabb_bytes,key_bytes,"
               "histogram_bytes,prefix_bytes,node_bytes,ready_bytes,"
               "peak_builder_bytes,sort_mismatches,root_count_mismatches,"
               "root_bounds_mismatches,validation_passed\n";

        bool all_valid = true;
        for (const auto size : sizes) {
            lane_f::F002LbvhBuilder builder(
                context,
                template_triangles,
                size,
                origin,
                page_extent,
                shader);
            const auto samples = builder.measure(
                cli.warmup_builds,
                cli.measured_builds);
            const auto validation = builder.validate();
            const auto memory = builder.memory();
            all_valid = all_valid && validation.passed();

            std::vector<double> totals;
            totals.reserve(samples.size());
            for (const auto& sample : samples) {
                totals.push_back(sample.total_us);
            }
            const auto [minimum, maximum] =
                std::minmax_element(totals.begin(), totals.end());

            const auto total_median =
                lane_f::f002_median(totals);
            out
                << size << ','
                << (size == nrep ? 1 : 0) << ','
                << cli.warmup_builds << ','
                << cli.measured_builds << ','
                << sample_median(samples, &lane_f::F002BuildSample::reset_us) << ','
                << sample_median(samples, &lane_f::F002BuildSample::input_us) << ','
                << sample_median(samples, &lane_f::F002BuildSample::aabb_us) << ','
                << sample_median(samples, &lane_f::F002BuildSample::morton_us) << ','
                << sample_median(samples, &lane_f::F002BuildSample::sort_us) << ','
                << sample_median(samples, &lane_f::F002BuildSample::topology_us) << ','
                << sample_median(samples, &lane_f::F002BuildSample::bounds_us) << ','
                << total_median << ','
                << *minimum << ','
                << *maximum << ','
                << memory.template_bytes << ','
                << memory.working_geometry_bytes << ','
                << memory.aabb_bytes << ','
                << memory.key_bytes << ','
                << memory.histogram_bytes << ','
                << memory.prefix_bytes << ','
                << memory.node_bytes << ','
                << memory.ready_bytes << ','
                << memory.total_bytes() << ','
                << validation.sort_mismatches << ','
                << validation.root_count_mismatches << ','
                << validation.root_bounds_mismatches << ','
                << (validation.passed() ? 1 : 0)
                << '\n';

            std::cout
                << "F002 size=" << size
                << (size == nrep ? " [Nrep]" : "")
                << " builder_median_us=" << total_median
                << " valid=" << (validation.passed() ? "yes" : "no")
                << '\n';
        }

        std::filesystem::create_directories(
            cli.device_output.parent_path().empty()
                ? std::filesystem::path(".")
                : cli.device_output.parent_path());
        std::ofstream device(cli.device_output);
        if (!device) {
            throw std::runtime_error(
                "cannot create F002 device JSON");
        }
        const auto api = context.api_version();
        device
            << "{\n"
            << "  \"device\": \"" << json_escape(context.device_name()) << "\",\n"
            << "  \"driver_name\": \"" << json_escape(context.driver_name()) << "\",\n"
            << "  \"driver_info\": \"" << json_escape(context.driver_info()) << "\",\n"
            << "  \"api_version_raw\": " << api << ",\n"
            << "  \"api_version\": \""
            << VK_VERSION_MAJOR(api) << '.'
            << VK_VERSION_MINOR(api) << '.'
            << VK_VERSION_PATCH(api) << "\",\n"
            << "  \"validation\": " << (cli.validation ? "true" : "false") << ",\n"
            << "  \"nrep\": " << nrep << ",\n"
            << "  \"dynamic_instance_id\": " << moving.instance_id << ",\n"
            << "  \"displacement\": " << moving.delta_x << ",\n"
            << "  \"page_extent\": " << page_extent << "\n"
            << "}\n";

        if (!all_valid) {
            std::cerr
                << "F002 structural validation failed; timing is not accepted\n";
            return 3;
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "F002 error: " << error.what() << '\n';
        return 1;
    }
}
