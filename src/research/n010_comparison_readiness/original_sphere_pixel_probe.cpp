// Plan136: caller-only diagnosis; the included original oracle is immutable.
#include "n010_rqmc_oracle.hpp"
#include <iomanip>
#include <iostream>

using namespace phos::gi::research::n008;

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    N010NetRng::load(argv[1]);
    std::ifstream input(argv[2]);
    const Scene scene = parse_scene(input);
    if (scene.width != 128 || scene.height != 96 || scene.max_bounces != 8)
        return 3;
    const Oracle oracle(scene);
    Oracle::PrimaryCache cache;
    RenderCounters counters;
    PrimaryRecord record;
    constexpr uint32_t x = 96, y = 77, spp = 8192;
    constexpr uint64_t seed = 81985529216486895ULL;
    for (uint32_t s = 0; s < spp; ++s) {
        N010NetRng rng(seed, size_t(y) * scene.width + x, s);
        Rgb components[kComponents];
        try {
            oracle.sample_all_split(x, y, rng, components, counters,
                                    s == 0 ? &record : nullptr, &cache);
        } catch (const std::exception& error) {
            std::cout << "{\"exception_caught\":true,\"sample_index\":" << s
                      << ",\"pixel\":[96,77],\"seed\":" << seed
                      << ",\"what\":" << std::quoted(error.what()) << "}\n";
            return 77;
        }
    }
    std::cout << "{\"exception_caught\":false,\"completed_samples\":8192,"
                 "\"pixel\":[96,77],\"seed\":" << seed << "}\n";
    return 0;
}
