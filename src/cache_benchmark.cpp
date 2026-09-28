#include "cache_benchmark.hpp"
#include "vk_init.hpp"

#include <array>
#include <cstring>
#include <filesystem>
#include <stdexcept>
#include <unordered_map>

namespace phos::gi {
namespace {

struct PushConstants {
    std::uint32_t count;
    std::uint32_t argument0;
    std::uint32_t argument1;
    std::uint32_t argument2;
};

[[noreturn]] void fail(const char* what) { throw std::runtime_error(what); }

VkBufferMemoryBarrier buffer_barrier(
    const GpuBuffer& buffer,
    VkAccessFlags src_access,
    VkAccessFlags dst_access) {
    auto barrier = detail::make_vk_info<VkBufferMemoryBarrier>(
        VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER);
    barrier.srcAccessMask = src_access;
    barrier.dstAccessMask = dst_access;
    barrier.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    barrier.buffer = buffer.buffer;
    barrier.offset = 0;
    barrier.size = buffer.size;
    return barrier;
}

} // namespace

CacheBenchmark::CacheBenchmark(VulkanContext& context) : ctx_(context) {
    std::array<VkDescriptorSetLayoutBinding, 4> bindings{};
    for (std::uint32_t i = 0; i < bindings.size(); ++i) {
        bindings[i].binding = i;
        bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        bindings[i].descriptorCount = 1;
        bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
    }
    auto dli = detail::make_vk_info<VkDescriptorSetLayoutCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
    dli.bindingCount = static_cast<std::uint32_t>(bindings.size());
    dli.pBindings = bindings.data();
    if (ctx_.vk().createDescriptorSetLayout(&dli, nullptr, &descriptor_layout_) != VK_SUCCESS) {
        fail("descriptor layout");
    }

    VkPushConstantRange pcr{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(PushConstants)};
    auto pli = detail::make_vk_info<VkPipelineLayoutCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO);
    pli.setLayoutCount = 1;
    pli.pSetLayouts = &descriptor_layout_;
    pli.pushConstantRangeCount = 1;
    pli.pPushConstantRanges = &pcr;
    if (ctx_.vk().createPipelineLayout(&pli, nullptr, &pipeline_layout_) != VK_SUCCESS) {
        fail("pipeline layout");
    }

    hash_pipeline_ = create_pipeline("hash_lookup.spv");
    hash_wg_bin16_pipeline_ = create_pipeline("hash_lookup_wg_bin16.spv");
    paged_pipeline_ = create_pipeline("paged_lookup.spv");
    histogram_pipeline_ = create_pipeline("page_histogram.spv");
    prefix_pipeline_ = create_pipeline("page_prefix.spv");
    scatter_pipeline_ = create_pipeline("page_scatter.spv");

    // Each measurement resets the pool before allocating its small fixed set of
    // descriptors. End-to-end GPU scheduling needs four sets at once.
    VkDescriptorPoolSize ps{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 64};
    auto dpi = detail::make_vk_info<VkDescriptorPoolCreateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
    dpi.maxSets = 16;
    dpi.poolSizeCount = 1;
    dpi.pPoolSizes = &ps;
    if (ctx_.vk().createDescriptorPool(&dpi, nullptr, &descriptor_pool_) != VK_SUCCESS) {
        fail("descriptor pool");
    }

    auto cpi = detail::make_vk_info<VkCommandPoolCreateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
    cpi.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
    cpi.queueFamilyIndex = ctx_.queue_family();
    if (ctx_.vk().createCommandPool(&cpi, nullptr, &command_pool_) != VK_SUCCESS) {
        fail("command pool");
    }

    auto cai = detail::make_vk_info<VkCommandBufferAllocateInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
    cai.commandPool = command_pool_;
    cai.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    cai.commandBufferCount = 1;
    if (ctx_.vk().allocateCommandBuffers(&cai, &command_buffer_) != VK_SUCCESS) {
        fail("command buffer");
    }

    auto qpi = detail::make_vk_info<VkQueryPoolCreateInfo>(
        VK_STRUCTURE_TYPE_QUERY_POOL_CREATE_INFO);
    qpi.queryType = VK_QUERY_TYPE_TIMESTAMP;
    qpi.queryCount = 2;
    if (ctx_.vk().createQueryPool(&qpi, nullptr, &query_pool_) != VK_SUCCESS) {
        fail("query pool");
    }

