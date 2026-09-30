#include "k001_contract.hpp"

#include <limits>
#include <stdexcept>
#include <string>

namespace phos::gi::research::lane_k {
namespace {

[[nodiscard]] bool is_power_of_two(std::uint32_t value) noexcept {
    return value != 0U && (value & (value - 1U)) == 0U;
}

[[nodiscard]] std::uint32_t seed_word(std::uint32_t index, std::uint32_t salt) noexcept {
    std::uint32_t value = index + salt + 0x9e3779b9U;
    value ^= value >> 16U;
    value *= 0x7feb352dU;
    value ^= value >> 15U;
    value *= 0x846ca68bU;
    value ^= value >> 16U;
    return value;
}

} // namespace

std::uint64_t WorkSpec::controlled_work_units() const noexcept {
    return static_cast<std::uint64_t>(element_count) *
           static_cast<std::uint64_t>(work_iterations) *
           static_cast<std::uint64_t>(batch_dispatches);
}

const char* variant_name(CalibrationVariant variant) noexcept {
    switch (variant) {
    case CalibrationVariant::Baseline: return "baseline";
    case CalibrationVariant::Plus5: return "plus5";
    case CalibrationVariant::Plus10: return "plus10";
    case CalibrationVariant::Plus20: return "plus20";
    }
    return "unknown";
}

CalibrationVariant parse_variant(std::string_view value) {
    if (value == "baseline") return CalibrationVariant::Baseline;
    if (value == "plus5") return CalibrationVariant::Plus5;
    if (value == "plus10") return CalibrationVariant::Plus10;
    if (value == "plus20") return CalibrationVariant::Plus20;
    throw std::runtime_error("unknown Lane K calibration variant: " + std::string(value));
}

std::uint32_t work_iterations(CalibrationVariant variant) noexcept {
    switch (variant) {
    case CalibrationVariant::Baseline: return 200U;
    case CalibrationVariant::Plus5: return 210U;
    case CalibrationVariant::Plus10: return 220U;
    case CalibrationVariant::Plus20: return 240U;
    }
    return 0U;
}

WorkSpec make_work_spec(
    CalibrationVariant variant,
    std::uint32_t element_count,
    std::uint32_t batch_dispatches) {
    if (!is_power_of_two(element_count)) {
        throw std::runtime_error("Lane K element count must be a non-zero power of two");
    }
    if (batch_dispatches == 0U) {
        throw std::runtime_error("Lane K batch dispatch count must be positive");
    }
    const auto iterations = work_iterations(variant);
    if (iterations == 0U) {
        throw std::runtime_error("Lane K variant has no declared work iteration count");
    }
    return {variant, element_count, iterations, batch_dispatches};
}

std::vector<std::uint32_t> make_input(std::uint32_t element_count) {
    if (!is_power_of_two(element_count)) {
        throw std::runtime_error("Lane K input size must be a non-zero power of two");
    }
    std::vector<std::uint32_t> values(element_count);
    for (std::uint32_t index = 0; index < element_count; ++index) {
        values[index] = seed_word(index, 0x13579bdfU);
    }
    return values;
}

std::vector<std::uint32_t> make_initial_state(std::uint32_t element_count) {
    if (!is_power_of_two(element_count)) {
        throw std::runtime_error("Lane K state size must be a non-zero power of two");
    }
    std::vector<std::uint32_t> values(element_count);
    for (std::uint32_t index = 0; index < element_count; ++index) {
        values[index] = seed_word(index, 0x2468ace0U);
    }
    return values;
}

void run_reference_dispatch(
    std::span<const std::uint32_t> input,
    std::span<std::uint32_t> state,
    std::uint32_t iterations) {
    if (input.size() != state.size() || input.empty()) {
        throw std::runtime_error("Lane K reference buffers must be equal and non-zero");
    }
    if (input.size() > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("Lane K reference buffer is too large");
    }
    if (!is_power_of_two(static_cast<std::uint32_t>(input.size()))) {
        throw std::runtime_error("Lane K reference buffer size must be a power of two");
    }
    const auto mask = static_cast<std::uint32_t>(input.size() - 1U);
    for (std::uint32_t index = 0; index < state.size(); ++index) {
        std::uint32_t value = state[index] ^ (index * 0x85ebca6bU);
        for (std::uint32_t iteration = 0; iteration < iterations; ++iteration) {
            const std::uint32_t source_index =
                (value ^ (iteration * 0x9e3779b9U) ^ (index * 0xc2b2ae35U)) & mask;
            const std::uint32_t source = input[source_index];
            value ^= source + 0x9e3779b9U + (value << 6U) + (value >> 2U);
            value = value * 1664525U + 1013904223U;
        }
        state[index] = value;
    }
}

void run_reference_batch(
    std::span<const std::uint32_t> input,
    std::span<std::uint32_t> state,
    std::uint32_t iterations,
    std::uint32_t batch_dispatches) {
    if (batch_dispatches == 0U) {
        throw std::runtime_error("Lane K reference batch must contain at least one dispatch");
    }
    for (std::uint32_t dispatch = 0; dispatch < batch_dispatches; ++dispatch) {
        run_reference_dispatch(input, state, iterations);
    }
}

std::uint64_t checksum(std::span<const std::uint32_t> values) noexcept {
    std::uint64_t hash = 1469598103934665603ULL;
    for (const auto value : values) {
        hash ^= static_cast<std::uint64_t>(value);
        hash *= 1099511628211ULL;
    }
    return hash;
}

} // namespace phos::gi::research::lane_k
