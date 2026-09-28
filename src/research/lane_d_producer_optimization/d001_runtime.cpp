#include "d001_runtime.hpp"

#include "vk_init.hpp"

#include <algorithm>
#include <array>
#include <cstring>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

namespace phos::gi::lane_d {
namespace {

[[noreturn]] void fail(const char* what) {
    throw std::runtime_error(what);
}

std::uint32_t groups(std::uint32_t count) {
    return (count + 63u) / 64u;
}

VkBufferMemoryBarrier buffer_barrier(
    const GpuBuffer& buffer,
    VkAccessFlags src,
    VkAccessFlags dst) {
    auto barrier = detail::make_vk_info<VkBufferMemoryBarrier>(
        VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER);
    barrier.srcAccessMask = src;
    barrier.dstAccessMask = dst;
    barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.buffer = buffer.buffer;
    barrier.offset = 0;
    barrier.size = buffer.size;
    return barrier;
}

} // namespace

const char* mode_name(D001Mode mode) {
    switch (mode) {
    case D001Mode::Full:
        return "full";
    case D001Mode::DepthReuse:
        return "depth-reuse";
    case D001Mode::OwnerReuse:
        return "owner-reuse";
    }
    return "unknown";
}

struct D001Runtime::Impl {
    enum PipelineIndex : std::size_t {
        VisibilityDepth = 0,
        VisibilityOwner = 1,
        Producer = 2,
        Finalize = 3,
        Gather = 4,
        Merge = 5,
        Resolve = 6,
        ProducerOwnerReuse = 7,
    };

    VulkanContext& ctx;
    lane_a::A001ParamsGpu params{};
    D001Mode mode{};
    std::uint32_t tile_count{};
    std::uint32_t max_work{};
    std::uint32_t max_outputs{};

    GpuBuffer surfaces;
    GpuBuffer depth;
    GpuBuffer counters;
    GpuBuffer work;
    GpuBuffer contributions;
    GpuBuffer accum;
    GpuBuffer resolved;
    GpuBuffer indirect;
    GpuBuffer owners;
    GpuBuffer uniform;

    VkDescriptorSetLayout descriptor_layout{VK_NULL_HANDLE};
    VkPipelineLayout pipeline_layout{VK_NULL_HANDLE};
    VkDescriptorPool descriptor_pool{VK_NULL_HANDLE};
    VkDescriptorSet descriptor_set{VK_NULL_HANDLE};
    std::array<VkPipeline, 8> pipelines{};
    VkCommandPool command_pool{VK_NULL_HANDLE};
    VkCommandBuffer command_buffer{VK_NULL_HANDLE};
    VkQueryPool query_pool{VK_NULL_HANDLE};
    VkFence fence{VK_NULL_HANDLE};

