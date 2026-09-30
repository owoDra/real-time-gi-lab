#pragma once
#include "a001_runtime.hpp"
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace phos::gi::lane_a {

struct A001Locality {
    std::uint64_t adjacent_pairs{};
    std::uint64_t same_probe_pairs{};
    std::uint64_t same_cascade_pairs{};
    std::uint64_t neighboring_probe_pairs{};
    std::uint64_t neighboring_tile_pairs{};
    std::uint64_t probe_runs{};
    std::vector<std::uint64_t> items_per_cascade;
};

struct A001Analysis {
    bool visibility_correct{true};
    bool producer_correct{true};
    bool resolve_correct{true};
    std::uint64_t visible_probe_count{};
    float max_resolve_abs_error{};
    A001Locality locality;
    std::vector<std::string> errors;

    [[nodiscard]] bool correct() const {
        return visibility_correct && producer_correct &&
               resolve_correct && errors.empty();
    }
};

A001Analysis analyze_a001(
    const SceneSurfaceSet& scene,
    const A001Settings& settings,
    const A001ParamsGpu& params,
    const A001Readback& readback);

void write_a001_artifacts(
    const std::filesystem::path& output_dir,
    const SceneSurfaceSet& scene,
    const A001Settings& settings,
    const A001ParamsGpu& params,
    const A001Timings& timings,
    const A001Memory& memory,
    const A001Readback& readback,
    const A001Analysis& analysis,
    const std::string& gpu_name,
    const std::string& git_commit);

} // namespace phos::gi::lane_a
