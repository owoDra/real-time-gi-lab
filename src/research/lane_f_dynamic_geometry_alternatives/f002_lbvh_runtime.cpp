#include "f002_lbvh_runtime.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <utility>

namespace phos::gi::research::lane_f {
namespace {

constexpr std::uint32_t kWorkgroupSize = 256U;
constexpr std::uint32_t kRadixPasses = 16U;
constexpr std::uint32_t kTimestampCountPerBuild = 8U;
constexpr std::uint32_t kInvalidId = 0xffffffffU;

[[noreturn]] void fail(const char* message) {
    throw std::runtime_error(message);
}

[[nodiscard]] std::uint32_t groups_for(std::uint32_t count) {
    return (count + kWorkgroupSize - 1U) / kWorkgroupSize;
}

[[nodiscard]] double timestamp_us(
    std::uint64_t begin,
    std::uint64_t end,
    float period_ns) {
    return static_cast<double>(end - begin) *
           static_cast<double>(period_ns) / 1000.0;
}

[[nodiscard]] bool close_bound(float expected, float actual) {
    const auto scale = std::max(1.0F, std::abs(expected));
    return std::abs(expected - actual) <= 2.0e-4F * scale;
}

} // namespace

double f002_median(std::vector<double> values) {
    if (values.empty()) return 0.0;
    std::sort(values.begin(), values.end());
    const auto mid = values.size() / 2U;
    if ((values.size() & 1U) != 0U) return values[mid];
    return (values[mid - 1U] + values[mid]) * 0.5;
}

F002LbvhBuilder::F002LbvhBuilder(
    lane_b::B002VulkanContext& context,
    std::span<const lane_b::GpuTriangle> template_triangles,
    std::uint32_t primitive_count,
    lane_b::Vec3 origin,
    float page_extent,
    std::filesystem::path shader_path)
    : context_(context),
      template_cpu_(template_triangles.begin(), template_triangles.end()),
      count_(primitive_count),
      origin_(origin),
      page_extent_(page_extent),
      shader_path_(std::move(shader_path)) {
    if (template_cpu_.empty() || count_ < 2U ||
        !(page_extent_ > 0.0F) || !std::isfinite(page_extent_)) {
        fail("F002 invalid LBVH builder dimensions");
    }

    const auto storage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
    const auto template_bytes =
        VkDeviceSize(template_cpu_.size() * sizeof(lane_b::GpuTriangle));
    const auto working_bytes =
        VkDeviceSize(count_) * sizeof(lane_b::GpuTriangle);
    const auto aabb_bytes = VkDeviceSize(count_) * sizeof(float) * 4U;
    const auto key_bytes = VkDeviceSize(count_) * sizeof(std::uint32_t) * 4U;
    const auto block_count = groups_for(count_);
    const auto histogram_bytes =
        VkDeviceSize(block_count) * 16U * sizeof(std::uint32_t);
    const auto digit_base_bytes = VkDeviceSize(16U) * sizeof(std::uint32_t);
    const auto node_count = std::size_t(count_) * 2U - 1U;
    const auto node_bytes =
        VkDeviceSize(node_count * sizeof(lane_b::GpuBvhNode));
    const auto ready_bytes =
        VkDeviceSize(std::max<std::uint32_t>(1U, count_ - 1U)) *
        sizeof(std::uint32_t);

    template_buffer_ = context_.upload_device_buffer(
        template_cpu_.data(), template_bytes, storage);
    working_buffer_ = context_.create_device_buffer(working_bytes, storage);
    aabb_min_buffer_ = context_.create_device_buffer(aabb_bytes, storage);
    aabb_max_buffer_ = context_.create_device_buffer(aabb_bytes, storage);
    keys_a_buffer_ = context_.create_device_buffer(key_bytes, storage);
    keys_b_buffer_ = context_.create_device_buffer(key_bytes, storage);
    histogram_buffer_ = context_.create_device_buffer(histogram_bytes, storage);
    offsets_buffer_ = context_.create_device_buffer(histogram_bytes, storage);
    digit_base_buffer_ = context_.create_device_buffer(digit_base_bytes, storage);
    nodes_buffer_ = context_.create_device_buffer(node_bytes, storage);
    ready_buffer_ = context_.create_device_buffer(ready_bytes, storage);

    memory_.template_bytes = template_buffer_.allocation_size;
    memory_.working_geometry_bytes = working_buffer_.allocation_size;
    memory_.aabb_bytes =
        aabb_min_buffer_.allocation_size + aabb_max_buffer_.allocation_size;
    memory_.key_bytes =
        keys_a_buffer_.allocation_size + keys_b_buffer_.allocation_size;
    memory_.histogram_bytes = histogram_buffer_.allocation_size;
    memory_.prefix_bytes =
        offsets_buffer_.allocation_size + digit_base_buffer_.allocation_size;
    memory_.node_bytes = nodes_buffer_.allocation_size;
    memory_.ready_bytes = ready_buffer_.allocation_size;

    constexpr std::size_t binding_count = 11U;
    std::array<const lane_b::B002Buffer*, binding_count> buffers{
        &template_buffer_,
        &working_buffer_,
        &aabb_min_buffer_,
        &aabb_max_buffer_,
        &keys_a_buffer_,
        &keys_b_buffer_,
        &histogram_buffer_,
        &offsets_buffer_,
        &digit_base_buffer_,
        &nodes_buffer_,
        &ready_buffer_,
    };

    std::array<VkDescriptorSetLayoutBinding, binding_count> layout_bindings{};
    for (std::uint32_t index = 0; index < binding_count; ++index) {
        layout_bindings[index].binding = index;
        layout_bindings[index].descriptorType =
            VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        layout_bindings[index].descriptorCount = 1;
        layout_bindings[index].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }

    auto descriptor_layout_info =
        detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    descriptor_layout_info.bindingCount =
        static_cast<std::uint32_t>(layout_bindings.size());
    descriptor_layout_info.pBindings = layout_bindings.data();
    if (context_.vk().createDescriptorSetLayout(
            &descriptor_layout_info,
            nullptr,
            &descriptor_layout_) != VK_SUCCESS) {
        fail("F002 descriptor set layout");
    }

    VkPushConstantRange push_range{};
    push_range.stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    push_range.offset = 0;
    push_range.size = sizeof(Push);

    auto pipeline_layout_info =
        detail::make_vk_info<VkPipelineLayoutCreateInfo>(
            VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pipeline_layout_info.setLayoutCount = 1;
    pipeline_layout_info.pSetLayouts = &descriptor_layout_;
    pipeline_layout_info.pushConstantRangeCount = 1;
    pipeline_layout_info.pPushConstantRanges = &push_range;
    if (context_.vk().createPipelineLayout(
            &pipeline_layout_info,
            nullptr,
            &pipeline_layout_) != VK_SUCCESS) {
        fail("F002 pipeline layout");
    }

    VkDescriptorPoolSize pool_size{
        VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,
        static_cast<std::uint32_t>(binding_count),
    };
    auto pool_info = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    pool_info.maxSets = 1;
    pool_info.poolSizeCount = 1;
    pool_info.pPoolSizes = &pool_size;
    if (context_.vk().createDescriptorPool(
            &pool_info,
            nullptr,
            &descriptor_pool_) != VK_SUCCESS) {
        fail("F002 descriptor pool");
    }

    auto allocate_info = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    allocate_info.descriptorPool = descriptor_pool_;
    allocate_info.descriptorSetCount = 1;
    allocate_info.pSetLayouts = &descriptor_layout_;
    if (context_.vk().allocateDescriptorSets(
            &allocate_info,
            &descriptor_set_) != VK_SUCCESS) {
        fail("F002 descriptor set");
    }

    std::array<VkDescriptorBufferInfo, binding_count> buffer_infos{};
    std::array<VkWriteDescriptorSet, binding_count> writes{};
    for (std::uint32_t index = 0; index < binding_count; ++index) {
        buffer_infos[index] = {
            buffers[index]->buffer,
            0,
            buffers[index]->size,
        };
        writes[index] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[index].dstSet = descriptor_set_;
        writes[index].dstBinding = index;
        writes[index].descriptorCount = 1;
        writes[index].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[index].pBufferInfo = &buffer_infos[index];
    }
    context_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()),
        writes.data(),
        0,
        nullptr);

