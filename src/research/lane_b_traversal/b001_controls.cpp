#include "software_bvh.hpp"
#include "sparse_grid.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <optional>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace lane = phos::gi::research::lane_b;
using Clock = std::chrono::steady_clock;

namespace {

constexpr lane::Vec3 kDynamicDelta{1.25F, 0.65F, -0.8F};

struct Row {
    std::string scene;
    std::string dynamic;
    std::string camera;
    std::string candidate;
    float tmax{};
    std::size_t triangles{};
    std::size_t rays{};
    int repeats{};
    std::size_t mismatches{};
    std::size_t persistent{};
    std::size_t scratch{};
    double build{};
    double refit{};
    double rebuild{};
    double update{};
    double trace{};
};

struct Args {
    std::size_t rays{2048};
    int repeats{3};
};

[[nodiscard]] double elapsed_us(Clock::time_point start) {
    return std::chrono::duration<double, std::micro>(Clock::now() - start).count();
}

[[nodiscard]] double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    const auto middle = values.size() / 2;
    return values.size() % 2 != 0
        ? values[middle]
        : (values[middle - 1] + values[middle]) * 0.5;
}

template <class Fn>
[[nodiscard]] double measure(int repeats, Fn&& fn) {
    std::vector<double> samples;
    samples.reserve(static_cast<std::size_t>(repeats));
    for (int repeat = 0; repeat < repeats; ++repeat) {
        const auto start = Clock::now();
        fn();
        samples.push_back(elapsed_us(start));
    }
    return median(std::move(samples));
}

template <class Acceleration>
[[nodiscard]] double measure_construction(
    const std::vector<lane::Triangle>& geometry,
    int repeats) {
    std::vector<double> samples;
    samples.reserve(static_cast<std::size_t>(repeats));
    for (int repeat = 0; repeat < repeats; ++repeat) {
        std::optional<Acceleration> candidate;
        const auto start = Clock::now();
        candidate.emplace(geometry);
        samples.push_back(elapsed_us(start));

        // Keep construction observable without charging destruction to build/rebuild.
        volatile auto bytes = candidate->persistent_bytes();
        (void)bytes;
    }
    return median(std::move(samples));
}

void consume(const lane::Hit& hit) {
    static volatile std::uint64_t sink = 0;
    sink = sink ^ std::uint64_t(hit.primitive_id) ^ std::uint64_t(hit.hit);
}

void contract_smoke_tests() {
    std::vector<lane::Triangle> triangles{
        {{-1, -1, 5}, {1, -1, 5}, {0, 1, 5}, 3, 7, 11, true},
    };

    const auto normalized = lane::trace_reference(
        triangles,
        {{0, 0, 0}, {0, 0, 2}, 10});
    if (!normalized.hit ||
        std::abs(normalized.t - 5.0F) > lane::kHitDistanceAbsTolerance ||
        normalized.primitive_id != 3) {
        throw std::runtime_error("contract normalization failed");
    }

    if (lane::trace_reference(
            triangles,
            {{0, 0, 0}, {0, 0, 1}, 4.9F})
            .hit) {
        throw std::runtime_error("contract tMax failed");
    }

    triangles[0].two_sided = false;
    if (lane::trace_reference(
            triangles,
            {{0, 0, 0}, {0, 0, 1}, 10})
            .hit) {
        throw std::runtime_error("contract face policy failed");
    }

    triangles[0].two_sided = true;
    triangles.push_back(triangles[0]);
    triangles.back().primitive_id = 1;
    if (lane::trace_reference(
            triangles,
            {{0, 0, 0}, {0, 0, 1}, 10})
            .primitive_id != 1) {
        throw std::runtime_error("contract tie break failed");
    }
}

template <class Acceleration>
[[nodiscard]] std::size_t validate(
    const std::vector<lane::Triangle>& triangles,
    const Acceleration& acceleration,
    std::span<const lane::Ray> rays) {
    std::size_t mismatches = 0;
    for (const auto ray : rays) {
        const auto expected = lane::trace_reference(triangles, ray);
        const auto actual = acceleration.trace(ray);
        if (!lane::equivalent_hit(expected, actual)) {
            ++mismatches;
        }
    }
    return mismatches;
}

