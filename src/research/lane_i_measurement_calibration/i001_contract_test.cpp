#include "i001_contract.hpp"

#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>

using namespace phos::gi::research::lane_i;

int main() {
    const auto base = make_work_spec(CalibrationVariant::Baseline, 1024U, 8U);
    const auto p5 = make_work_spec(CalibrationVariant::Plus5, 1024U, 8U);
    const auto p10 = make_work_spec(CalibrationVariant::Plus10, 1024U, 8U);
    const auto p20 = make_work_spec(CalibrationVariant::Plus20, 1024U, 8U);

    assert(base.work_iterations == 200U);
    assert(p5.work_iterations == 210U);
    assert(p10.work_iterations == 220U);
    assert(p20.work_iterations == 240U);
    assert(p5.controlled_work_units() * 100ULL == base.controlled_work_units() * 105ULL);
    assert(p10.controlled_work_units() * 100ULL == base.controlled_work_units() * 110ULL);
    assert(p20.controlled_work_units() * 100ULL == base.controlled_work_units() * 120ULL);

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
        assert(sums[i] != 0ULL);
        for (std::size_t j = i + 1; j < sums.size(); ++j) {
            assert(sums[i] != sums[j]);
        }
    }

    bool rejected = false;
    try {
        (void)make_work_spec(CalibrationVariant::Baseline, 1000U, 1U);
    } catch (...) {
        rejected = true;
    }
    assert(rejected);

    std::cout << "Lane I I001 contract tests passed\n";
    return 0;
}
