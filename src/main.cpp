#include "cache_benchmark.hpp"
#include "scene_workload.hpp"
#include "vk_context.hpp"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace phos::gi;

int main(int argc, char** argv) {
    try {
        std::filesystem::path scene =
            "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf";
        std::size_t query_count = 4'000'000;
        std::uint32_t iterations = 100;
        bool synthetic = false;
        bool validation = false;

        for (int i = 1; i < argc; ++i) {
            const std::string arg = argv[i];
            if (arg == "--scene" && i + 1 < argc) {
                scene = argv[++i];
            } else if (arg == "--queries" && i + 1 < argc) {
                query_count = std::stoull(argv[++i]);
            } else if (arg == "--iterations" && i + 1 < argc) {
                iterations = static_cast<std::uint32_t>(std::stoul(argv[++i]));
            } else if (arg == "--synthetic") {
                synthetic = true;
            } else if (arg == "--validation") {
                validation = true;
            } else if (arg == "--help") {
                std::cout
                    << "phos-gi-lab [--scene path] [--queries N] [--iterations N] "
                       "[--synthetic] [--validation]\n";
                return 0;
            }
        }

        std::vector<Vec3> points;
        if (!synthetic && std::filesystem::exists(scene)) {
            std::cerr << "Loading Sponza surface workload: " << scene << "\n";
            points = load_surface_points(scene);
        } else {
            std::cerr << "Using synthetic surface workload\n";
            points = make_synthetic_surface_points(500'000);
        }
        std::cerr << "Surface samples: " << points.size() << "\n";

        auto workload = build_workload(points, query_count);
        std::cerr
            << "Queries: " << workload.original.size()
            << ", pages: " << workload.page_table.size()
            << ", active cells: " << workload.active_cells
            << ", hash slots: " << workload.hash_keys.size()
            << ", hash max probe: " << workload.hash_max_probe
            << "\n";

        VulkanContext vk(validation);
        std::cerr << "GPU: " << vk.device_name() << "\n";

        CacheBenchmark bench(vk);
        auto results = bench.run(workload, iterations);

        std::cout
            << "variant,queries,pages,bytes,gpu_us_per_dispatch,"
               "checksum,expected_checksum,correct\n";

        bool all_correct = true;
        for (const auto& r : results) {
            std::cout
                << r.variant << ','
                << r.queries << ','
                << r.pages << ','
                << r.bytes << ','
                << r.gpu_us_per_dispatch << ','
                << r.checksum << ','
                << r.expected_checksum << ','
                << (r.correct ? "true" : "false")
                << '\n';
            all_correct = all_correct && r.correct;
        }

        if (!all_correct) {
            std::cerr
                << "fatal: benchmark correctness guard failed; "
                   "cache variants returned different semantic payloads\n";
            return 2;
        }

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "fatal: " << e.what() << '\n';
        return 1;
    }
}