    auto fi = detail::make_vk_info<VkFenceCreateInfo>(VK_STRUCTURE_TYPE_FENCE_CREATE_INFO);
    if (ctx_.vk().createFence(&fi, nullptr, &fence_) != VK_SUCCESS) fail("fence");
}

CacheBenchmark::~CacheBenchmark() {
    ctx_.vk().deviceWaitIdle();
    if (fence_) ctx_.vk().destroyFence(fence_, nullptr);
    if (query_pool_) ctx_.vk().destroyQueryPool(query_pool_, nullptr);
    if (command_pool_) ctx_.vk().destroyCommandPool(command_pool_, nullptr);
    if (descriptor_pool_) ctx_.vk().destroyDescriptorPool(descriptor_pool_, nullptr);
    if (scatter_pipeline_) ctx_.vk().destroyPipeline(scatter_pipeline_, nullptr);
    if (prefix_pipeline_) ctx_.vk().destroyPipeline(prefix_pipeline_, nullptr);
    if (histogram_pipeline_) ctx_.vk().destroyPipeline(histogram_pipeline_, nullptr);
    if (paged_pipeline_) ctx_.vk().destroyPipeline(paged_pipeline_, nullptr);
    if (hash_wg_bin16_pipeline_) {
        ctx_.vk().destroyPipeline(hash_wg_bin16_pipeline_, nullptr);
    }
    if (hash_pipeline_) ctx_.vk().destroyPipeline(hash_pipeline_, nullptr);
    if (pipeline_layout_) ctx_.vk().destroyPipelineLayout(pipeline_layout_, nullptr);
    if (descriptor_layout_) ctx_.vk().destroyDescriptorSetLayout(descriptor_layout_, nullptr);
}

