#pragma once

#include <vulkan/vulkan.h>

namespace phos::gi::detail {

// Vulkan structs are C aggregates whose first meaningful field is sType.
// Zero-initialize the complete struct first, then set sType explicitly so
// omitted optional members are unambiguously null/zero without compiler noise.
template <typename T>
[[nodiscard]] constexpr T make_vk_info(VkStructureType s_type) noexcept {
    T value{};
    value.sType = s_type;
    return value;
}

} // namespace phos::gi::detail