    Impl(
        VulkanContext& context,
        const lane_a::SceneSurfaceSet& scene,
        const lane_a::A001ParamsGpu& p,
        D001Mode m)
        : ctx(context), params(p), mode(m) {
        tile_count = params.counts[1] * params.counts[2];
        max_work = params.limits[1];
        max_outputs = params.limits[2];

        std::vector<std::array<float, 4>> positions(scene.samples.size());
        for (std::size_t i = 0; i < scene.samples.size(); ++i) {
            std::copy_n(
                scene.samples[i].position,
                4,
                positions[i].data());
        }

        surfaces = ctx.upload_device_buffer(
            positions.data(),
            positions.size() * sizeof(positions[0]),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        depth = ctx.create_device_buffer(
            VkDeviceSize(tile_count) * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        counters = ctx.create_device_buffer(
            4 * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        work = ctx.create_device_buffer(
            VkDeviceSize(max_work) * sizeof(lane_a::SplitRcWorkItemV1),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        contributions = ctx.create_device_buffer(
            VkDeviceSize(max_work) * sizeof(std::uint32_t) * 2,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        accum = ctx.create_device_buffer(
            VkDeviceSize(max_outputs) * sizeof(std::uint32_t) * 2,
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        resolved = ctx.create_device_buffer(
            VkDeviceSize(max_outputs) * sizeof(float),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        indirect = ctx.create_device_buffer(
            6 * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT |
                VK_BUFFER_USAGE_INDIRECT_BUFFER_BIT);
        owners = ctx.create_device_buffer(
            VkDeviceSize(tile_count) * sizeof(std::uint32_t),
            VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
        uniform = ctx.create_host_buffer(
            sizeof(lane_a::A001ParamsGpu),
            VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT);
        std::memcpy(uniform.mapped, &params, sizeof(params));

        init_descriptors();

        const std::array<const char*, 8> names{{
            "lane_a_visibility_depth.spv",
            "lane_a_visibility_owner.spv",
            "lane_a_producer.spv",
            "lane_a_finalize.spv",
            "lane_a_gather.spv",
            "lane_a_merge.spv",
            "lane_a_resolve.spv",
            "lane_d_d001_producer_owner_reuse.spv",
        }};
        for (std::size_t i = 0; i < names.size(); ++i) {
            pipelines[i] = make_pipeline(names[i]);
        }

        auto pool_info =
            detail::make_vk_info<VkCommandPoolCreateInfo>(
                VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
        pool_info.flags =
            VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pool_info.queueFamilyIndex = ctx.queue_family();
        if (ctx.vk().createCommandPool(
                &pool_info, nullptr, &command_pool) != VK_SUCCESS) {
            fail("D001 command pool");
        }

        auto command_info =
            detail::make_vk_info<VkCommandBufferAllocateInfo>(
                VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
        command_info.commandPool = command_pool;
        command_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        command_info.commandBufferCount = 1;
        if (ctx.vk().allocateCommandBuffers(
                &command_info, &command_buffer) != VK_SUCCESS) {
            fail("D001 command buffer");
        }

        auto query_info =
            detail::make_vk_info<VkQueryPoolCreateInfo>(
                VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
        query_info.queryType = VK_QUERY_TYPE_TIMESTAMP;
        query_info.queryCount = 11;
        if (ctx.vk().createQueryPool(
                &query_info, nullptr, &query_pool) != VK_SUCCESS) {
            fail("D001 query pool");
        }

        auto fence_info =
            detail::make_vk_info<VkFenceCreateInfo>(
                VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
        if (ctx.vk().createFence(
                &fence_info, nullptr, &fence) != VK_SUCCESS) {
            fail("D001 fence");
        }
    }

    ~Impl() {
        ctx.vk().deviceWaitIdle();

        if (fence) {
            ctx.vk().destroyFence(fence, nullptr);
        }
        if (query_pool) {
            ctx.vk().destroyQueryPool(query_pool, nullptr);
        }
        if (command_pool) {
            ctx.vk().destroyCommandPool(command_pool, nullptr);
        }
        for (auto pipeline : pipelines) {
            if (pipeline) {
                ctx.vk().destroyPipeline(pipeline, nullptr);
            }
        }
        if (descriptor_pool) {
            ctx.vk().destroyDescriptorPool(descriptor_pool, nullptr);
        }
        if (pipeline_layout) {
            ctx.vk().destroyPipelineLayout(pipeline_layout, nullptr);
        }
        if (descriptor_layout) {
            ctx.vk().destroyDescriptorSetLayout(
                descriptor_layout, nullptr);
        }

        ctx.destroy_buffer(uniform);
        ctx.destroy_buffer(owners);
        ctx.destroy_buffer(indirect);
        ctx.destroy_buffer(resolved);
        ctx.destroy_buffer(accum);
        ctx.destroy_buffer(contributions);
        ctx.destroy_buffer(work);
        ctx.destroy_buffer(counters);
        ctx.destroy_buffer(depth);
        ctx.destroy_buffer(surfaces);
    }

    void init_descriptors() {
        std::array<VkDescriptorSetLayoutBinding, 10> bindings{};
        for (std::uint32_t i = 0; i < 9; ++i) {
            bindings[i].binding = i;
            bindings[i].descriptorType =
                VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            bindings[i].descriptorCount = 1;
            bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        }
        bindings[9].binding = 9;
        bindings[9].descriptorType =
            VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER;
        bindings[9].descriptorCount = 1;
        bindings[9].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;

        auto layout_info =
            detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
                VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
        layout_info.bindingCount =
            static_cast<std::uint32_t>(bindings.size());
        layout_info.pBindings = bindings.data();
        if (ctx.vk().createDescriptorSetLayout(
                &layout_info, nullptr, &descriptor_layout) != VK_SUCCESS) {
            fail("D001 descriptor layout");
        }

        auto pipeline_layout_info =
            detail::make_vk_info<VkPipelineLayoutCreateInfo>(
                VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
        pipeline_layout_info.setLayoutCount = 1;
        pipeline_layout_info.pSetLayouts = &descriptor_layout;
        if (ctx.vk().createPipelineLayout(
                &pipeline_layout_info,
                nullptr,
                &pipeline_layout) != VK_SUCCESS) {
            fail("D001 pipeline layout");
        }

        std::array<VkDescriptorPoolSize, 2> sizes{{
            {VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 9},
            {VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER, 1},
        }};
        auto pool_info =
            detail::make_vk_info<VkDescriptorPoolCreateInfo>(
                VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
        pool_info.maxSets = 1;
        pool_info.poolSizeCount =
            static_cast<std::uint32_t>(sizes.size());
        pool_info.pPoolSizes = sizes.data();
        if (ctx.vk().createDescriptorPool(
                &pool_info, nullptr, &descriptor_pool) != VK_SUCCESS) {
            fail("D001 descriptor pool");
        }

        auto allocate_info =
            detail::make_vk_info<VkDescriptorSetAllocateInfo>(
                VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
        allocate_info.descriptorPool = descriptor_pool;
        allocate_info.descriptorSetCount = 1;
        allocate_info.pSetLayouts = &descriptor_layout;
        if (ctx.vk().allocateDescriptorSets(
                &allocate_info, &descriptor_set) != VK_SUCCESS) {
            fail("D001 descriptor set");
        }

        std::array<const GpuBuffer*, 10> buffers{{
            &surfaces,
            &depth,
            &counters,
            &work,
            &contributions,
            &accum,
            &resolved,
            &indirect,
            &owners,
            &uniform,
        }};
        std::array<VkDescriptorBufferInfo, 10> infos{};
        std::array<VkWriteDescriptorSet, 10> writes{};

        for (std::uint32_t i = 0; i < 10; ++i) {
            infos[i] = {
                buffers[i]->buffer,
                0,
                buffers[i]->size,
            };
            writes[i] =
                detail::make_vk_info<VkWriteDescriptorSet>(
                    VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
            writes[i].dstSet = descriptor_set;
            writes[i].dstBinding = i;
            writes[i].descriptorCount = 1;
            writes[i].descriptorType =
                i == 9
                    ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER
                    : VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            writes[i].pBufferInfo = &infos[i];
        }

        ctx.vk().updateDescriptorSets(
            static_cast<std::uint32_t>(writes.size()),
            writes.data(),
            0,
            nullptr);
    }

    VkPipeline make_pipeline(const std::string& filename) {
        const auto code = read_binary_file(
            (std::filesystem::path(PHOS_GI_LANE_D_SHADER_DIR) /
             filename)
                .string());

        auto module_info =
            detail::make_vk_info<VkShaderModuleCreateInfo>(
                VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
        module_info.codeSize = code.size();
        module_info.pCode =
            reinterpret_cast<const std::uint32_t*>(code.data());

        VkShaderModule module{};
        if (ctx.vk().createShaderModule(
                &module_info, nullptr, &module) != VK_SUCCESS) {
            fail("D001 shader module");
        }

        auto stage =
            detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
        stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        stage.module = module;
        stage.pName = "main";

        auto pipeline_info =
            detail::make_vk_info<VkComputePipelineCreateInfo>(
                VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
        pipeline_info.stage = stage;
        pipeline_info.layout = pipeline_layout;

        VkPipeline pipeline{};
        const auto result = ctx.vk().createComputePipelines(
            VK_NULL_HANDLE,
            1,
            &pipeline_info,
            nullptr,
            &pipeline);
        ctx.vk().destroyShaderModule(module, nullptr);

        if (result != VK_SUCCESS) {
            fail("D001 compute pipeline");
        }
        return pipeline;
    }

    void bind(VkPipeline pipeline) {
        ctx.vk().cmdBindPipeline(
            command_buffer,
            VK_PIPELINE_BIND_POINT_COMPUTE,
            pipeline);
        ctx.vk().cmdBindDescriptorSets(
            command_buffer,
            VK_PIPELINE_BIND_POINT_COMPUTE,
            pipeline_layout,
            0,
            1,
            &descriptor_set,
            0,
            nullptr);
    }

    void sync_compute(const GpuBuffer& buffer) {
        auto barrier = buffer_barrier(
            buffer,
            VK_ACCESS_SHADER_WRITE_BIT,
            VK_ACCESS_SHADER_READ_BIT |
                VK_ACCESS_SHADER_WRITE_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            0,
            0,
            nullptr,
            1,
            &barrier,
            0,
            nullptr);
    }

    void clear_for_compute(
        const GpuBuffer& buffer,
        std::uint32_t value) {
        ctx.vk().cmdFillBuffer(
            command_buffer,
            buffer.buffer,
            0,
            buffer.size,
            value);
        auto barrier = buffer_barrier(
            buffer,
            VK_ACCESS_TRANSFER_WRITE_BIT,
            VK_ACCESS_SHADER_READ_BIT |
                VK_ACCESS_SHADER_WRITE_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            0,
            0,
            nullptr,
            1,
            &barrier,
            0,
            nullptr);
    }

    void clear_gi_state() {
        ctx.vk().cmdFillBuffer(
            command_buffer,
            counters.buffer,
            0,
            counters.size,
            0u);
        ctx.vk().cmdFillBuffer(
            command_buffer,
            accum.buffer,
            0,
            accum.size,
            0u);

        std::array<VkBufferMemoryBarrier, 2> barriers{{
            buffer_barrier(
                counters,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT |
                    VK_ACCESS_SHADER_WRITE_BIT),
            buffer_barrier(
                accum,
                VK_ACCESS_TRANSFER_WRITE_BIT,
                VK_ACCESS_SHADER_READ_BIT |
                    VK_ACCESS_SHADER_WRITE_BIT),
        }};
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            0,
            0,
            nullptr,
            static_cast<std::uint32_t>(barriers.size()),
            barriers.data(),
            0,
            nullptr);
    }

    void begin_command_buffer() {
        ctx.vk().resetCommandBuffer(command_buffer, 0);

        auto begin_info =
            detail::make_vk_info<VkCommandBufferBeginInfo>(
                VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
        begin_info.flags =
            VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (ctx.vk().beginCommandBuffer(
                command_buffer, &begin_info) != VK_SUCCESS) {
            fail("D001 begin command buffer");
        }
    }

    void submit_and_wait() {
        if (ctx.vk().endCommandBuffer(command_buffer) != VK_SUCCESS) {
            fail("D001 end command buffer");
        }

        ctx.vk().resetFences(1, &fence);
        auto submit_info =
            detail::make_vk_info<VkSubmitInfo>(
                VK_STRUCTURE_TYPE_SUBMIT_INFO);
        submit_info.commandBufferCount = 1;
        submit_info.pCommandBuffers = &command_buffer;

        if (ctx.vk().queueSubmit(
                ctx.queue(),
                1,
                &submit_info,
                fence) != VK_SUCCESS) {
            fail("D001 submit");
        }
        if (ctx.vk().waitForFences(
                1,
                &fence,
                VK_TRUE,
                UINT64_MAX) != VK_SUCCESS) {
            fail("D001 wait");
        }
    }

    void prepare_reused_visibility() {
        if (mode == D001Mode::Full) {
            return;
        }

        begin_command_buffer();

        clear_for_compute(depth, 0x7f800000u);
        bind(pipelines[VisibilityDepth]);
        ctx.vk().cmdDispatch(
            command_buffer,
            groups(params.counts[0]),
            1,
            1);
        sync_compute(depth);

        if (mode == D001Mode::OwnerReuse) {
            clear_for_compute(owners, 0xffffffffu);
            bind(pipelines[VisibilityOwner]);
            ctx.vk().cmdDispatch(
                command_buffer,
                groups(params.counts[0]),
                1,
                1);
            sync_compute(owners);
        }

        submit_and_wait();
    }

    std::array<std::uint64_t, 11> run(bool read_timestamps) {
        begin_command_buffer();

        ctx.vk().cmdResetQueryPool(
            command_buffer,
            query_pool,
            0,
            11);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
            query_pool,
            0);

        if (mode == D001Mode::Full) {
            clear_for_compute(depth, 0x7f800000u);
        }
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            1);

        if (mode == D001Mode::Full) {
            bind(pipelines[VisibilityDepth]);
            ctx.vk().cmdDispatch(
                command_buffer,
                groups(params.counts[0]),
                1,
                1);
            sync_compute(depth);
        }
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            2);

        if (mode != D001Mode::OwnerReuse) {
            clear_for_compute(owners, 0xffffffffu);
        }
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            3);

        if (mode != D001Mode::OwnerReuse) {
            bind(pipelines[VisibilityOwner]);
            ctx.vk().cmdDispatch(
                command_buffer,
                groups(params.counts[0]),
                1,
                1);
            sync_compute(owners);
        }
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            4);

        clear_gi_state();
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            5);

        const auto producer_pipeline =
            mode == D001Mode::OwnerReuse
                ? pipelines[ProducerOwnerReuse]
                : pipelines[Producer];
        bind(producer_pipeline);
        ctx.vk().cmdDispatch(
            command_buffer,
            groups(params.counts[0]),
            1,
            1);
        sync_compute(counters);
        sync_compute(work);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            6);

        bind(pipelines[Finalize]);
        ctx.vk().cmdDispatch(command_buffer, 1, 1, 1);
        auto indirect_ready = buffer_barrier(
            indirect,
            VK_ACCESS_SHADER_WRITE_BIT,
            VK_ACCESS_INDIRECT_COMMAND_READ_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            VK_PIPELINE_STAGE_DRAW_INDIRECT_BIT,
            0,
            0,
            nullptr,
            1,
            &indirect_ready,
            0,
            nullptr);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            7);

        bind(pipelines[Gather]);
        ctx.vk().cmdDispatchIndirect(
            command_buffer,
            indirect.buffer,
            0);
        sync_compute(contributions);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            8);

        bind(pipelines[Merge]);
        ctx.vk().cmdDispatchIndirect(
            command_buffer,
            indirect.buffer,
            0);
        sync_compute(accum);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            query_pool,
            9);

        bind(pipelines[Resolve]);
        ctx.vk().cmdDispatchIndirect(
            command_buffer,
            indirect.buffer,
            3 * sizeof(std::uint32_t));
        auto resolved_ready = buffer_barrier(
            resolved,
            VK_ACCESS_SHADER_WRITE_BIT,
            VK_ACCESS_TRANSFER_READ_BIT);
        ctx.vk().cmdPipelineBarrier(
            command_buffer,
            VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            0,
            0,
            nullptr,
            1,
            &resolved_ready,
            0,
            nullptr);
        ctx.vk().cmdWriteTimestamp(
            command_buffer,
            VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT,
            query_pool,
            10);

        submit_and_wait();

        std::array<std::uint64_t, 11> timestamps{};
        if (read_timestamps &&
            ctx.vk().getQueryPoolResults(
                query_pool,
                0,
                11,
                sizeof(timestamps),
                timestamps.data(),
                sizeof(std::uint64_t),
                VK_QUERY_RESULT_64_BIT |
                    VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
            fail("D001 timestamps");
        }
        return timestamps;
    }
};

D001Runtime::D001Runtime(
    VulkanContext& context,
    const lane_a::SceneSurfaceSet& scene,
    const lane_a::A001ParamsGpu& params,
    D001Mode mode)
    : impl_(std::make_unique<Impl>(
          context,
          scene,
          params,
          mode)) {}

D001Runtime::~D001Runtime() = default;

D001StageTimings D001Runtime::measure(std::uint32_t iterations) {
    if (iterations == 0) {
        throw std::runtime_error(
            "D001 iterations must be positive");
    }

    impl_->prepare_reused_visibility();
    for (int i = 0; i < 3; ++i) {
        impl_->run(false);
    }

    std::array<double, 10> sum{};
    for (std::uint32_t i = 0; i < iterations; ++i) {
        const auto timestamps = impl_->run(true);
        for (std::size_t stage = 0; stage < sum.size(); ++stage) {
            sum[stage] +=
                double(
                    timestamps[stage + 1] -
                    timestamps[stage]) *
                impl_->ctx.timestamp_period_ns() /
                1000.0;
        }
    }

    for (auto& value : sum) {
        value /= double(iterations);
    }

    if (impl_->mode != D001Mode::Full) {
        sum[0] = 0.0;
        sum[1] = 0.0;
    }
    if (impl_->mode == D001Mode::OwnerReuse) {
        sum[2] = 0.0;
        sum[3] = 0.0;
    }

    return {
        sum[0],
        sum[1],
        sum[2],
        sum[3],
        sum[4],
        sum[5],
        sum[6],
        sum[7],
        sum[8],
        sum[9],
    };
}

lane_a::A001Readback D001Runtime::readback() {
    lane_a::A001Readback output;

    impl_->ctx.download_device_buffer(
        impl_->counters,
        output.counters.data(),
        sizeof(output.counters));
    if (output.counters[0] > impl_->max_work ||
        output.counters[1] > impl_->max_outputs) {
        throw std::runtime_error(
            "D001 GPU counters exceeded allocated capacity");
    }

    output.tile_owner.resize(impl_->tile_count);
    impl_->ctx.download_device_buffer(
        impl_->owners,
        output.tile_owner.data(),
        VkDeviceSize(output.tile_owner.size()) *
            sizeof(std::uint32_t));

    output.work_items.resize(output.counters[0]);
    if (!output.work_items.empty()) {
        impl_->ctx.download_device_buffer(
            impl_->work,
            output.work_items.data(),
            VkDeviceSize(output.work_items.size()) *
                sizeof(lane_a::SplitRcWorkItemV1));
    }

    output.resolved.resize(output.counters[1]);
    if (!output.resolved.empty()) {
        impl_->ctx.download_device_buffer(
            impl_->resolved,
            output.resolved.data(),
            VkDeviceSize(output.resolved.size()) *
                sizeof(float));
    }

    return output;
}

D001Memory D001Runtime::memory() const {
    const auto& i = *impl_;

    const std::size_t physical_persistent =
        i.surfaces.size + i.uniform.size + i.resolved.size;
    const std::size_t physical_transient =
        i.depth.size + i.owners.size + i.counters.size +
        i.work.size + i.contributions.size + i.accum.size +
        i.indirect.size;

    std::size_t reused_visibility = 0;
    std::size_t gi_visibility_scratch =
        i.depth.size + i.owners.size;

    if (i.mode == D001Mode::DepthReuse) {
        reused_visibility = i.depth.size;
        gi_visibility_scratch = i.owners.size;
    } else if (i.mode == D001Mode::OwnerReuse) {
        reused_visibility = i.owners.size;
        gi_visibility_scratch = 0;
    }

    // In owner-reuse mode the depth buffer exists only so the harness can
    // synthesize the renderer-provided owner input before timing. It is not a
    // logical GI requirement of the incremental candidate.
    std::size_t non_gi_prerequisite = reused_visibility;
    if (i.mode == D001Mode::OwnerReuse) {
        non_gi_prerequisite += i.depth.size;
    }

    const std::size_t gi_transient =
        physical_transient - non_gi_prerequisite;
    const std::size_t producer_scratch =
        gi_visibility_scratch +
        i.counters.size +
        i.indirect.size;

    return {
        physical_persistent,
        physical_transient,
        physical_persistent + physical_transient,
        physical_persistent,
        gi_transient,
        producer_scratch,
        static_cast<std::size_t>(i.work.size),
        reused_visibility,
        static_cast<std::size_t>(i.depth.size + i.owners.size),
    };
}

} // namespace phos::gi::lane_d