template <class Acceleration>
[[nodiscard]] double trace_time(
    const Acceleration& acceleration,
    std::span<const lane::Ray> rays,
    int repeats) {
    return measure(repeats, [&] {
        for (const auto ray : rays) {
            consume(acceleration.trace(ray));
        }
    });
}

[[nodiscard]] double measure_common_geometry_update(
    const lane::Scene& source,
    int repeats) {
    std::vector<double> samples;
    samples.reserve(static_cast<std::size_t>(repeats));
    for (int repeat = 0; repeat < repeats; ++repeat) {
        auto geometry = source.triangles;
        const auto start = Clock::now();
        lane::translate(geometry, source.moving, kDynamicDelta);
        samples.push_back(elapsed_us(start));
    }
    return median(std::move(samples));
}

[[nodiscard]] double measure_bvh_refit(
    const lane::Scene& source,
    const std::vector<lane::Triangle>& final_geometry,
    int repeats) {
    std::vector<double> samples;
    samples.reserve(static_cast<std::size_t>(repeats));
    for (int repeat = 0; repeat < repeats; ++repeat) {
        lane::SoftwareBvh candidate(source.triangles);
        const auto start = Clock::now();
        candidate.refit(final_geometry);
        samples.push_back(elapsed_us(start));
    }
    return median(std::move(samples));
}

[[nodiscard]] double measure_grid_update(
    const lane::Scene& source,
    const std::vector<lane::Triangle>& final_geometry,
    int repeats) {
    std::vector<double> samples;
    samples.reserve(static_cast<std::size_t>(repeats));
    for (int repeat = 0; repeat < repeats; ++repeat) {
        lane::SparseGrid candidate(source.triangles);
        const auto start = Clock::now();
        candidate.update(final_geometry, source.moving);
        samples.push_back(elapsed_us(start));
    }
    return median(std::move(samples));
}

[[nodiscard]] Row run_bvh(
    const lane::Scene& source,
    std::span<const lane::Ray> rays,
    bool dynamic,
    bool shifted_camera,
    float tmax,
    int repeats) {
    const double build =
        measure_construction<lane::SoftwareBvh>(source.triangles, repeats);

    auto final_geometry = source.triangles;
    lane::SoftwareBvh final_bvh(final_geometry);

    double refit = 0.0;
    double update = 0.0;
    if (dynamic) {
        update = measure_common_geometry_update(source, repeats);
        lane::translate(final_geometry, source.moving, kDynamicDelta);
        refit = measure_bvh_refit(source, final_geometry, repeats);
        final_bvh.refit(final_geometry);
    }

    const double rebuild =
        measure_construction<lane::SoftwareBvh>(final_geometry, repeats);

    return {
        source.name,
        dynamic ? "moving" : "static",
        shifted_camera ? "shifted" : "static",
        "software-bvh",
        tmax,
        final_geometry.size(),
        rays.size(),
        repeats,
        validate(final_geometry, final_bvh, rays),
        final_bvh.persistent_bytes(),
        final_bvh.scratch_bytes(),
        build,
        refit,
        rebuild,
        update,
        trace_time(final_bvh, rays, repeats),
    };
}

[[nodiscard]] Row run_grid(
    const lane::Scene& source,
    std::span<const lane::Ray> rays,
    bool dynamic,
    bool shifted_camera,
    float tmax,
    int repeats) {
    const double build =
        measure_construction<lane::SparseGrid>(source.triangles, repeats);

    auto final_geometry = source.triangles;
    lane::SparseGrid final_grid(final_geometry);

    double membership_update = 0.0;
    double common_update = 0.0;
    if (dynamic) {
        common_update = measure_common_geometry_update(source, repeats);
        lane::translate(final_geometry, source.moving, kDynamicDelta);
        membership_update =
            measure_grid_update(source, final_geometry, repeats);
        final_grid.update(final_geometry, source.moving);
    }

    const double rebuild =
        measure_construction<lane::SparseGrid>(final_geometry, repeats);

    // dynamic_update_us is the common moved-geometry update plus candidate-specific
    // membership maintenance. Refit remains a separate field for BVH-style candidates.
    const double dynamic_update = common_update + membership_update;

    return {
        source.name,
        dynamic ? "moving" : "static",
        shifted_camera ? "shifted" : "static",
        "stratabrick-grid-control",
        tmax,
        final_geometry.size(),
        rays.size(),
        repeats,
        validate(final_geometry, final_grid, rays),
        final_grid.persistent_bytes(),
        final_grid.scratch_bytes(),
        build,
        0.0,
        rebuild,
        dynamic_update,
        trace_time(final_grid, rays, repeats),
    };
}

