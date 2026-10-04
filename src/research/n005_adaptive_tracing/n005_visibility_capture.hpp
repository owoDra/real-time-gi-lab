#pragma once

#include <bit>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::n005 {

inline constexpr const char* kVisibilityCaptureEnv =
    "PHOS_N005_VISIBILITY_CAPTURE_DIR";

struct VisibilityCaptureHeader {
    char magic[8]{'N', '0', '0', '5', 'V', 'I', 'S', '1'};
    std::uint32_t version{1U};
    std::uint32_t width{};
    std::uint32_t height{};
    std::uint32_t count{};
};
static_assert(sizeof(VisibilityCaptureHeader) == 24U);

template <typename Context, typename Buffer>
void capture_visibility_if_requested(
    Context& context,
    Buffer& depth,
    Buffer& owners,
    std::uint32_t width,
    std::uint32_t height) {
    const char* raw_root = std::getenv(kVisibilityCaptureEnv);
    if (raw_root == nullptr || raw_root[0] == '\0') {
        return;
    }
    static_assert(std::endian::native == std::endian::little);

    const std::uint64_t count64 =
        std::uint64_t(width) * std::uint64_t(height);
    if (width == 0U || height == 0U ||
        count64 > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("N005 visibility capture dimensions invalid");
    }
    const auto count = static_cast<std::uint32_t>(count64);
    std::vector<std::uint32_t> depth_bits(count);
    std::vector<std::uint32_t> owner_ids(count);
    context.download_device_buffer(
        depth,
        depth_bits.data(),
        depth_bits.size() * sizeof(depth_bits[0]));
    context.download_device_buffer(
        owners,
        owner_ids.data(),
        owner_ids.size() * sizeof(owner_ids[0]));

    const std::filesystem::path root(raw_root);
    std::filesystem::create_directories(root);
    static std::uint32_t capture_index = 0U;
    std::ostringstream name;
    name << "visibility-" << std::setw(3) << std::setfill('0')
         << capture_index << ".bin";
    const auto path = root / name.str();

    VisibilityCaptureHeader header{};
    header.width = width;
    header.height = height;
    header.count = count;

    std::ofstream out(path, std::ios::binary);
    if (!out) {
        throw std::runtime_error("could not open N005 visibility capture");
    }
    out.write(
        reinterpret_cast<const char*>(&header),
        static_cast<std::streamsize>(sizeof(header)));
    out.write(
        reinterpret_cast<const char*>(depth_bits.data()),
        static_cast<std::streamsize>(
            depth_bits.size() * sizeof(depth_bits[0])));
    out.write(
        reinterpret_cast<const char*>(owner_ids.data()),
        static_cast<std::streamsize>(
            owner_ids.size() * sizeof(owner_ids[0])));
    if (!out) {
        throw std::runtime_error("N005 visibility capture write failed");
    }
    ++capture_index;
}

} // namespace phos::gi::research::n005
