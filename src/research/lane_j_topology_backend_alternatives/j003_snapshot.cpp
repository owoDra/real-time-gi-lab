#include "j003_snapshot.hpp"

#include <array>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <type_traits>

namespace phos::gi::research::lane_j {
namespace {

struct SnapshotHeader {
    std::array<char, 8> magic{};
    std::uint32_t version{};
    std::uint32_t count{};
    std::array<std::byte, 32> payload_sha256{};
};
static_assert(sizeof(SnapshotHeader) == 48);

struct SnapshotTriangle {
    float v0[3]{};
    float v1[3]{};
    float v2[3]{};
    std::uint32_t primitive_id{};
    std::uint32_t material_id{};
    std::uint32_t instance_id{};
    std::uint8_t two_sided{};
    std::uint8_t padding[3]{};
};
static_assert(sizeof(SnapshotTriangle) == 52);
static_assert(std::is_trivially_copyable_v<SnapshotTriangle>);

[[noreturn]] void fail(const std::string& message) {
    throw std::runtime_error("J003 snapshot: " + message);
}

} // namespace

std::vector<Triangle> load_j002_snapshot(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) {
        fail("cannot open " + path.string());
    }
    const auto end = input.tellg();
    if (end < static_cast<std::streamoff>(sizeof(SnapshotHeader))) {
        fail("file is smaller than PHOSJ2G1 header");
    }
    const auto size = static_cast<std::size_t>(end);
    input.seekg(0);

    SnapshotHeader header{};
    input.read(
        reinterpret_cast<char*>(&header),
        static_cast<std::streamsize>(sizeof(header)));
    if (!input) {
        fail("header read failed");
    }

    constexpr std::array<char, 8> kMagic{
        'P', 'H', 'O', 'S', 'J', '2', 'G', '1',
    };
    if (header.magic != kMagic) {
        fail("magic mismatch");
    }
    if (header.version != 1U) {
        fail("unsupported snapshot version");
    }
    const auto expected =
        sizeof(SnapshotHeader) +
        std::size_t(header.count) * sizeof(SnapshotTriangle);
    if (size != expected) {
        fail("record count/byte size mismatch");
    }
    if (header.count == 0U) {
        fail("empty snapshot");
    }

    std::vector<SnapshotTriangle> disk(header.count);
    input.read(
        reinterpret_cast<char*>(disk.data()),
        static_cast<std::streamsize>(disk.size() * sizeof(SnapshotTriangle)));
    if (!input) {
        fail("triangle payload read failed");
    }

    std::vector<Triangle> triangles;
    triangles.reserve(disk.size());
    for (const auto& item : disk) {
        triangles.push_back({
            {item.v0[0], item.v0[1], item.v0[2]},
            {item.v1[0], item.v1[1], item.v1[2]},
            {item.v2[0], item.v2[1], item.v2[2]},
            item.primitive_id,
            item.material_id,
            item.instance_id,
            item.two_sided != 0U,
        });
    }
    return triangles;
}

} // namespace phos::gi::research::lane_j
