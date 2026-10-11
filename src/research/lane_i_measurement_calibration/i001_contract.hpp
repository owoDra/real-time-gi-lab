#pragma once

#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

namespace phos::gi::research::lane_i {

enum class CalibrationVariant {
    Baseline,
    Plus5,
    Plus10,
    Plus20,
};

struct WorkSpec {
    CalibrationVariant variant{CalibrationVariant::Baseline};
    std::uint32_t element_count{};
    std::uint32_t work_iterations{};
    std::uint32_t batch_dispatches{};

    [[nodiscard]] std::uint64_t controlled_work_units() const noexcept;
};

inline constexpr std::uint32_t kBaselineIterations = 200;
inline constexpr std::uint32_t kDefaultElementCount = 8192;
inline constexpr std::uint32_t kDefaultBatchDispatches = 16;

[[nodiscard]] const char* variant_name(CalibrationVariant variant) noexcept;
[[nodiscard]] CalibrationVariant parse_variant(std::string_view value);
[[nodiscard]] std::uint32_t work_iterations(CalibrationVariant variant) noexcept;
[[nodiscard]] WorkSpec make_work_spec(
    CalibrationVariant variant,
    std::uint32_t element_count,
    std::uint32_t batch_dispatches);

[[nodiscard]] std::vector<std::uint32_t> make_input(std::uint32_t element_count);
[[nodiscard]] std::vector<std::uint32_t> make_initial_state(std::uint32_t element_count);
void run_reference_dispatch(
    std::span<const std::uint32_t> input,
    std::span<std::uint32_t> state,
    std::uint32_t work_iterations);
void run_reference_batch(
    std::span<const std::uint32_t> input,
    std::span<std::uint32_t> state,
    std::uint32_t work_iterations,
    std::uint32_t batch_dispatches);
[[nodiscard]] std::uint64_t checksum(std::span<const std::uint32_t> values) noexcept;

} // namespace phos::gi::research::lane_i
