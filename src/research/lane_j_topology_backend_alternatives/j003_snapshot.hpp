#pragma once

#include "j003_types.hpp"

#include <filesystem>
#include <vector>

namespace phos::gi::research::lane_j {

// Reads the exact PHOSJ2G1 binary emitted by J002. The J002 materializer owns
// cryptographic snapshot identity; this loader additionally fails closed on
// magic/version/record-size drift before GPU validation.
[[nodiscard]] std::vector<Triangle> load_j002_snapshot(
    const std::filesystem::path& path);

} // namespace phos::gi::research::lane_j