VkPipeline CacheBenchmark::create_pipeline(const std::string& filename) {
    const auto path = std::filesystem::path(PHOS_GI_LAB_SHADER_DIR) / filename;
    auto code = read_binary_file(path.string());

    auto smi = detail::make_vk_info<VkShaderModuleCreateInfo>(
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
    smi.codeSize = code.size();
    smi.pCode = reinterpret_cast<const std::uint32_t*>(code.data());

    VkShaderModule module{};
    if (ctx_.vk().createShaderModule(&smi, nullptr, &module) != VK_SUCCESS) {
        fail("shader module");
    }

    auto stage = detail::make_vk_info<VkPipelineShaderStageCreateInfo>(
        VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
    stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
    stage.module = module;
    stage.pName = "main";

    auto ci = detail::make_vk_info<VkComputePipelineCreateInfo>(
        VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO);
    ci.stage = stage;
    ci.layout = pipeline_layout_;

    VkPipeline pipeline{};
    const auto result =
        ctx_.vk().createComputePipelines(VK_NULL_HANDLE, 1, &ci, nullptr, &pipeline);
    ctx_.vk().destroyShaderModule(module, nullptr);
    if (result != VK_SUCCESS) fail("compute pipeline");
    return pipeline;
}

GpuBuffer CacheBenchmark::upload(const void* data, std::size_t bytes) {
    return ctx_.upload_device_buffer(data, bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
}

VkDescriptorSet CacheBenchmark::create_descriptor_set(
    const std::array<const GpuBuffer*, 4>& buffers) {
    VkDescriptorSet set{};
    auto ai = detail::make_vk_info<VkDescriptorSetAllocateInfo>(
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
    ai.descriptorPool = descriptor_pool_;
    ai.descriptorSetCount = 1;
    ai.pSetLayouts = &descriptor_layout_;
    if (ctx_.vk().allocateDescriptorSets(&ai, &set) != VK_SUCCESS) {
        fail("descriptor allocate");
    }

    std::array<VkDescriptorBufferInfo, 4> infos{};
    std::array<VkWriteDescriptorSet, 4> writes{};
    for (std::uint32_t i = 0; i < buffers.size(); ++i) {
        infos[i] = {buffers[i]->buffer, 0, buffers[i]->size};
        writes[i] = detail::make_vk_info<VkWriteDescriptorSet>(
            VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET);
        writes[i].dstSet = set;
        writes[i].dstBinding = i;
        writes[i].descriptorCount = 1;
        writes[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
        writes[i].pBufferInfo = &infos[i];
    }
    ctx_.vk().updateDescriptorSets(
        static_cast<std::uint32_t>(writes.size()), writes.data(), 0, nullptr);
    return set;
}

void CacheBenchmark::record_lookup_pass(
    VkCommandBuffer command_buffer,
    const CacheGpuData& cache,
    VkDescriptorSet set,
    const GpuBuffer& output,
    std::uint32_t query_count) {
    ctx_.vk().cmdBindPipeline(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, cache.pipeline);
    ctx_.vk().cmdBindDescriptorSets(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &set, 0, nullptr);

    const PushConstants pc{
        query_count,
        cache.mask_or_page_size,
        cache.lookup_limit,
        0,
    };
    ctx_.vk().cmdPushConstants(
        command_buffer, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(pc), &pc);

    const std::uint32_t groups = (query_count + 255u) / 256u;
    ctx_.vk().cmdDispatch(command_buffer, groups, 1, 1);

    // Every timed dispatch writes the same output buffer. Make the WAW
    // dependency explicit rather than relying on queue submission order alone.
    // The barrier is intentionally part of every lookup pass for every
    // representation/ordering so the benchmark remains Vulkan-correct and fair.
    auto output_ready = buffer_barrier(
        output,
        VK_ACCESS_SHADER_WRITE_BIT,
        VK_ACCESS_SHADER_WRITE_BIT | VK_ACCESS_TRANSFER_READ_BIT);
    ctx_.vk().cmdPipelineBarrier(
        command_buffer,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_TRANSFER_BIT,
        0, 0, nullptr, 1, &output_ready, 0, nullptr);
}

CacheBenchmark::SchedulerSets CacheBenchmark::create_scheduler_sets(
    const GpuBuffer& source_queries,
    const SchedulerGpuData& scheduler) {
    SchedulerSets sets;
    sets.histogram = create_descriptor_set({
        &source_queries, &scheduler.counts, &scheduler.counts, &scheduler.counts});
    sets.prefix = create_descriptor_set({
        &scheduler.counts, &scheduler.offsets, &scheduler.counts, &scheduler.counts});
    sets.scatter = create_descriptor_set({
        &source_queries, &scheduler.offsets, &scheduler.cursors,
        &scheduler.grouped_queries});
    return sets;
}

void CacheBenchmark::record_schedule_pass(
    VkCommandBuffer command_buffer,
    const SchedulerGpuData& scheduler,
    const SchedulerSets& sets) {
    // A pass may follow another scheduling or lookup pass in the same command
    // buffer. Order previous compute accesses before resetting counters.
    auto previous = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    previous.srcAccessMask = VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    previous.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    ctx_.vk().cmdPipelineBarrier(
        command_buffer,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0, 1, &previous, 0, nullptr, 0, nullptr);

    ctx_.vk().cmdFillBuffer(
        command_buffer, scheduler.counts.buffer, 0, scheduler.counts.size, 0u);
    ctx_.vk().cmdFillBuffer(
        command_buffer, scheduler.cursors.buffer, 0, scheduler.cursors.size, 0u);

    std::array<VkBufferMemoryBarrier, 2> cleared{{
        buffer_barrier(
            scheduler.counts,
            VK_ACCESS_TRANSFER_WRITE_BIT,
            VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT),
        buffer_barrier(
            scheduler.cursors,
            VK_ACCESS_TRANSFER_WRITE_BIT,
            VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT),
    }};
    ctx_.vk().cmdPipelineBarrier(
        command_buffer,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0, 0, nullptr,
        static_cast<std::uint32_t>(cleared.size()), cleared.data(),
        0, nullptr);

    const PushConstants page_pc{
        scheduler.query_count,
        scheduler.page_count,
        0,
        0,
    };

    ctx_.vk().cmdBindPipeline(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, histogram_pipeline_);
    ctx_.vk().cmdBindDescriptorSets(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &sets.histogram, 0, nullptr);
    ctx_.vk().cmdPushConstants(
        command_buffer, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(page_pc), &page_pc);
    ctx_.vk().cmdDispatch(
        command_buffer, (scheduler.query_count + 255u) / 256u, 1, 1);

    auto histogram_ready = buffer_barrier(
        scheduler.counts,
        VK_ACCESS_SHADER_WRITE_BIT,
        VK_ACCESS_SHADER_READ_BIT);
    ctx_.vk().cmdPipelineBarrier(
        command_buffer,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0, 0, nullptr, 1, &histogram_ready, 0, nullptr);

    const PushConstants prefix_pc{
        scheduler.page_count,
        0,
        0,
        0,
    };
    ctx_.vk().cmdBindPipeline(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, prefix_pipeline_);
    ctx_.vk().cmdBindDescriptorSets(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &sets.prefix, 0, nullptr);
    ctx_.vk().cmdPushConstants(
        command_buffer, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(prefix_pc), &prefix_pc);
    ctx_.vk().cmdDispatch(command_buffer, 1, 1, 1);

    auto offsets_ready = buffer_barrier(
        scheduler.offsets,
        VK_ACCESS_SHADER_WRITE_BIT,
        VK_ACCESS_SHADER_READ_BIT);
    ctx_.vk().cmdPipelineBarrier(
        command_buffer,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0, 0, nullptr, 1, &offsets_ready, 0, nullptr);

    ctx_.vk().cmdBindPipeline(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, scatter_pipeline_);
    ctx_.vk().cmdBindDescriptorSets(
        command_buffer, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline_layout_,
        0, 1, &sets.scatter, 0, nullptr);
    ctx_.vk().cmdPushConstants(
        command_buffer, pipeline_layout_, VK_SHADER_STAGE_COMPUTE_BIT,
        0, sizeof(page_pc), &page_pc);
    ctx_.vk().cmdDispatch(
        command_buffer, (scheduler.query_count + 255u) / 256u, 1, 1);

    auto grouped_ready = buffer_barrier(
        scheduler.grouped_queries,
        VK_ACCESS_SHADER_WRITE_BIT,
        VK_ACCESS_SHADER_READ_BIT |
            VK_ACCESS_SHADER_WRITE_BIT |
            VK_ACCESS_TRANSFER_READ_BIT);
    ctx_.vk().cmdPipelineBarrier(
        command_buffer,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT | VK_PIPELINE_STAGE_TRANSFER_BIT,
        0, 0, nullptr, 1, &grouped_ready, 0, nullptr);
}

double CacheBenchmark::finish_timed_submission(std::uint32_t iterations) {
    ctx_.vk().endCommandBuffer(command_buffer_);

    ctx_.vk().resetFences(1, &fence_);
    auto si = detail::make_vk_info<VkSubmitInfo>(VK_STRUCTURE_TYPE_SUBMIT_INFO);
    si.commandBufferCount = 1;
    si.pCommandBuffers = &command_buffer_;
    if (ctx_.vk().queueSubmit(ctx_.queue(), 1, &si, fence_) != VK_SUCCESS) {
        fail("queue submit");
    }
    ctx_.vk().waitForFences(1, &fence_, VK_TRUE, UINT64_MAX);

    std::array<std::uint64_t, 2> ts{};
    if (ctx_.vk().getQueryPoolResults(
            query_pool_, 0, 2, sizeof(ts), ts.data(), sizeof(std::uint64_t),
            VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT) != VK_SUCCESS) {
        fail("timestamp results");
    }

    const double elapsed_ns =
        static_cast<double>(ts[1] - ts[0]) * ctx_.timestamp_period_ns();
    return elapsed_ns / 1000.0 / static_cast<double>(iterations);
}

CacheBenchmark::LookupMeasurement CacheBenchmark::measure_lookup(
    const GpuBuffer& queries,
    std::uint32_t query_count,
    const CacheGpuData& cache,
    std::uint32_t iterations) {
    auto output = ctx_.create_device_buffer(
        static_cast<VkDeviceSize>(query_count) * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    ctx_.vk().resetDescriptorPool(descriptor_pool_, 0);
    const auto set = create_descriptor_set({
        &queries, &cache.table, &cache.payload, &output});

    ctx_.vk().resetCommandBuffer(command_buffer_, 0);
    auto bi = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    ctx_.vk().beginCommandBuffer(command_buffer_, &bi);
    ctx_.vk().cmdResetQueryPool(command_buffer_, query_pool_, 0, 2);

    for (std::uint32_t i = 0; i < 5u; ++i) {
        record_lookup_pass(command_buffer_, cache, set, output, query_count);
    }

    auto warmup_done = buffer_barrier(
        output, VK_ACCESS_SHADER_WRITE_BIT, VK_ACCESS_SHADER_WRITE_BIT);
    ctx_.vk().cmdPipelineBarrier(
        command_buffer_,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,
        0, 0, nullptr, 1, &warmup_done, 0, nullptr);

    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, query_pool_, 0);
    for (std::uint32_t i = 0; i < iterations; ++i) {
        record_lookup_pass(command_buffer_, cache, set, output, query_count);
    }
    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, query_pool_, 1);

    const double gpu_us = finish_timed_submission(iterations);

    std::vector<std::uint32_t> downloaded(query_count);
    ctx_.download_device_buffer(
        output, downloaded.data(),
        static_cast<VkDeviceSize>(downloaded.size()) * sizeof(std::uint32_t));

    std::uint64_t checksum = 0;
    for (const auto value : downloaded) checksum += value;
    ctx_.destroy_buffer(output);

    return {gpu_us, checksum};
}

double CacheBenchmark::measure_scheduler(
    const GpuBuffer& source_queries,
    SchedulerGpuData& scheduler,
    std::uint32_t iterations) {
    ctx_.vk().resetDescriptorPool(descriptor_pool_, 0);
    const auto sets = create_scheduler_sets(source_queries, scheduler);

    ctx_.vk().resetCommandBuffer(command_buffer_, 0);
    auto bi = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    ctx_.vk().beginCommandBuffer(command_buffer_, &bi);
    ctx_.vk().cmdResetQueryPool(command_buffer_, query_pool_, 0, 2);

    for (std::uint32_t i = 0; i < 3u; ++i) {
        record_schedule_pass(command_buffer_, scheduler, sets);
    }

    auto warmup_done = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    warmup_done.srcAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT | VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    warmup_done.dstAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT | VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    ctx_.vk().cmdPipelineBarrier(
        command_buffer_,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        0, 1, &warmup_done, 0, nullptr, 0, nullptr);

    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, query_pool_, 0);
    for (std::uint32_t i = 0; i < iterations; ++i) {
        record_schedule_pass(command_buffer_, scheduler, sets);
    }
    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, query_pool_, 1);

    return finish_timed_submission(iterations);
}

CacheBenchmark::LookupMeasurement CacheBenchmark::measure_end_to_end(
    const GpuBuffer& source_queries,
    SchedulerGpuData& scheduler,
    const CacheGpuData& cache,
    std::uint32_t iterations) {
    auto output = ctx_.create_device_buffer(
        static_cast<VkDeviceSize>(scheduler.query_count) * sizeof(std::uint32_t),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);

    ctx_.vk().resetDescriptorPool(descriptor_pool_, 0);
    const auto sets = create_scheduler_sets(source_queries, scheduler);
    const auto lookup_set = create_descriptor_set({
        &scheduler.grouped_queries, &cache.table, &cache.payload, &output});

    ctx_.vk().resetCommandBuffer(command_buffer_, 0);
    auto bi = detail::make_vk_info<VkCommandBufferBeginInfo>(
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO);
    bi.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    ctx_.vk().beginCommandBuffer(command_buffer_, &bi);
    ctx_.vk().cmdResetQueryPool(command_buffer_, query_pool_, 0, 2);

    for (std::uint32_t i = 0; i < 3u; ++i) {
        record_schedule_pass(command_buffer_, scheduler, sets);
        record_lookup_pass(
            command_buffer_, cache, lookup_set, output, scheduler.query_count);
    }

    auto warmup_done = detail::make_vk_info<VkMemoryBarrier>(
        VK_STRUCTURE_TYPE_MEMORY_BARRIER);
    warmup_done.srcAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT | VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    warmup_done.dstAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT | VK_ACCESS_SHADER_READ_BIT | VK_ACCESS_SHADER_WRITE_BIT;
    ctx_.vk().cmdPipelineBarrier(
        command_buffer_,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
        0, 1, &warmup_done, 0, nullptr, 0, nullptr);

    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, query_pool_, 0);
    for (std::uint32_t i = 0; i < iterations; ++i) {
        record_schedule_pass(command_buffer_, scheduler, sets);
        record_lookup_pass(
            command_buffer_, cache, lookup_set, output, scheduler.query_count);
    }
    ctx_.vk().cmdWriteTimestamp(
        command_buffer_, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, query_pool_, 1);

    const double gpu_us = finish_timed_submission(iterations);

    std::vector<std::uint32_t> downloaded(scheduler.query_count);
    ctx_.download_device_buffer(
        output, downloaded.data(),
        static_cast<VkDeviceSize>(downloaded.size()) * sizeof(std::uint32_t));
    std::uint64_t checksum = 0;
    for (const auto value : downloaded) checksum += value;

    ctx_.destroy_buffer(output);
    return {gpu_us, checksum};
}

bool CacheBenchmark::validate_gpu_grouping(
    const Workload& workload,
    const GpuBuffer& grouped_queries) {
    std::vector<Query> grouped(workload.source.size());
    ctx_.download_device_buffer(
        grouped_queries,
        grouped.data(),
        static_cast<VkDeviceSize>(grouped.size()) * sizeof(Query));

    // Query.key uniquely identifies (page, local cell) in M0. Counting key
    // multiplicities therefore gives an exact multiset check without sorting
    // millions of queries on the CPU.
    std::unordered_map<std::uint32_t, std::uint32_t> remaining;
    remaining.reserve(static_cast<std::size_t>(workload.active_cells) * 2u + 1u);
    for (const auto& q : workload.source) {
        ++remaining[q.key];
    }

    bool first = true;
    std::uint32_t previous_page = 0;
    for (const auto& q : grouped) {
        if (q.page_id >= workload.page_table.size()) return false;
        if (!first && q.page_id < previous_page) return false;
        previous_page = q.page_id;
        first = false;

        const std::uint64_t logical_cell =
            static_cast<std::uint64_t>(q.page_id) * workload.page_size + q.local_index;
        if (logical_cell + 1u != q.key) return false;

        auto it = remaining.find(q.key);
        if (it == remaining.end() || it->second == 0u) return false;
        --it->second;
    }

    for (const auto& [key, count] : remaining) {
        (void)key;
        if (count != 0u) return false;
    }
    return true;
}

std::vector<BenchmarkResult> CacheBenchmark::run(
    const Workload& w,
    std::uint32_t iterations) {
    if (iterations == 0u) throw std::runtime_error("Benchmark iterations must be positive");
    if (w.source.empty() || w.page_table.empty()) {
        throw std::runtime_error("Benchmark workload is empty");
    }

    const auto query_count = static_cast<std::uint32_t>(w.source.size());
    const std::size_t hash_bytes =
        (w.hash_keys.size() + w.hash_payload.size()) * sizeof(std::uint32_t);
    const std::size_t paged_bytes =
        (w.page_table.size() + w.paged_payload.size()) * sizeof(std::uint32_t);

    CacheGpuData hash{
        "hash",
        hash_pipeline_,
        upload(w.hash_keys.data(), w.hash_keys.size() * sizeof(std::uint32_t)),
        upload(w.hash_payload.data(), w.hash_payload.size() * sizeof(std::uint32_t)),
        w.hash_mask,
        w.hash_max_probe,
        hash_bytes,
        0,
    };
    CacheGpuData paged{
        "paged",
        paged_pipeline_,
        upload(w.page_table.data(), w.page_table.size() * sizeof(std::uint32_t)),
        upload(w.paged_payload.data(), w.paged_payload.size() * sizeof(std::uint32_t)),
        w.page_size,
        1,
        paged_bytes,
        w.page_table.size(),
    };
    std::array<CacheGpuData*, 2> caches{{&hash, &paged}};

    auto source_queries = upload(w.source.data(), w.source.size() * sizeof(Query));
    auto randomized_queries =
        upload(w.randomized.data(), w.randomized.size() * sizeof(Query));
    auto page_grouped_queries =
        upload(w.page_grouped.data(), w.page_grouped.size() * sizeof(Query));

    struct OrderingInput {
        const char* name;
        const GpuBuffer* queries;
    };
    const std::array<OrderingInput, 3> orderings{{
        {"source", &source_queries},
        {"randomized", &randomized_queries},
        {"page-grouped", &page_grouped_queries},
    }};

    std::vector<BenchmarkResult> out;
    out.reserve(9);

    for (const auto& ordering : orderings) {
        for (const auto* cache : caches) {
            const auto measurement =
                measure_lookup(*ordering.queries, query_count, *cache, iterations);
            const std::string variant =
                std::string(ordering.name) == "source"
                    ? std::string(cache->name)
                    : std::string(cache->name) + "-" + ordering.name;

            out.push_back({
                variant,
                w.source.size(),
                cache->pages,
                cache->logical_bytes,
                measurement.gpu_us_per_dispatch,
                measurement.checksum,
                w.expected_checksum,
                measurement.checksum == w.expected_checksum,
                cache->name,
                ordering.name,
                0,
                std::nullopt,
                std::nullopt,
            });
        }
    }

    // Issue #7 sub-experiment: recover only workgroup-local coherence and fuse
    // its cost into the hash lookup dispatch. The shader uses shared memory to
    // bin each 256-query workgroup by the high bits of its initial hash slot,
    // then writes results back to the original query indices. There is no
    // global reorder buffer, scheduler dispatch, or global scheduling scratch.
    CacheGpuData hash_wg_bin16{
        "hash-wg-bin16",
        hash_wg_bin16_pipeline_,
        hash.table,
        hash.payload,
        hash.mask_or_page_size,
        hash.lookup_limit,
        hash.logical_bytes,
        hash.pages,
    };
    const auto wg_bin16 =
        measure_lookup(source_queries, query_count, hash_wg_bin16, iterations);
    out.push_back({
        "hash-wg-bin16",
        w.source.size(),
        hash.pages,
        hash.logical_bytes,
        wg_bin16.gpu_us_per_dispatch,
        wg_bin16.checksum,
        w.expected_checksum,
        wg_bin16.checksum == w.expected_checksum,
        "hash",
        "wg-hash-bin16",
        0,
        std::nullopt,
        wg_bin16.gpu_us_per_dispatch,
    });

    SchedulerGpuData scheduler;
    scheduler.query_count = query_count;
    scheduler.page_count = static_cast<std::uint32_t>(w.page_table.size());
    const auto page_bytes =
        static_cast<VkDeviceSize>(scheduler.page_count) * sizeof(std::uint32_t);
    scheduler.counts = ctx_.create_device_buffer(
        page_bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    scheduler.offsets = ctx_.create_device_buffer(
        page_bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    scheduler.cursors = ctx_.create_device_buffer(
        page_bytes, VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    scheduler.grouped_queries = ctx_.create_device_buffer(
        static_cast<VkDeviceSize>(query_count) * sizeof(Query),
        VK_BUFFER_USAGE_STORAGE_BUFFER_BIT);
    scheduler.transient_bytes =
        static_cast<std::size_t>(scheduler.grouped_queries.size) +
        static_cast<std::size_t>(scheduler.counts.size) +
        static_cast<std::size_t>(scheduler.offsets.size) +
        static_cast<std::size_t>(scheduler.cursors.size);

    const double scheduling_us =
        measure_scheduler(source_queries, scheduler, iterations);
    const bool grouping_correct = validate_gpu_grouping(w, scheduler.grouped_queries);

    for (auto* cache : caches) {
        const auto lookup =
            measure_lookup(
                scheduler.grouped_queries, query_count, *cache, iterations);
        const auto end_to_end =
            measure_end_to_end(
                source_queries, scheduler, *cache, iterations);

        out.push_back({
            std::string(cache->name) + "-gpu-page-grouped",
            w.source.size(),
            cache->pages,
            cache->logical_bytes,
            lookup.gpu_us_per_dispatch,
            lookup.checksum,
            w.expected_checksum,
            grouping_correct &&
                lookup.checksum == w.expected_checksum &&
                end_to_end.checksum == w.expected_checksum,
            cache->name,
            "gpu-page-grouped",
            scheduler.transient_bytes,
            scheduling_us,
            end_to_end.gpu_us_per_dispatch,
        });
    }

    ctx_.destroy_buffer(scheduler.grouped_queries);
    ctx_.destroy_buffer(scheduler.cursors);
    ctx_.destroy_buffer(scheduler.offsets);
    ctx_.destroy_buffer(scheduler.counts);

    ctx_.destroy_buffer(page_grouped_queries);
    ctx_.destroy_buffer(randomized_queries);
    ctx_.destroy_buffer(source_queries);

    ctx_.destroy_buffer(paged.payload);
    ctx_.destroy_buffer(paged.table);
    ctx_.destroy_buffer(hash.payload);
    ctx_.destroy_buffer(hash.table);

    return out;
}

} // namespace phos::gi