void write_csv(std::ostream& output, const std::vector<Row>& rows) {
    output
        << "scene,dynamic,camera,t_max,candidate,triangles,rays,repeats,mismatches,"
           "build_us,refit_us,rebuild_us,dynamic_update_us,trace_us,"
           "persistent_bytes,scratch_bytes\n";
    output << std::fixed << std::setprecision(3);

    for (const auto& row : rows) {
        output << row.scene << ',' << row.dynamic << ',' << row.camera << ','
               << row.tmax << ',' << row.candidate << ',' << row.triangles << ','
               << row.rays << ',' << row.repeats << ',' << row.mismatches << ','
               << row.build << ',' << row.refit << ',' << row.rebuild << ','
               << row.update << ',' << row.trace << ',' << row.persistent << ','
               << row.scratch << '\n';
    }
}

[[nodiscard]] Args parse_args(int argc, char** argv) {
    Args parsed;
    for (int index = 1; index < argc; ++index) {
        const std::string_view option = argv[index];
        if (++index >= argc) {
            throw std::runtime_error("option requires value");
        }
        if (option == "--rays") {
            parsed.rays = std::stoull(argv[index]);
        } else if (option == "--repeats") {
            parsed.repeats = std::stoi(argv[index]);
        } else {
            throw std::runtime_error("unknown option");
        }
    }
    if (parsed.rays == 0 || parsed.repeats <= 0) {
        throw std::runtime_error("rays/repeats must be positive");
    }
    return parsed;
}

} // namespace

int main(int argc, char** argv) {
    try {
        contract_smoke_tests();
        const auto args = parse_args(argc, argv);
        std::vector<Row> rows;

        for (const std::string_view scene_name : {"sparse", "dense", "vertical"}) {
            const auto scene = lane::make_scene(scene_name);
            for (const bool dynamic : {false, true}) {
                for (const bool shifted_camera : {false, true}) {
                    for (const float tmax : {50.0F, 200.0F}) {
                        const auto rays = lane::make_rays(
                            scene_name,
                            args.rays,
                            tmax,
                            shifted_camera);
                        rows.push_back(run_bvh(
                            scene,
                            rays,
                            dynamic,
                            shifted_camera,
                            tmax,
                            args.repeats));
                        rows.push_back(run_grid(
                            scene,
                            rays,
                            dynamic,
                            shifted_camera,
                            tmax,
                            args.repeats));
                    }
                }
            }
        }

        write_csv(std::cout, rows);
        if (const char* artifact_dir = std::getenv("PHOS_RESEARCH_ARTIFACT_DIR");
            artifact_dir != nullptr && *artifact_dir != '\0') {
            std::ofstream artifact(std::string(artifact_dir) + "/b001-controls.csv");
            if (!artifact) {
                throw std::runtime_error("artifact open failed");
            }
            write_csv(artifact, rows);
        }

        const auto mismatches = std::accumulate(
            rows.begin(),
            rows.end(),
            std::size_t{},
            [](std::size_t total, const Row& row) {
                return total + row.mismatches;
            });
        if (mismatches != 0) {
            std::cerr << "correctness mismatches: " << mismatches << '\n';
            return 2;
        }

        std::cerr << "B001 correctness: PASS (" << rows.size()
                  << " candidate rows)\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "B001 error: " << error.what() << '\n';
        return 1;
    }
}
