#include "i001_contract.hpp"

#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace phos::gi::research::lane_i;

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

} // namespace

int main() {
    try {
        const auto base = make_work_spec(CalibrationVariant::Baseline, 1024U, 8U);
        const auto p5 = make_work_spec(CalibrationVariant::Plus5, 1024U, 8U);
        const auto p10 = make_work_spec(CalibrationVariant::Plus10, 1024U, 8U);
        const auto p20 = make_work_spec(CalibrationVariant::Plus20, 1024U, 8U);

        require(base.work_iterations == 200U, "baseline iteration count");
        require(p5.work_iterations == 210U, "plus5 iteration count");
        require(p10.work_iterations == 220U, "plus10 iteration count");
        require(p20.work_iterations == 240U, "plus20 iteration count");
        require(
            p5.controlled_work_units() * 100ULL ==
                base.controlled_work_units() * 105ULL,
            "plus5 work ratio");
        require(
            p10.controlled_work_units() * 100ULL ==
                base.controlled_work_units() * 110ULL,
            "plus10 work ratio");
        require(
            p20.controlled_work_units() * 100ULL ==
                base.controlled_work_units() * 120ULL,
            "plus20 work ratio");

        const auto input = make_input(1024U);
        const auto initial = make_initial_state(1024U);
        std::array<std::uint64_t, 4> sums{};
        const std::array variants{
            CalibrationVariant::Baseline,
            CalibrationVariant::Plus5,
            CalibrationVariant::Plus10,
            CalibrationVariant::Plus20,
        };
        for (std::size_t i = 0; i < variants.size(); ++i) {
            auto state = initial;
            run_reference_batch(input, state, work_iterations(variants[i]), 2U);
            sums[i] = checksum(state);
        }
        for (std::size_t i = 0; i < sums.size(); ++i) {
            require(sums[i] != 0ULL, "reference checksum must be non-zero");
            for (std::size_t j = i + 1; j < sums.size(); ++j) {
                require(sums[i] != sums[j], "variant checksums must differ");
            }
        }

        bool rejected = false;
        try {
            (void)make_work_spec(CalibrationVariant::Baseline, 1000U, 1U);
        } catch (const std::runtime_error&) {
            rejected = true;
        }
        require(rejected, "non-power-of-two size must be rejected");

        std::cout << "Lane I I001 contract tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "Lane I I001 contract test failed: " << error.what() << '\n';
        return 1;
    }
}