    const auto code = lane_b::read_b002_binary(shader_path_.string());
    auto module_info = detail::make_vk_info<VkShaderModuleCreateInfo>(
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    module_info.codeSize = code.size();
    module_info.pCode =
        reinterpret_cast<const std::uint32_t*>(code.data());
    VkShaderModule module{VK_NULL_HANDLE};
    if (context_.vk().createShaderModule(
            &module_info,
            nullptr,
            &module) != VK_SUCCESS) {
        fail("F002 shader module");
    }

    auto stage = detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
    stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    stage.module = module;
    stage.pName = "main";

    auto pipeline_info = detail::make_vk_info<VkComputePipelineCreateInfo>(
        VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
    pipeline_info.stage = stage;
    pipeline_info.layout = pipeline_layout_;
    const auto pipeline_result = context_.vk().createComputePipelines(
        VK_NULL_HANDLE,
        1,
        &pipeline_info,
        nullptr,
        &pipeline_);
    context_.vk().destroyShaderModule(module, nullptr);
    if (pipeline_result != VK_SUCCESS) {
        fail("F002 compute pipeline");
    }

    auto command_pool_info = detail::make_vk_info<VkCommandPoolCreateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    command_pool_info.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    command_pool_info.queueFamilyIndex = context_.queue_family();
    if (context_.vk().createCommandPool(
            &command_pool_info,
            nullptr,
            &command_pool_) != VK_SUCCESS) {
        fail("F002 command pool");
    }

    auto fence_info = detail::make_vk_info<VkFenceCreateInfo>(
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (context_.vk().createFence(
            &fence_info,
            nullptr,
            &fence_) != VK_SUCCESS) {
        fail("F002 fence");
    }
}

F002LbvhBuilder::~F002LbvhBuilder() {
    context_.vk().deviceWaitIdle();
    if (fence_ != VK_NULL_HANDLE) context_.vk().destroyFence(fence_, nullptr);
    if (command_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyCommandPool(command_pool_, nullptr);
    if (pipeline_ != VK_NULL_HANDLE)
        context_.vk().destroyPipeline(pipeline_, nullptr);
    if (descriptor_pool_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (pipeline_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_ != VK_NULL_HANDLE)
        context_.vk().destroyDescriptorSetLayout(descriptor_layout_, nullptr);

    context_.destroy_buffer(ready_buffer_);
    context_.destroy_buffer(nodes_buffer_);
    context_.destroy_buffer(digit_base_buffer_);
    context_.destroy_buffer(offsets_buffer_);
    context_.destroy_buffer(histogram_buffer_);
    context_.destroy_buffer(keys_b_buffer_);
    context_.destroy_buffer(keys_a_buffer_);
    context_.destroy_buffer(aabb_max_buffer_);
    context_.destroy_buffer(aabb_min_buffer_);
    context_.destroy_buffer(working_buffer_);
    context_.destroy_buffer(template_buffer_);
}

void F002LbvhBuilder::compute_barrier(VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask =
        VK_ACCESS_SHADER_WRITE_BIT | VK_ACCESS_SHADER_READ_BIT;
    barrier.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0,
        1,
        &barrier,
        0,
        nullptr,
        0,
        nullptr);
}

void F002LbvhBuilder::transfer_to_compute_barrier(
    VkCommandBuffer command) const {
    auto barrier = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    barrier.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    barrier.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    context_.vk().cmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0,
        1,
        &barrier,
        0,
        nullptr,
        0,
        nullptr);
}

void F002LbvhBuilder::dispatch(
    VkCommandBuffer command,
    std::uint32_t mode,
    std::uint32_t pass,
    std::uint32_t groups) const {
    Push push{};
    push.mode = mode;
    push.count = count_;
    push.template_count =
        static_cast<std::uint32_t>(template_cpu_.size());
    push.pass_index = pass;
    push.origin_page_extent[0] = origin_.x;
    push.origin_page_extent[1] = origin_.y;
    push.origin_page_extent[2] = origin_.z;
    push.origin_page_extent[3] = page_extent_;

    context_.vk().cmdPushConstants(
        command,
        pipeline_layout_,
        VK_SHADER_STAGE_COMPUTE_BIT,
        0,
        sizeof(Push),
        &push);
    context_.vk().cmdDispatch(command, groups, 1, 1);
}

void F002LbvhBuilder::record_build(
    VkCommandBuffer command,
    VkQueryPool query_pool,
    std::uint32_t query_base,
    bool timed) const {
    auto timestamp = [&](std::uint32_t offset) {
        if (!timed) return;
        context_.vk().cmdWriteTimestamp(
            command,
            VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            query_pool,
            query_base + offset);
    };

    timestamp(0U);

    context_.vk().cmdFillBuffer(
        command, ready_buffer_.buffer, 0, ready_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, histogram_buffer_.buffer, 0, histogram_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, offsets_buffer_.buffer, 0, offsets_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command, digit_base_buffer_.buffer, 0, digit_base_buffer_.size, 0U);
    context_.vk().cmdFillBuffer(
        command,
        nodes_buffer_.buffer,
        0,
        nodes_buffer_.size,
        kInvalidId);
    transfer_to_compute_barrier(command);
    timestamp(1U);

    context_.vk().cmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        pipeline_);
    context_.vk().cmdBindDescriptorSets(
        command,
        VK_PIPELINE_BIND_POINT_COMPUTE,
        pipeline_layout_,
        0,
        1,
        &descriptor_set_,
        0,
        nullptr);

    const auto groups = groups_for(count_);
    dispatch(command, 0U, 0U, groups);
    compute_barrier(command);
    timestamp(2U);

    dispatch(command, 1U, 0U, groups);
    compute_barrier(command);
    timestamp(3U);

    dispatch(command, 2U, 0U, groups);
    compute_barrier(command);
    timestamp(4U);

    const auto block_groups = groups_for(count_);
    for (std::uint32_t pass = 0U; pass < kRadixPasses; ++pass) {
        dispatch(command, 3U, pass, block_groups);
        compute_barrier(command);
        dispatch(command, 4U, pass, 1U);
        compute_barrier(command);
        dispatch(command, 5U, pass, block_groups);
        compute_barrier(command);
    }
    timestamp(5U);

    dispatch(command, 6U, 0U, groups_for(count_ - 1U));
    compute_barrier(command);
    timestamp(6U);

    dispatch(command, 7U, 0U, groups);
    compute_barrier(command);
    timestamp(7U);
}

void F002LbvhBuilder::submit_and_wait(VkCommandBuffer command) const {
    if (context_.vk().endCommandBuffer(command) != VK_SUCCESS) {
        fail("F002 command end");
    }

    context_.vk().resetFences(1, &fence_);
    auto submit_info = detail::make_vk_info<VkSubmitInfo>(
        VK_STRUCTURE_TYPE_SUBMIT_INFO);
    submit_info.commandBufferCount = 1;
    submit_info.pCommandBuffers = &command;
    if (context_.vk().queueSubmit(
            context_.queue(),
            1,
            &submit_info,
            fence_) != VK_SUCCESS) {
        fail("F002 queue submit");
    }
    if (context_.vk().waitForFences(
            1,
            &fence_,
            VK_TRUE,
            UINT64_MAX) != VK_SUCCESS) {
        fail("F002 fence wait");
    }
}

std::vector<F002BuildSample> F002LbvhBuilder::measure(
    std::uint32_t warmup_builds,
    std::uint32_t measured_builds) {
    if (warmup_builds == 0U || measured_builds == 0U ||
        measured_builds > 1000U) {
        fail("F002 invalid warmup/measured build count");
    }

    context_.vk().resetCommandPool(command_pool_, 0);

    VkQueryPool query_pool{VK_NULL_HANDLE};
    auto query_info = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
    query_info.queryCount = measured_builds * kTimestampCountPerBuild;
    if (context_.vk().createQueryPool(
            &query_info,
            nullptr,
            &query_pool) != VK_SUCCESS) {
        fail("F002 query pool");
    }

    VkCommandBuffer command{};
    auto allocate_info = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    allocate_info.commandPool = command_pool_;
    allocate_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocate_info.commandBufferCount = 1;
    if (context_.vk().allocateCommandBuffers(
            &allocate_info,
            &command) != VK_SUCCESS) {
        context_.vk().destroyQueryPool(query_pool, nullptr);
        fail("F002 command buffer");
    }

    auto begin_info = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    begin_info.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (context_.vk().beginCommandBuffer(command, &begin_info) != VK_SUCCESS) {
        context_.vk().destroyQueryPool(query_pool, nullptr);
        fail("F002 command begin");
    }

    context_.vk().cmdResetQueryPool(
        command,
        query_pool,
        0,
        measured_builds * kTimestampCountPerBuild);

    for (std::uint32_t build = 0U; build < warmup_builds; ++build) {
        record_build(command, query_pool, 0U, false);
    }
    for (std::uint32_t build = 0U; build < measured_builds; ++build) {
        record_build(
            command,
            query_pool,
            build * kTimestampCountPerBuild,
            true);
    }

    submit_and_wait(command);

    std::vector<std::uint64_t> timestamps(
        std::size_t(measured_builds) * kTimestampCountPerBuild);
    if (context_.vk().getQueryPoolResults(
            query_pool,
            0,
            static_cast<std::uint32_t>(timestamps.size()),
            timestamps.size() * sizeof(std::uint64_t),
            timestamps.data(),
            sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        context_.vk().destroyQueryPool(query_pool, nullptr);
        fail("F002 query readback");
    }
    context_.vk().destroyQueryPool(query_pool, nullptr);

    std::vector<F002BuildSample> samples;
    samples.reserve(measured_builds);
    const auto period = context_.timestamp_period_ns();
    for (std::uint32_t build = 0U; build < measured_builds; ++build) {
        const auto* q =
            timestamps.data() + std::size_t(build) * kTimestampCountPerBuild;
        samples.push_back({
            timestamp_us(q[0], q[1], period),
            timestamp_us(q[1], q[2], period),
            timestamp_us(q[2], q[3], period),
            timestamp_us(q[3], q[4], period),
            timestamp_us(q[4], q[5], period),
            timestamp_us(q[5], q[6], period),
            timestamp_us(q[6], q[7], period),
            timestamp_us(q[0], q[7], period),
        });
    }
    return samples;
}

F002Validation F002LbvhBuilder::validate() const {
    F002Validation result;

    std::vector<std::uint32_t> keys(
        std::size_t(count_) * 4U);
    context_.download_device_buffer(
        keys_a_buffer_,
        keys.data(),
        VkDeviceSize(keys.size() * sizeof(std::uint32_t)));

    for (std::uint32_t index = 1U; index < count_; ++index) {
        const auto previous = std::size_t(index - 1U) * 4U;
        const auto current = std::size_t(index) * 4U;
        const bool ordered =
            keys[previous] < keys[current] ||
            (keys[previous] == keys[current] &&
             (keys[previous + 1U] < keys[current + 1U] ||
              (keys[previous + 1U] == keys[current + 1U] &&
               keys[previous + 2U] <= keys[current + 2U])));
        if (!ordered) ++result.sort_mismatches;
    }

    std::vector<lane_b::GpuBvhNode> nodes(
        std::size_t(count_) * 2U - 1U);
    context_.download_device_buffer(
        nodes_buffer_,
        nodes.data(),
        VkDeviceSize(nodes.size() * sizeof(lane_b::GpuBvhNode)));

    std::uint32_t root = kInvalidId;
    std::size_t root_count = 0U;
    for (std::uint32_t index = 0U; index < count_ - 1U; ++index) {
        if (nodes[index].data[2] == kInvalidId) {
            root = index;
            ++root_count;
        }
    }
    if (root_count != 1U) {
        result.root_count_mismatches = 1U;
        return result;
    }

    lane_b::Aabb expected{};
    for (std::uint32_t id = 0U; id < count_; ++id) {
        const auto source = id % template_cpu_.size();
        const auto group =
            id / static_cast<std::uint32_t>(template_cpu_.size());
        const auto gx = group & 31U;
        const auto gy = (group >> 5U) & 31U;
        const auto gz = group >> 10U;
        const float spacing = page_extent_ * 1.5F;
        const lane_b::Vec3 delta{
            static_cast<float>(gx) * spacing,
            static_cast<float>(gy) * spacing,
            static_cast<float>(gz) * spacing,
        };
        const auto& source_triangle = template_cpu_[source];
        lane_b::Triangle triangle{
            {
                source_triangle.v0[0] + delta.x,
                source_triangle.v0[1] + delta.y,
                source_triangle.v0[2] + delta.z,
            },
            {
                source_triangle.v1[0] + delta.x,
                source_triangle.v1[1] + delta.y,
                source_triangle.v1[2] + delta.z,
            },
            {
                source_triangle.v2[0] + delta.x,
                source_triangle.v2[1] + delta.y,
                source_triangle.v2[2] + delta.z,
            },
            id,
            source_triangle.metadata[1],
            source_triangle.metadata[2],
            source_triangle.metadata[3] != 0U,
        };
        expected = lane_b::merge(expected, lane_b::triangle_bounds(triangle));
    }

    const auto& actual = nodes[root];
    const std::array<float, 6> expected_values{
        expected.min.x,
        expected.min.y,
        expected.min.z,
        expected.max.x,
        expected.max.y,
        expected.max.z,
    };
    const std::array<float, 6> actual_values{
        actual.bounds_min[0],
        actual.bounds_min[1],
        actual.bounds_min[2],
        actual.bounds_max[0],
        actual.bounds_max[1],
        actual.bounds_max[2],
    };
    for (std::size_t index = 0; index < expected_values.size(); ++index) {
        if (!close_bound(expected_values[index], actual_values[index])) {
            ++result.root_bounds_mismatches;
        }
    }

    return result;
}

} // namespace phos::gi::research::lane_f
